"""
Stage 1: Base JS/TS Corpus Construction

Builds the base corpus of active, non-fork JavaScript/TypeScript repos
using the GitHub Search API, then verifies each candidate's language
composition, commit count, contributor count, and package.json presence.

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
STRATA_BOUNDS       = {"small": (0, 50), "medium": (51, 500), "large": (501, None)}

# ── Topic-specific parameters ─────────────────────────────────────────────────
TOPIC_ID      = 2
ECOSYSTEM     = "npm"
MANIFEST_FILE = "package.json"
LANGUAGES     = ["JavaScript", "TypeScript"]

# ── API ───────────────────────────────────────────────────────────────────────
GITHUB_API = "https://api.github.com"
TOKEN      = os.environ.get("GITHUB_TOKEN")
HEADERS    = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
HEADERS["Accept"] = "application/vnd.github+json"

# ── Output files ──────────────────────────────────────────────────────────────
CORPUS_OUT       = "base_jsts_corpus_pilot.csv"
FILTER_AUDIT_OUT = "filter_audit.csv"
PULL_LOG_OUT     = "pull_log.jsonl"

filter_audit_rows = []

# ── Tutorial / auto-gen exclusion patterns (E-1, E-4) ────────────────────────
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "endpoint": endpoint,
            "params": params,
            "status_code": status_code,
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


def rate_limited_get(url: str, params: dict = None, max_retries: int = 4):
    """GET with retry on network errors and proper wait on 403 rate limit."""
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
            log_api_call(url, params or {}, resp.status_code, len(resp.content))
            if resp.status_code == 403:
                reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait  = max(reset - int(time.time()), 1) + 2
                print(f"  Rate limited. Sleeping {wait}s (resets at epoch {reset})...")
                time.sleep(wait)
                continue
            return resp
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
            wait = 2 ** attempt
            print(f"  Network error ({type(e).__name__}), retry {attempt}/{max_retries} in {wait}s...")
            time.sleep(wait)
    print(f"  FAILED after {max_retries} retries: {url}")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Search
# ─────────────────────────────────────────────────────────────────────────────

def search_repos(language: str, max_pages: int = 10, per_page: int = 100) -> list:
    """
    GET /search/repositories
    - No star minimum: stars are for stratification only, not a filter.
    - Sort by stars to get a diverse sample across strata.
    - Bounded by MIN_LAST_PUSH and STUDY_SNAPSHOT_DATE.
    GitHub Search caps at 1000 results per query. For a larger corpus,
    split by date range or star band and merge.
    """
    results = []
    query = (
        f"language:{language} fork:false "
        f"pushed:>{MIN_LAST_PUSH} "
        f"created:<{STUDY_SNAPSHOT_DATE}"
    )
    for page in range(1, max_pages + 1):
        resp = rate_limited_get(
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
        print(f"  [{language}] page {page}: {len(items)} repos (running total {len(results)})")
        time.sleep(2)  # Search API limit: 30 req/min → 2s between pages
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Manifest verification (Rule I-9)
# ─────────────────────────────────────────────────────────────────────────────

def verify_manifest(owner: str, repo: str) -> bool:
    """Check that package.json exists at the repo root."""
    resp = rate_limited_get(
        f"{GITHUB_API}/repos/{owner}/{repo}/contents/{MANIFEST_FILE}",
        params={"ref": "HEAD"},
    )
    return resp is not None and resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Language byte-share
# ─────────────────────────────────────────────────────────────────────────────

def get_js_ts_share(owner: str, repo: str) -> float:
    """
    Returns the fraction of repo bytes that are JS or TS.
    Uses this as a stricter secondary check beyond GitHub's primary-language tag,
    to exclude repos where JS/TS is only a minor part.
    """
    resp = rate_limited_get(f"{GITHUB_API}/repos/{owner}/{repo}/languages")
    if resp is None or resp.status_code != 200:
        return 0.0
    lang_bytes = resp.json()
    total = sum(lang_bytes.values())
    if total == 0:
        return 0.0
    js_ts = lang_bytes.get("JavaScript", 0) + lang_bytes.get("TypeScript", 0)
    return js_ts / total


# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Commit count (Rule I-4)
# ─────────────────────────────────────────────────────────────────────────────

def approximate_commit_count(owner: str, repo: str) -> int:
    """
    Uses the Link header trick: request 1 commit per page, read the 'last'
    page number from the Link header — that IS the total commit count.
    Bounded by STUDY_SNAPSHOT_DATE so we don't count commits after our window.
    """
    resp = rate_limited_get(
        f"{GITHUB_API}/repos/{owner}/{repo}/commits",
        params={"per_page": 1, "until": f"{STUDY_SNAPSHOT_DATE}T00:00:00Z"},
    )
    if resp is None or resp.status_code != 200:
        return 0
    link = resp.headers.get("Link", "")
    if not link:
        return len(resp.json())
    match = re.search(r'page=(\d+)>; rel="last"', link)
    return int(match.group(1)) if match else 0


# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Contributor count (Rule I-5)
# ─────────────────────────────────────────────────────────────────────────────

def get_contributor_count(owner: str, repo: str) -> int:
    """
    Same Link header trick as commit count.
    GitHub caps contributors at 500; sufficient for our MIN_CONTRIBUTORS = 2 check.
    """
    resp = rate_limited_get(
        f"{GITHUB_API}/repos/{owner}/{repo}/contributors",
        params={"per_page": 1, "anon": "false"},
    )
    if resp is None or resp.status_code == 204:
        return 0
    if resp.status_code != 200:
        return 0
    link = resp.headers.get("Link", "")
    if not link:
        return len(resp.json())
    match = re.search(r'page=(\d+)>; rel="last"', link)
    return int(match.group(1)) if match else 1


# ─────────────────────────────────────────────────────────────────────────────
# Exclusion rules E-1, E-2, E-4 (applied after pull, during cleaning)
# ─────────────────────────────────────────────────────────────────────────────

def check_exclusions(repo: dict, commit_count: int) -> str | None:
    """Returns the rule ID that excludes this repo, or None if it passes all."""
    name  = repo.get("name", "")
    desc  = (repo.get("description") or "").lower()
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)

    # E-1: tutorial / course / collection patterns
    if TUTORIAL_RE.search(name) or any(
        kw in desc for kw in ["tutorial", "course", "bootcamp", "exercises", "solutions"]
    ):
        return "E-1"

    # E-2: completely empty repos
    if stars == 0 and forks == 0 and commit_count < 5:
        return "E-2"

    # E-4: auto-generated name pattern + empty description
    if AUTOGEN_RE.match(name) and len(desc) < 20:
        return "E-4"

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        print("WARNING: no GITHUB_TOKEN — unauthenticated limit is 60 req/hr.")

    # Step 1: Search both languages, deduplicate by repo ID
    raw = []
    for language in LANGUAGES:
        print(f"\nSearching {language} repos...")
        raw.extend(search_repos(language, max_pages=10))

    seen = {}
    for r in raw:
        if r["id"] not in seen:
            seen[r["id"]] = r
    candidates = list(seen.values())
    print(f"\n{len(candidates)} unique candidates after dedup.")

    corpus_rows = []

    for idx, repo in enumerate(candidates):
        repo_id   = repo["id"]
        full_name = repo["full_name"]
        owner     = repo["owner"]["login"]
        name      = repo["name"]
        print(f"[{idx+1}/{len(candidates)}] {full_name}")

        # ── Fast filters (from search result — no extra API call) ─────────────

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

        # ── API calls (only reached after fast filters pass) ──────────────────

        # I-9: package.json at root
        has_manifest = verify_manifest(owner, name)
        if not has_manifest:
            add_audit(repo_id, full_name, False, "I-9"); continue

        # I-8 secondary: JS/TS must be ≥50% of bytes
        js_ts_share = get_js_ts_share(owner, name)
        if js_ts_share < 0.5:
            add_audit(repo_id, full_name, False, "I-8-share"); continue

        # I-4: minimum commits
        commit_count = approximate_commit_count(owner, name)
        if commit_count < MIN_COMMITS:
            add_audit(repo_id, full_name, False, "I-4"); continue

        # I-5: minimum distinct contributors
        contributor_count = get_contributor_count(owner, name)
        if contributor_count < MIN_CONTRIBUTORS:
            add_audit(repo_id, full_name, False, "I-5"); continue

        # Exclusion rules E-1, E-2, E-4
        ex_rule = check_exclusions(repo, commit_count)
        if ex_rule:
            add_audit(repo_id, full_name, False, ex_rule); continue

        # ── All filters passed ────────────────────────────────────────────────
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
            "contributor_count": contributor_count,
            "total_commits":     commit_count,
            "has_manifest":      has_manifest,
            "js_ts_byte_share":  round(js_ts_share, 3),
            "size_stratum":      compute_stratum(repo.get("stargazers_count", 0)),
            "agent_adopted":     None,   # filled in Stage 4
            "topic_id":          TOPIC_ID,
            "ecosystem":         ECOSYSTEM,
        })

        time.sleep(0.3)

    # Save corpus and audit log
    pd.DataFrame(corpus_rows).to_csv(CORPUS_OUT, index=False)
    pd.DataFrame(filter_audit_rows).to_csv(FILTER_AUDIT_OUT, index=False)

    # Summary
    total  = len(filter_audit_rows)
    passed = sum(1 for r in filter_audit_rows if r["passed_all"])
    audit_df = pd.DataFrame(filter_audit_rows)
    failed_counts = (
        audit_df[~audit_df["passed_all"]]["failed_rule"]
        .value_counts()
        .to_string()
    )

    print(f"\n─── Summary ────────────────────────────────────────────")
    print(f"Candidates checked  : {total}")
    print(f"Passed all filters  : {passed}")
    print(f"Rejected by rule    :\n{failed_counts}")
    if corpus_rows:
        strata = pd.DataFrame(corpus_rows)["size_stratum"].value_counts().to_string()
        print(f"Stratum breakdown   :\n{strata}")
    print(f"\nSaved: {CORPUS_OUT}, {FILTER_AUDIT_OUT}, {PULL_LOG_OUT}")


if __name__ == "__main__":
    main()
