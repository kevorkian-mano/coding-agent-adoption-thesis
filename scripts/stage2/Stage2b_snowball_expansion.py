"""
Stage 2b: Egyptian Seed List Snowball Expansion

Takes the cleaned seed list from Stage 2a and expands it by pulling
each seed account's followers and following via the GitHub GraphQL API.
New accounts with Egypt-linked locations are collected and become the
frontier for the next round.

Runs up to 3 rounds, stopping early if a round finds no new accounts
(convergence).

Input: a CSV with a 'login' column (your cleaned Stage 2a output)
Output: egypt_snowball_candidates.csv with a 'round' column indicating
        which expansion round discovered each account.

Requires: pip install requests pandas
Set GITHUB_TOKEN as an environment variable first.
"""

import os
import time
import requests
import pandas as pd

GRAPHQL_URL = "https://api.github.com/graphql"
TOKEN       = os.environ.get("GITHUB_TOKEN")
HEADERS     = {"Authorization": f"Bearer {TOKEN}"}

MAX_ROUNDS               = 3
MAX_CONNECTIONS_PER_SEED = 30   # followers + following per account per round
CONNECTIONS_BATCH_SIZE   = 5    # accounts per GraphQL request

# English and Arabic location terms — must match Stage 2a
LOCATION_TERMS = [
    "egypt", "cairo", "alexandria", "giza",
    "مصر", "القاهرة", "الإسكندرية", "الجيزة",
]


# ─────────────────────────────────────────────────────────────────────────────
# Network helpers
# ─────────────────────────────────────────────────────────────────────────────

def graphql_post(query: str, max_retries: int = 4) -> dict:
    """POST to the GraphQL endpoint with retry on network errors and 403."""
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(
                GRAPHQL_URL,
                headers=HEADERS,
                json={"query": query},
                timeout=15,
            )
            if resp.status_code == 403:
                reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait  = max(reset - int(time.time()), 1) + 2
                print(f"    Rate limited. Sleeping {wait}s (resets at epoch {reset})...")
                time.sleep(wait)
                continue
            if resp.status_code != 200:
                return {}
            data = resp.json()
            # GraphQL rate-limit errors come back as 200 with an error payload
            if "errors" in data:
                errs = data["errors"]
                if any(e.get("type") == "RATE_LIMITED" for e in errs):
                    print("    GraphQL rate limited. Sleeping 60s...")
                    time.sleep(60)
                    continue
            return data.get("data", {})
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
            wait = 2 ** attempt
            print(f"    Network error ({type(e).__name__}), retry {attempt}/{max_retries} in {wait}s...")
            time.sleep(wait)
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# GraphQL: batch-fetch followers + following for up to CONNECTIONS_BATCH_SIZE accounts
# ─────────────────────────────────────────────────────────────────────────────

def build_connections_batch_query(logins: list, count: int) -> str:
    """
    Fetches followers and following for a batch of logins in one GraphQL request.
    Uses aliases (user_0, user_1, …) so multiple users can be queried at once.
    count = MAX_CONNECTIONS_PER_SEED (30) — keep low to avoid heavy node traversal.
    """
    fragments = []
    for idx, login in enumerate(logins):
        clean = login.replace('"', "")
        fragments.append(f"""
        user_{idx}: user(login: "{clean}") {{
            login
            followers(first: {count}) {{
                nodes {{ login name location bio }}
            }}
            following(first: {count}) {{
                nodes {{ login name location bio }}
            }}
        }}
        """)
    return "query { " + " ".join(fragments) + " }"


def fetch_connections_batch(logins: list) -> dict:
    """
    Returns dict: login -> (followers_list, following_list)
    for all logins in the batch.
    """
    query = build_connections_batch_query(logins, MAX_CONNECTIONS_PER_SEED)
    data  = graphql_post(query)
    result = {}
    for idx, login in enumerate(logins):
        user_data = data.get(f"user_{idx}")
        if not user_data:
            result[login] = ([], [])
            continue
        followers = (user_data.get("followers") or {}).get("nodes") or []
        following = (user_data.get("following") or {}).get("nodes") or []
        result[login] = (followers, following)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Location matching
# ─────────────────────────────────────────────────────────────────────────────

def location_matches_egypt(location_str) -> bool:
    if not location_str:
        return False
    loc_lower = location_str.lower()
    # Arabic terms are matched as-is (already lowercase-safe for Latin; Arabic is case-insensitive)
    return any(term.lower() in loc_lower for term in LOCATION_TERMS)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main(seed_csv_path: str = "egypt_seed_candidates.csv"):
    seeds = pd.read_csv(seed_csv_path)
    seed_logins = set(seeds["login"].astype(str))
    print(f"Loaded {len(seed_logins)} seed accounts from {seed_csv_path}")

    # `all_confirmed` tracks every account we've already catalogued so we
    # never re-add them in a later round.
    all_confirmed   = set(seed_logins)
    current_frontier = set(seed_logins)  # accounts to expand in this round

    all_discovered_rows = []

    for round_num in range(1, MAX_ROUNDS + 1):
        frontier_list = list(current_frontier)
        total_batches = (len(frontier_list) + CONNECTIONS_BATCH_SIZE - 1) // CONNECTIONS_BATCH_SIZE
        print(f"\n=== Snowball Round {round_num} "
              f"(frontier: {len(frontier_list)} accounts, {total_batches} batches) ===")
        new_this_round = {}

        for b_start in range(0, len(frontier_list), CONNECTIONS_BATCH_SIZE):
            batch    = frontier_list[b_start : b_start + CONNECTIONS_BATCH_SIZE]
            b_num    = b_start // CONNECTIONS_BATCH_SIZE + 1
            print(f"  Batch {b_num}/{total_batches} ({len(batch)} accounts)...")

            connections = fetch_connections_batch(batch)

            for login, (followers, following) in connections.items():
                for acct in followers + following:
                    candidate_login = acct.get("login")
                    if not candidate_login:
                        continue
                    if candidate_login in all_confirmed:
                        continue
                    if location_matches_egypt(acct.get("location")):
                        if candidate_login not in new_this_round:
                            new_this_round[candidate_login] = {
                                "login":           candidate_login,
                                "name":            acct.get("name"),
                                "location_raw":    acct.get("location"),
                                "bio":             acct.get("bio"),
                                "discovered_from": login,
                                "round":           round_num,
                            }

            time.sleep(1)   # 1s between batches

        if not new_this_round:
            print(f"  No new accounts found in round {round_num}. Converged early.")
            break

        print(f"  Round {round_num} complete: {len(new_this_round)} new Egypt-linked accounts.")
        all_discovered_rows.extend(new_this_round.values())

        # Next round's frontier = only the accounts just discovered
        all_confirmed.update(new_this_round.keys())
        current_frontier = set(new_this_round.keys())

    df = pd.DataFrame(all_discovered_rows) if all_discovered_rows else pd.DataFrame()
    df.to_csv("egypt_snowball_candidates.csv", index=False)

    print(f"\n─── Summary ─────────────────────────────────────────────")
    print(f"Seeds processed               : {len(seed_logins)}")
    print(f"New Egypt-linked accounts     : {len(df)}")
    if not df.empty and "round" in df.columns:
        print(f"By round:\n{df['round'].value_counts().sort_index().to_string()}")
    print(f"\nSaved to egypt_snowball_candidates.csv")
    print("NEXT: run combine_accounts.py, then Stage 2c on the combined list.")


if __name__ == "__main__":
    main()
