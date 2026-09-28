"""
Stage 2a: Egyptian Seed List Discovery

Searches GitHub for developer accounts with Egypt-linked locations (English
and Arabic terms), then batch-fetches profile details via GraphQL to apply
the activity filter and produce the seed list for Stage 2b.

Speed: ~3-5 minutes (GraphQL batch replaces 1 REST call per account).

Requires: pip install requests pandas
Set GITHUB_TOKEN as an environment variable first.
"""

import os
import time
import requests
import pandas as pd

GITHUB_API  = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"
TOKEN       = os.environ.get("GITHUB_TOKEN")

REST_HEADERS = {"Accept": "application/vnd.github+json"}
GQL_HEADERS  = {}
if TOKEN:
    REST_HEADERS["Authorization"] = f"Bearer {TOKEN}"
    GQL_HEADERS["Authorization"]  = f"Bearer {TOKEN}"

# English and Arabic location terms (both needed to avoid undercounting)
LOCATION_TERMS = [
    "Egypt", "Cairo", "Alexandria", "Giza",
    "مصر", "القاهرة", "الإسكندرية", "الجيزة",
]

# Minimum activity filter (≥10 followers OR ≥5 public repos)
MIN_FOLLOWERS    = 10
MIN_PUBLIC_REPOS = 5

USER_DETAIL_BATCH_SIZE = 50   # accounts per GraphQL request

OUTPUT_FILE = "egypt_seed_candidates.csv"
SAVE_EVERY  = 200             # write progress every N batches


# ─────────────────────────────────────────────────────────────────────────────
# Network helpers
# ─────────────────────────────────────────────────────────────────────────────

def rest_get(url: str, params: dict = None, max_retries: int = 4):
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=REST_HEADERS, params=params, timeout=15)
            if resp.status_code == 403:
                reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait  = max(reset - int(time.time()), 1) + 2
                print(f"    Rate limited. Sleeping {wait}s...")
                time.sleep(wait)
                continue
            return resp
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
            wait = 2 ** attempt
            print(f"    Network error ({type(e).__name__}), retry {attempt}/{max_retries} in {wait}s...")
            time.sleep(wait)
    return None


def graphql_post(query: str, max_retries: int = 4) -> dict:
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(GRAPHQL_URL, json={"query": query},
                                 headers=GQL_HEADERS, timeout=30)
            if resp.status_code == 403:
                reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait  = max(reset - int(time.time()), 1) + 2
                print(f"    GraphQL rate limited. Sleeping {wait}s...")
                time.sleep(wait)
                continue
            if resp.status_code not in (200,):
                return {}
            payload = resp.json()
            if "errors" in payload:
                if any(e.get("type") == "RATE_LIMITED" for e in payload["errors"]):
                    print("    GraphQL RATE_LIMITED. Sleeping 60s...")
                    time.sleep(60)
                    continue
            return payload.get("data") or {}
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
            wait = 2 ** attempt
            print(f"    Network error ({type(e).__name__}), retry {attempt}/{max_retries} in {wait}s...")
            time.sleep(wait)
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Search users by location term
# ─────────────────────────────────────────────────────────────────────────────

def search_users_by_location(location_term: str, max_pages: int = 5,
                              per_page: int = 100) -> list:
    results = []
    query   = f"location:{location_term}"
    for page in range(1, max_pages + 1):
        resp = rest_get(
            f"{GITHUB_API}/search/users",
            params={"q": query, "per_page": per_page, "page": page,
                    "sort": "repositories", "order": "desc"},
        )
        if resp is None or resp.status_code != 200:
            break
        items = resp.json().get("items", [])
        if not items:
            break
        results.extend(items)
        print(f"  [{query}] page {page}: {len(items)} accounts (total {len(results)})")
        time.sleep(2)   # Search API: 30 req/min
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Batch-fetch user details via GraphQL (replaces 1 REST call per user)
# ─────────────────────────────────────────────────────────────────────────────

def build_user_detail_query(logins: list) -> str:
    """
    Fetches followers count, public repo count, location, and account type
    for a batch of logins in one GraphQL request.
    Uses totalCount only (no node list) — cheap in terms of GraphQL points.
    """
    fragments = []
    for idx, login in enumerate(logins):
        clean = login.replace('"', "")
        fragments.append(f"""
        user_{idx}: user(login: "{clean}") {{
            login
            name
            bio
            location
            company
            createdAt
            followers {{ totalCount }}
            publicRepos: repositories(
                privacy: PUBLIC, ownerAffiliations: OWNER
            ) {{ totalCount }}
        }}
        """)
    return "query { " + " ".join(fragments) + " }"


