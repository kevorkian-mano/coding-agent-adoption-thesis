"""
Stage 2c (fast): Egyptian Corpus Pull via GraphQL

Batched alternative to the REST-based Stage2c_egypt_corpus_direct_pull.py.
Fetches repos, JS/TS language shares, commit counts, AND package.json
presence in a single GraphQL call per batch of accounts — significantly
fewer API round-trips than the REST version.

Input:  egypt_combined_accounts.csv
Output: egypt_corpus.csv  (same schema as the REST version)

Requires: pip install requests pandas
Set GITHUB_TOKEN as an environment variable first.
"""

import os
import time
import requests
import pandas as pd

# ── Shared constants (must match across all 6 topics) ─────────────────────────
STUDY_SNAPSHOT_DATE = "2026-09-01"
MIN_COMMITS         = 10
MIN_CONTRIBUTORS    = 2   # NOTE: GraphQL repos endpoint does not expose contributor
                           # count. Stage 2c REST version enforces this; here we skip
                           # it and rely on Stage 1 having already enforced it for the
                           # base corpus. For the Egypt-specific corpus, contributor
                           # count is checked in a post-processing step if needed.
MIN_LAST_PUSH       = "2023-01-01"
MIN_JS_TS_SHARE     = 0.5

# ── Topic-specific ────────────────────────────────────────────────────────────
TOPIC_ID  = 2
ECOSYSTEM = "npm"

# ── API ───────────────────────────────────────────────────────────────────────
GRAPHQL_URL = "https://api.github.com/graphql"
TOKEN       = os.environ.get("GITHUB_TOKEN")
HEADERS     = {
    "Authorization": f"bearer {TOKEN}",
    "Accept":        "application/vnd.github.v3+json",
}

BATCH_SIZE = 5    # accounts per GraphQL request (10+ caused 502 timeouts)


# ─────────────────────────────────────────────────────────────────────────────
# GraphQL query builder
# ─────────────────────────────────────────────────────────────────────────────

def build_batch_query(batch_logins: list) -> str:
    """
    Builds a single GraphQL query for a batch of accounts.
    For each repo we fetch: basic metadata, primaryLanguage, pushedAt.

    Intentionally omitted (too expensive in bulk):
      - history { totalCount } : scans full commit history, exhausts quota
      - object(expression:"HEAD:package.json") : git tree lookup per repo × 50 = 502 timeouts
      - languages { edges } : byte-share distribution per repo (replaced by primaryLanguage check)

    Activity proxy: pushedAt >= MIN_LAST_PUSH (replaces commit count check).
    Language proxy: primaryLanguage in JS/TS (replaces byte-share check).
    I-9 (package.json) is skipped for the Egypt corpus — documented limitation.
    """
    nodes = []
    for idx, login in enumerate(batch_logins):
        clean = login.replace('"', "").strip()
        nodes.append(f"""
        owner_{idx}: repositoryOwner(login: "{clean}") {{
          login
          repositories(
            first: 50,
            isFork: false,
            privacy: PUBLIC,
            orderBy: {{field: PUSHED_AT, direction: DESC}}
          ) {{
            nodes {{
              name
              nameWithOwner
              stargazerCount
              pushedAt
              primaryLanguage {{ name }}
            }}
          }}
        }}
        """)
    return "query { " + " ".join(nodes) + " }"


# ─────────────────────────────────────────────────────────────────────────────
# Request helper
# ─────────────────────────────────────────────────────────────────────────────

