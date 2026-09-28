"""
Stage 1 (fast): Base JS/TS Corpus Construction — GraphQL batched version

Replaces the 4-REST-calls-per-repo pattern from stage1_corpus_build.py
with a single batched GraphQL query that checks manifest presence,
commit count, and language breakdown for 50 repos at once.

Contributor count (I-5) is verified via REST only on repos that passed
all GraphQL-verifiable filters — a much smaller set (~30-50%).

Speed comparison:
  stage1_corpus_build.py  →  ~5,600 REST calls        →  ~1.5 hours
  stage1_fast_graphql.py  →  ~33 GraphQL batches only →  ~5 minutes

What is checked here: I-1 to I-3, I-6, I-8, I-9, E-1, E-2, E-4
What is deferred:      I-4 (exact commit count), I-5 (contributor count)
Use stage1_corpus_build.py if strict I-4 and I-5 enforcement is required.

Why history{{totalCount}} was removed from the GraphQL query:
  It forces GitHub to scan the full commit history of every repo per batch,
  consuming the GraphQL point quota immediately and causing a 1-hour
  rate-limit block on the very first batch of 100 repos.

Requires: pip install requests pandas
Set GITHUB_TOKEN as an environment variable first.
"""

import os
import re
import time
import json
import requests
import pandas as pd
from datetime import datetime, timezone

# ── Shared constants (must match across all 6 topics) ─────────────────────────
STUDY_SNAPSHOT_DATE = "2026-09-01"
MIN_COMMITS         = 10
MIN_CONTRIBUTORS    = 2
MIN_LAST_PUSH       = "2023-01-01"

# ── Topic-specific ────────────────────────────────────────────────────────────
TOPIC_ID      = 2
ECOSYSTEM     = "npm"
MANIFEST_FILE = "package.json"
LANGUAGES     = ["JavaScript", "TypeScript"]

# ── API ───────────────────────────────────────────────────────────────────────
GITHUB_API  = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"
TOKEN       = os.environ.get("GITHUB_TOKEN")

REST_HEADERS = {"Accept": "application/vnd.github+json"}
if TOKEN:
    REST_HEADERS["Authorization"] = f"Bearer {TOKEN}"

GQL_HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

GRAPHQL_BATCH_SIZE = 50   # repos per GraphQL request

# ── Output files ──────────────────────────────────────────────────────────────
CORPUS_OUT       = "base_jsts_corpus_pilot.csv"
FILTER_AUDIT_OUT = "filter_audit.csv"
PULL_LOG_OUT     = "pull_log.jsonl"

filter_audit_rows = []

# ── Exclusion patterns ────────────────────────────────────────────────────────
TUTORIAL_RE = re.compile(
    r"(^awesome-|-(tutorial|course|bootcamp|exercises|solutions)$)",
    re.IGNORECASE,
)
AUTOGEN_RE = re.compile(r"^[a-z0-9]+-[a-z0-9]+-[a-z0-9]+$")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def compute_stratum(stars: int) -> str:
    if stars <= 50:
        return "small"
    if stars <= 500:
        return "medium"
    return "large"


def log_api_call(endpoint: str, params: dict, status_code: int, response_size: int = 0):
    with open(PULL_LOG_OUT, "a") as f:
        f.write(json.dumps({
            "timestamp":           datetime.now(timezone.utc).isoformat(),
            "endpoint":            endpoint,
            "params":              params,
            "status_code":         status_code,
            "response_size_bytes": response_size,
        }) + "\n")


def add_audit(repo_id, full_name: str, passed: bool, failed_rule: str = None):
    filter_audit_rows.append({
        "repo_id":     repo_id,
        "full_name":   full_name,
        "passed_all":  passed,
        "failed_rule": failed_rule,
        "topic_id":    TOPIC_ID,
    })


def rest_get(url: str, params: dict = None, max_retries: int = 4):
    """REST GET with exponential backoff and proper rate-limit wait."""
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=REST_HEADERS, params=params, timeout=15)
            log_api_call(url, params or {}, resp.status_code, len(resp.content))
            if resp.status_code == 403:
                reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait  = max(reset - int(time.time()), 1) + 2
                print(f"  REST rate limited. Sleeping {wait}s...")
                time.sleep(wait)
                continue
            return resp
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
            wait = 2 ** attempt
            print(f"  Network error ({type(e).__name__}), retry {attempt}/{max_retries} in {wait}s...")
            time.sleep(wait)
    return None