def parse_user_detail_results(data: dict) -> dict:
    """Returns dict: login → detail fields"""
    out = {}
    for user_data in data.values():
        if not user_data:
            continue
        login = user_data.get("login")
        if not login:
            continue
        out[login] = {
            "name":         user_data.get("name"),
            "company":      user_data.get("company"),
            "bio":          user_data.get("bio"),
            "location_raw": user_data.get("location"),
            "followers":    (user_data.get("followers") or {}).get("totalCount", 0),
            "public_repos": (user_data.get("publicRepos") or {}).get("totalCount", 0),
            "account_type": "User",   # user(login:...) only returns User nodes
            "created_at":   user_data.get("createdAt"),
        }
    return out


def meets_activity_filter(details: dict) -> bool:
    """≥10 followers OR ≥5 public repos."""
    return (details.get("followers") or 0) >= MIN_FOLLOWERS or \
           (details.get("public_repos") or 0) >= MIN_PUBLIC_REPOS


# ─────────────────────────────────────────────────────────────────────────────
# Resume support
# ─────────────────────────────────────────────────────────────────────────────

def load_existing_progress() -> pd.DataFrame:
    if os.path.exists(OUTPUT_FILE):
        existing = pd.read_csv(OUTPUT_FILE)
        print(f"Resuming: {len(existing)} accounts already fetched.")
        return existing
    return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        print("WARNING: no GITHUB_TOKEN — unauthenticated limit is 60 req/hr.")

    # ── Step 1: Search all location terms ─────────────────────────────────────
    all_accounts = {}
    for term in LOCATION_TERMS:
        print(f"\nSearching location: {term}")
        found = search_users_by_location(term, max_pages=5)
        for acct in found:
            login = acct["login"]
            if login not in all_accounts:
                all_accounts[login] = {
                    "login":        login,
                    "matched_term": term,
                    "profile_url":  acct["html_url"],
                }

    print(f"\n{len(all_accounts)} unique candidate accounts found.")

    # ── Step 2: Resume check ───────────────────────────────────────────────────
    existing_df  = load_existing_progress()
    already_done = set(existing_df["login"]) if not existing_df.empty else set()
    rows         = existing_df.to_dict("records") if not existing_df.empty else []

    remaining_logins = [l for l in all_accounts if l not in already_done]
    print(f"Batch-fetching details for {len(remaining_logins)} accounts "
          f"({len(already_done)} already done)...")

    # ── Step 3: GraphQL batch-fetch user details ───────────────────────────────
    filtered_out  = 0
    total_batches = (len(remaining_logins) + USER_DETAIL_BATCH_SIZE - 1) // USER_DETAIL_BATCH_SIZE

    for i in range(0, len(remaining_logins), USER_DETAIL_BATCH_SIZE):
        batch   = remaining_logins[i : i + USER_DETAIL_BATCH_SIZE]
        b_num   = i // USER_DETAIL_BATCH_SIZE + 1
        print(f"  Detail batch {b_num}/{total_batches} ({len(batch)} accounts)...")

        data         = graphql_post(build_user_detail_query(batch))
        details_map  = parse_user_detail_results(data) if data else {}

        for login in batch:
            base    = all_accounts[login]
            details = details_map.get(login, {})

            if not details or not meets_activity_filter(details):
                filtered_out += 1
                continue

            rows.append({**base, **details})

        # Incremental save
        if b_num % SAVE_EVERY == 0:
            pd.DataFrame(rows).to_csv(OUTPUT_FILE, index=False)
            print(f"    Progress saved ({len(rows)} accounts so far).")

        time.sleep(0.5)

    # ── Save ──────────────────────────────────────────────────────────────────
    df = pd.DataFrame(rows).drop_duplicates(subset=["login"])
    df["review_priority_score"] = df["public_repos"].fillna(0) + df["followers"].fillna(0)
    df = df.sort_values("review_priority_score", ascending=False)
    df.to_csv(OUTPUT_FILE, index=False)

    print(f"\n─── Summary ─────────────────────────────────────────────")
    print(f"Candidates found        : {len(all_accounts)}")
    print(f"Filtered (low activity) : {filtered_out}")
    print(f"Saved to seed list      : {len(df)}")
    print(f"\nSaved to {OUTPUT_FILE}")
    print("NEXT: manually review, remove false positives, then run Stage 2b.")


if __name__ == "__main__":
    main()