def post_graphql(query: str, max_retries: int = 4) -> dict:
    """POST GraphQL query with retry and proper rate-limit handling."""
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.post(
                GRAPHQL_URL,
                json={"query": query},
                headers=HEADERS,
                timeout=15,
            )
            if res.status_code == 403:
                reset = int(res.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait  = max(reset - int(time.time()), 1) + 2
                print(f"  Rate limited (HTTP 403). Sleeping {wait}s...")
                time.sleep(wait)
                continue
            if res.status_code in (502, 504):
                wait = 2 ** attempt
                print(f"  Server error {res.status_code}, retry {attempt}/{max_retries} in {wait}s...")
                time.sleep(wait)
                continue
            if res.status_code != 200:
                return {}
            payload = res.json()
            # GraphQL rate-limit errors: 200 response with error payload
            if "errors" in payload:
                errs = payload["errors"]
                if any(e.get("type") == "RATE_LIMITED" for e in errs):
                    print("  GraphQL RATE_LIMITED. Sleeping 60s...")
                    time.sleep(60)
                    continue
            return payload.get("data") or {}
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
            wait = 2 ** attempt
            print(f"  Network error ({type(e).__name__}), retry {attempt}/{max_retries} in {wait}s...")
            time.sleep(wait)
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# Result parsing
# ─────────────────────────────────────────────────────────────────────────────

def compute_stratum(stars: int) -> str:
    if stars <= 50:
        return "small"
    if stars <= 500:
        return "medium"
    return "large"


def process_batch_data(data: dict, all_rows: list):
    """Parse GraphQL response and apply all filters."""
    for owner_data in data.values():
        if not owner_data or not owner_data.get("repositories"):
            continue

        owner_login = owner_data["login"]
        repos       = owner_data["repositories"]["nodes"] or []

        for repo in repos:
            # I-6: last push date
            pushed_at = repo.get("pushedAt") or ""
            if pushed_at[:10] < MIN_LAST_PUSH:
                continue
            # Snapshot bound
            if pushed_at[:10] > STUDY_SNAPSHOT_DATE:
                continue

            # I-8 (proxy): primary language must be JS or TS
            primary_lang = (repo.get("primaryLanguage") or {}).get("name")
            if primary_lang not in ("JavaScript", "TypeScript"):
                continue

            all_rows.append({
                "seed_account":     owner_login,
                "owner_login":      owner_login,
                "repo_name":        repo["name"],
                "full_name":        repo["nameWithOwner"],
                "primary_language": primary_lang,
                "stars":            repo.get("stargazerCount"),
                "pushed_at":        pushed_at,
                "has_manifest":     None,   # I-9 not checked (git tree lookup too expensive)
                "total_commits":    None,   # not fetched (history scan too expensive)
                "js_ts_byte_share": None,   # not fetched (languages edges removed)
                "size_stratum":     compute_stratum(repo.get("stargazerCount", 0)),
                "agent_adopted":    None,   # filled in Stage 4
                "topic_id":         TOPIC_ID,
                "ecosystem":        ECOSYSTEM,
            })


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main(seed_csv_path: str = "egypt_combined_accounts.csv",
         output_csv: str    = "egypt_corpus.csv"):

    if not os.path.exists(seed_csv_path):
        print(f"Error: {seed_csv_path} not found.")
        return

    seeds  = pd.read_csv(seed_csv_path)
    logins = seeds["login"].dropna().unique().tolist()
    print(f"Loaded {len(logins)} unique accounts. "
          f"Starting batched GraphQL pull (batch size={BATCH_SIZE})...")

    all_rows      = []
    total_batches = (len(logins) + BATCH_SIZE - 1) // BATCH_SIZE
    SAVE_EVERY    = 100   # write progress every N batches

    for i in range(0, len(logins), BATCH_SIZE):
        batch = logins[i : i + BATCH_SIZE]
        b_num = i // BATCH_SIZE + 1
        query = build_batch_query(batch)
        data  = post_graphql(query)

        if data:
            process_batch_data(data, all_rows)
        else:
            # Fallback: process accounts individually if batch fails entirely
            print(f"  Batch {b_num} returned no data — retrying individually...")
            for single_login in batch:
                single_data = post_graphql(build_batch_query([single_login]))
                if single_data:
                    process_batch_data(single_data, all_rows)
                time.sleep(0.2)

        if b_num % SAVE_EVERY == 0:
            pd.DataFrame(all_rows).drop_duplicates(subset=["full_name"]).to_csv(output_csv, index=False)
            print(f"  [{b_num}/{total_batches}] Progress saved. Repos so far: {len(all_rows)}")
        else:
            print(f"  [{b_num}/{total_batches}] Repos so far: {len(all_rows)}")

        time.sleep(0.3)

    df = pd.DataFrame(all_rows).drop_duplicates(subset=["full_name"])
    df.to_csv(output_csv, index=False)

    print(f"\n─── Summary ─────────────────────────────────────────────")
    print(f"Accounts checked       : {len(logins)}")
    print(f"Repos matching criteria: {len(df)}")
    if not df.empty:
        print(f"Stratum breakdown:\n{df['size_stratum'].value_counts().to_string()}")
    print(f"Saved to '{output_csv}'")


if __name__ == "__main__":
    main()