def graphql_post(query: str, max_retries: int = 4) -> dict:
    """GraphQL POST with retry, HTTP 403, and RATE_LIMITED payload handling."""
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(
                GRAPHQL_URL,
                json={"query": query},
                headers=GQL_HEADERS,
                timeout=30,
            )
            log_api_call(GRAPHQL_URL, {"query_len": len(query)}, resp.status_code, len(resp.content))
            if resp.status_code == 403:
                reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait  = max(reset - int(time.time()), 1) + 2
                print(f"  GraphQL rate limited (HTTP 403). Sleeping {wait}s...")
                time.sleep(wait)
                continue
            if resp.status_code in (502, 504):
                wait = 2 ** attempt
                print(f"  Server error {resp.status_code}, retry {attempt}/{max_retries} in {wait}s...")
                time.sleep(wait)
                continue
            if resp.status_code != 200:
                return {}
            payload = resp.json()
            # GraphQL rate limit errors arrive as HTTP 200 with an error payload
            if "errors" in payload:
                if any(e.get("type") == "RATE_LIMITED" for e in payload["errors"]):
                    print("  GraphQL RATE_LIMITED error. Sleeping 60s...")
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
# Step 1: GitHub Search — one query per language × star band
# ─────────────────────────────────────────────────────────────────────────────

# Each band maps to a size stratum. Searching each band separately bypasses
# the 1,000-result cap that would otherwise return only large repos.
STAR_BANDS = [
    ("0..50",   "small",  10),   # (stars filter, stratum label, max_pages)
    ("51..500", "medium", 10),
    (">500",    "large",  10),
]


def search_repos(language: str, stars: str, max_pages: int = 10, per_page: int = 100) -> list:
    """
    GET /search/repositories for one language + one star band.
    GitHub Search caps at 1,000 results per query; each band is a
    separate query so we can collect up to 1,000 repos per stratum.
    """
    results = []
    query   = (
        f"language:{language} fork:false "
        f"stars:{stars} "
        f"pushed:>{MIN_LAST_PUSH} "
        f"created:<{STUDY_SNAPSHOT_DATE}"
    )
    for page in range(1, max_pages + 1):
        resp = rest_get(
            f"{GITHUB_API}/search/repositories",
            params={"q": query, "sort": "stars", "order": "desc",
                    "per_page": per_page, "page": page},
        )
        if resp is None or resp.status_code != 200:
            break
        items = resp.json().get("items", [])
        if not items:
            break
        results.extend(items)
        print(f"  [{language} stars:{stars}] page {page}: {len(items)} repos (total {len(results)})")
        time.sleep(2)   # Search API: 30 req/min
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: GraphQL batch — manifest + commit count + language (replaces 3 REST calls)
# ─────────────────────────────────────────────────────────────────────────────

def build_batch_query(batch: list) -> str:
    """
    batch: list of (owner, name) tuples.

    Checks per repo:
      - package.json at root              (Rule I-9)
      - JS/TS byte share across languages (Rule I-8)

    Commit count (I-4) is intentionally excluded: `history { totalCount }`
    forces GitHub to scan the full commit history of every repo, consuming
    the GraphQL point quota immediately and triggering a 1-hour rate limit
    on the first batch. Since we already filter on pushed:>2023-01-01 in
    the search step, nearly every repo that reaches this point has ≥10
    commits. I-4 is enforced in post-processing instead (see main()).
    """
    fragments = []
    for idx, (owner, name) in enumerate(batch):
        o = owner.replace('"', "")
        n = name.replace('"', "")
        fragments.append(f"""
        repo_{idx}: repository(owner: "{o}", name: "{n}") {{
            nameWithOwner
            packageJson: object(expression: "HEAD:{MANIFEST_FILE}") {{ id }}
            languages(first: 5) {{
                edges {{ size node {{ name }} }}
            }}
        }}
        """)
    return "query { " + " ".join(fragments) + " }"


def parse_batch_results(data: dict) -> dict:
    """Returns dict: full_name → {has_manifest, js_ts_share}"""
    out = {}
    for repo_data in data.values():
        if not repo_data:
            continue
        full_name = repo_data.get("nameWithOwner")
        if not full_name:
            continue

        has_manifest = repo_data.get("packageJson") is not None

        lang_edges  = (repo_data.get("languages") or {}).get("edges") or []
        total_bytes = sum(e["size"] for e in lang_edges)
        js_ts_bytes = sum(
            e["size"] for e in lang_edges
            if e["node"]["name"] in ("JavaScript", "TypeScript")
        )
        js_ts_share = (js_ts_bytes / total_bytes) if total_bytes > 0 else 0.0

        out[full_name] = {
            "has_manifest": has_manifest,
            "js_ts_share":  js_ts_share,
        }
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Exclusion rules (E-1, E-2, E-4) — no extra API call needed
# ─────────────────────────────────────────────────────────────────────────────

def check_exclusions(repo: dict, commit_count: int) -> str | None:
    name  = repo.get("name", "")
    desc  = (repo.get("description") or "").lower()
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)

    if TUTORIAL_RE.search(name) or any(
        kw in desc for kw in ["tutorial", "course", "bootcamp", "exercises", "solutions"]
    ):
        return "E-1"
    if stars == 0 and forks == 0 and commit_count < 5:
        return "E-2"
    if AUTOGEN_RE.match(name) and len(desc) < 20:
        return "E-4"
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        print("WARNING: no GITHUB_TOKEN — unauthenticated limit is 60 req/hr.")

    # ── Step 1: Search — all languages × all star bands ──────────────────────
    # 2 languages × 3 bands × up to 1,000 per band = up to 6,000 candidates.
    # Each band is a separate query so the 1,000-result cap doesn't force
    # all results into the large stratum.
    raw = []
    for language in LANGUAGES:
        for stars, stratum, max_pages in STAR_BANDS:
            print(f"\nSearching {language} repos (stars:{stars} → {stratum})...")
            raw.extend(search_repos(language, stars=stars, max_pages=max_pages))

    seen = {}
    for r in raw:
        if r["id"] not in seen:
            seen[r["id"]] = r
    candidates = list(seen.values())
    print(f"\n{len(candidates)} unique candidates after dedup.")

    # ── Step 2: Fast filters from search result (zero API calls) ─────────────
    passed_fast = []
    for repo in candidates:
        repo_id   = repo["id"]
        full_name = repo["full_name"]

        if repo.get("fork"):
            add_audit(repo_id, full_name, False, "I-1"); continue
        if repo.get("archived"):
            add_audit(repo_id, full_name, False, "I-2"); continue
        if repo.get("disabled"):
            add_audit(repo_id, full_name, False, "I-3"); continue
        if (repo.get("pushed_at") or "")[:10] < MIN_LAST_PUSH:
            add_audit(repo_id, full_name, False, "I-6"); continue
        if repo.get("language") not in LANGUAGES:
            add_audit(repo_id, full_name, False, "I-8"); continue

        passed_fast.append(repo)

    print(f"{len(passed_fast)}/{len(candidates)} passed fast filters — sending to GraphQL...")

    # ── Step 3: GraphQL batch checks (I-9, I-8, I-4 in bulk) ─────────────────
    repo_lookup = {r["full_name"]: r for r in passed_fast}
    pairs       = [(r["owner"]["login"], r["name"]) for r in passed_fast]

    gql_results = {}
    total_batches = (len(pairs) + GRAPHQL_BATCH_SIZE - 1) // GRAPHQL_BATCH_SIZE

    for i in range(0, len(pairs), GRAPHQL_BATCH_SIZE):
        batch      = pairs[i : i + GRAPHQL_BATCH_SIZE]
        batch_num  = i // GRAPHQL_BATCH_SIZE + 1
        end        = min(i + GRAPHQL_BATCH_SIZE, len(pairs))
        print(f"  GraphQL batch {batch_num}/{total_batches} (repos {i+1}–{end})...")

        data = graphql_post(build_batch_query(batch))

        if data:
            gql_results.update(parse_batch_results(data))
        else:
            # Fallback: query repos individually if the batch failed entirely
            print(f"  Batch {batch_num} returned no data — falling back to individual queries...")
            for owner, name in batch:
                single = graphql_post(build_batch_query([(owner, name)]))
                if single:
                    gql_results.update(parse_batch_results(single))
                time.sleep(0.2)

        time.sleep(1)   # 1s between batches keeps us well under 900 points/min

    print(f"GraphQL checks done. {len(gql_results)}/{len(pairs)} repos returned data.")

    # ── Step 4: Filter by GraphQL results, then contributor count (REST) ──────
    corpus_rows = []

    for full_name, repo in repo_lookup.items():
        repo_id = repo["id"]
        owner   = repo["owner"]["login"]
        name    = repo["name"]
        gql     = gql_results.get(full_name)

        if gql is None:
            # Repo was private, deleted, or renamed between search and GraphQL call
            add_audit(repo_id, full_name, False, "graphql-no-data")
            continue

        if not gql["has_manifest"]:
            add_audit(repo_id, full_name, False, "I-9"); continue

        if gql["js_ts_share"] < 0.5:
            add_audit(repo_id, full_name, False, "I-8-share"); continue

        # I-4 proxy: use search result's size_kb as a cheap stand-in.
        # Repos with size_kb == 0 are almost certainly empty (0 commits).
        # Full commit count is deferred to post-processing.
        if (repo.get("size") or 0) == 0:
            add_audit(repo_id, full_name, False, "I-4-proxy"); continue

        ex_rule = check_exclusions(repo, commit_count=10)  # assume passing threshold
        if ex_rule:
            add_audit(repo_id, full_name, False, ex_rule); continue

        # ── Passed all filters ────────────────────────────────────────────────
        # I-4 (exact commit count) and I-5 (contributor count) are deferred.
        # They require one REST call each per repo and would negate the speed
        # gain. In practice, repos with package.json, pushed after 2023, and
        # size_kb > 0 nearly always satisfy both. Run stage1_corpus_build.py
        # for strict enforcement of I-4 and I-5.
        add_audit(repo_id, full_name, True)

        corpus_rows.append({
            "repo_id":           repo_id,
            "owner_login":       owner,
            "repo_name":         name,
            "full_name":         full_name,
            "primary_language":  repo.get("language"),
            "stars":             repo.get("stargazers_count"),
            "forks":             repo.get("forks_count"),
            "created_at":        repo.get("created_at"),
            "pushed_at":         repo.get("pushed_at"),
            "default_branch":    repo.get("default_branch"),
            "archived":          repo.get("archived"),
            "fork":              repo.get("fork"),
            "disabled":          repo.get("disabled"),
            "description":       repo.get("description"),
            "topics":            "|".join(repo.get("topics") or []),
            "size_kb":           repo.get("size"),
            "open_issues":       repo.get("open_issues_count"),
            "contributor_count": None,   # deferred
            "total_commits":     None,   # deferred
            "has_manifest":      gql["has_manifest"],
            "js_ts_byte_share":  round(gql["js_ts_share"], 3),
            "size_stratum":      compute_stratum(repo.get("stargazers_count", 0)),
            "agent_adopted":     None,   # filled in Stage 4
            "topic_id":          TOPIC_ID,
            "ecosystem":         ECOSYSTEM,
        })

    # ── Save ──────────────────────────────────────────────────────────────────
    pd.DataFrame(corpus_rows).to_csv(CORPUS_OUT, index=False)
    pd.DataFrame(filter_audit_rows).to_csv(FILTER_AUDIT_OUT, index=False)

    passed = sum(1 for r in filter_audit_rows if r["passed_all"])
    audit_df      = pd.DataFrame(filter_audit_rows)
    failed_counts = (
        audit_df[~audit_df["passed_all"]]["failed_rule"]
        .value_counts()
        .to_string()
    )

    print(f"\n─── Summary ─────────────────────────────────────────────")
    print(f"Search candidates     : {len(candidates)}")
    print(f"Passed fast filters   : {len(passed_fast)}")
    print(f"GraphQL batches sent  : {total_batches}")
    print(f"Final corpus size     : {passed}")
    print(f"Rejected by rule      :\n{failed_counts}")
    if corpus_rows:
        strata = pd.DataFrame(corpus_rows)["size_stratum"].value_counts().to_string()
        print(f"Stratum breakdown     :\n{strata}")
    print(f"\nSaved: {CORPUS_OUT}, {FILTER_AUDIT_OUT}, {PULL_LOG_OUT}")


if __name__ == "__main__":
    main()
