# Scripts Reference & Methodology Alignment

**Project**: Coding Agent Adoption in JavaScript/TypeScript/npm  
**Pipeline stages covered**: Stage 1, Stage 2 (a, b, c)  
**Last updated**: 2026-09-25  
**Stage 1 recommended script**: `stage1_fast_graphql.py` (~15 min vs ~1.5 hr)

---

## Table of Contents

1. [Data Flow Overview](#1-data-flow-overview)
2. [Shared Constants](#2-shared-constants)
3. [Script Reference](#3-script-reference)
   - [stage1_fast_graphql.py](#31-stage1_fast_graphqlpy-recommended) ← recommended
   - [stage1_corpus_build.py](#32-stage1_corpus_buildpy-slow-fallback) ← slow fallback
   - [stage2a_egypt_seed_discovery_v2.py](#33-stage2a_egypt_seed_discovery_v2py)
   - [Stage2b_snowball_expansion.py](#34-stage2b_snowball_expansionpy)
   - [combine_accounts.py](#35-combine_accountspy)
   - [Stage2c_egypt_corpus_direct_pull.py](#36-stage2c_egypt_corpus_direct_pullpy-slow-fallback)
   - [stage2c_fast_graphql.py](#37-stage2c_fast_graphqlpy-recommended)
4. [Methodology Alignment Assessment](#4-methodology-alignment-assessment)
5. [Known Gaps — Not Yet Implemented](#5-known-gaps--not-yet-implemented)
6. [Running Order](#6-running-order)

---

## 1. Data Flow Overview

```
stage1_fast_graphql.py     ◄── USE THIS (~15 min)
stage1_corpus_build.py     ◄── slow fallback (~1.5 hr)
    │
    └──► base_jsts_corpus_pilot.csv    (base JS/TS corpus)
         filter_audit.csv              (per-repo pass/fail log)
         pull_log.jsonl                (every API call logged)

stage2a_egypt_seed_discovery_v2.py
    │
    └──► egypt_seed_candidates.csv     (Egyptian developer seeds)

Stage2b_snowball_expansion.py
    │  (reads egypt_seed_candidates.csv)
    └──► egypt_snowball_candidates.csv (3-round expanded accounts)

combine_accounts.py
    │  (reads seed + snowball CSVs)
    └──► egypt_combined_accounts.csv   (deduplicated master list)

stage2c_fast_graphql.py  ◄── recommended
Stage2c_egypt_corpus_direct_pull.py  ◄── slow fallback
    │  (reads egypt_combined_accounts.csv)
    └──► egypt_corpus.csv              (Egyptian JS/TS repos)
         egypt_filter_audit.csv
         egypt_pull_log.jsonl
```

---

## 2. Shared Constants

These constants must be **identical across all 6 topics** in the research cluster. They are defined at the top of every script.

| Constant | Value | Purpose |
|----------|-------|---------|
| `STUDY_SNAPSHOT_DATE` | `"2026-09-01"` | Upper bound for all commits, PRs, and repo pulls |
| `MIN_COMMITS` | `10` | Minimum commits to include a repo (Rule I-4) |
| `MIN_CONTRIBUTORS` | `2` | Minimum distinct authors (Rule I-5) |
| `MIN_LAST_PUSH` | `"2023-01-01"` | Earliest acceptable last-push date (Rule I-6) |
| `TOPIC_ID` | `2` | Identifies this topic in the shared output schema |
| `ECOSYSTEM` | `"npm"` | Package ecosystem label |

---

## 3. Script Reference

---

### 3.1 `stage1_fast_graphql.py` ← recommended

**Purpose**: Same as `stage1_corpus_build.py` but uses GraphQL batching for the expensive per-repo checks. **This is the version you should run.**

**How it's faster**:

| Approach | API calls | Estimated time |
|----------|-----------|----------------|
| REST version (`stage1_corpus_build.py`) | ~5,600 REST calls | ~1.5 hours |
| **GraphQL version (`stage1_fast_graphql.py`)** | **~28 GraphQL + ~600 REST** | **~15 minutes** |

**Why the difference**: The REST version makes 4 separate calls per repo (manifest, language, commit count, contributor count). The GraphQL version batches 50 repos into one request and checks manifest + commit count + language together. Contributor count (which has no GraphQL equivalent) is then checked via REST only for repos that passed everything else — typically ~30–50% of candidates.

**Data flow**:

```
Search (REST)        → ~2,000 candidates
Fast filters         → ~1,400 pass    (no API call)
GraphQL batch        → ~28 requests   (50 repos each)
  checks: I-9, I-4, I-8
Filter by results    → ~700 pass
Contributor check    → ~600 REST calls (only for above)
  checks: I-5
Final corpus         → ~500-600 repos
```

**Output**: Same files as the REST version — `base_jsts_corpus_pilot.csv`, `filter_audit.csv`, `pull_log.jsonl`.

---

### 3.2 `stage1_corpus_build.py` ← slow fallback

**Purpose**: Build the base JS/TS corpus from GitHub Search, then verify each candidate against all inclusion/exclusion rules from the shared methodology.

**Input**: GitHub API (no local file input)

**Outputs**:

| File | Description |
|------|-------------|
| `base_jsts_corpus_pilot.csv` | Repos that passed all filters, with full schema |
| `filter_audit.csv` | Every candidate with pass/fail and the rule that rejected it |
| `pull_log.jsonl` | Timestamped log of every API call made |

**Key functions**:

| Function | What it does |
|----------|-------------|
| `search_repos(language)` | GitHub Search API, sorted by stars, no star minimum |
| `verify_manifest(owner, repo)` | Checks `package.json` exists at root (Rule I-9) |
| `get_js_ts_share(owner, repo)` | Returns fraction of repo bytes in JS or TS |
| `approximate_commit_count(owner, repo)` | Link-header trick for total commits, bounded by snapshot date |
| `get_contributor_count(owner, repo)` | Link-header trick for distinct contributor count |
| `check_exclusions(repo, commit_count)` | Applies rules E-1, E-2, E-4 |
| `rate_limited_get(url, params)` | GET with retry + proper rate-limit wait from `X-RateLimit-Reset` |

**Filtering sequence** (applied in this order to minimize API calls):

```
Search result (no extra call):
  I-1: not a fork
  I-2: not archived
  I-3: not disabled
  I-6: pushed_at ≥ 2023-01-01
  I-8: primary_language in [JavaScript, TypeScript]

Extra API calls (only if above pass):
  I-9: package.json at root         → 1 call
  I-8b: JS/TS byte share ≥ 50%      → 1 call
  I-4: commit count ≥ 10            → 1 call
  I-5: contributor count ≥ 2        → 1 call
  E-1, E-2, E-4: exclusion patterns → no extra call
```

**Output schema** (columns in `base_jsts_corpus_pilot.csv`):

`repo_id`, `owner_login`, `repo_name`, `full_name`, `primary_language`, `stars`, `forks`, `created_at`, `pushed_at`, `default_branch`, `archived`, `fork`, `disabled`, `description`, `topics`, `size_kb`, `open_issues`, `contributor_count`, `total_commits`, `has_manifest`, `js_ts_byte_share`, `size_stratum`, `agent_adopted` *(null — filled Stage 4)*, `topic_id`, `ecosystem`

**Performance note**: Each passing candidate triggers 4 REST calls. For ~1,400 candidates this takes ~1.5 hours. Use `stage1_fast_graphql.py` instead.

---

### 3.2 `stage2a_egypt_seed_discovery_v2.py`

**Purpose**: Discover GitHub accounts whose self-reported location is Egypt, in both English and Arabic, and filter to those with meaningful activity.

**Input**: GitHub API (no local file input)

**Output**: `egypt_seed_candidates.csv`

**Location terms searched** (both English and Arabic):
```python
["Egypt", "Cairo", "Alexandria", "Giza",
 "مصر", "القاهرة", "الإسكندرية", "الجيزة"]
```

**Activity filter** (applied before saving):
- `followers ≥ 10` OR `public_repos ≥ 5`
- Accounts below both thresholds are dropped; they are unlikely to have meaningful JS/TS repositories
- JS/TS-specific filtering happens in Stage 2c after repo pull

**Resume support**: If `egypt_seed_candidates.csv` already exists from a previous partial run, the script skips accounts already fetched and continues from where it left off.

**Output columns**: `login`, `matched_term`, `profile_url`, `name`, `company`, `blog`, `bio`, `location_raw`, `public_repos`, `followers`, `following`, `account_type`, `created_at`, `review_priority_score`

> **Manual review required**: Before running Stage 2b, review this CSV and remove false positives (accounts that matched a term but are not actually Egyptian).

---

### 3.3 `Stage2b_snowball_expansion.py`

**Purpose**: Expand the seed list by following the social graph (followers + following) of each seed account, collecting newly-discovered Egypt-linked accounts. Runs up to 3 rounds or until convergence (no new accounts found).

**Input**: `egypt_seed_candidates.csv` (cleaned, after manual review)

**Output**: `egypt_snowball_candidates.csv`

**Multi-round logic**:

```
Round 1: expand from all seed accounts → new_round_1
Round 2: expand from new_round_1 → new_round_2
Round 3: expand from new_round_2 → new_round_3
Stop if any round finds 0 new accounts (converged)
```

Each discovered account is checked for Egypt-linked location using the same English + Arabic terms as Stage 2a. Accounts already in `all_confirmed` (seeds + prior rounds) are skipped.

**Output columns**: `login`, `name`, `location_raw`, `bio`, `discovered_from`, `round`

> The `round` column tracks which expansion round found each account. This is used to assess the marginal value of each snowball round.

---

### 3.4 `combine_accounts.py`

**Purpose**: Merge the seed list and snowball list into a single deduplicated master file for Stage 2c.

**Input**: `egypt_seed_candidates.csv` + `egypt_snowball_candidates.csv`

**Output**: `egypt_combined_accounts.csv`

**Key behaviors**:
- Validates both input files exist and have a `login` column before proceeding (exits with a clear error otherwise)
- Adds a `source` column: `"seed"` or `"snowball"` for traceability
- Ensures `account_type` column exists for all rows (fills `"User"` for snowball rows which don't have it — required by the Stage 2c REST version)
- Deduplicates on `login`, keeping the first occurrence (seeds take priority)

---

### 3.5 `Stage2c_egypt_corpus_direct_pull.py`

**Purpose**: Pull all JS/TS repositories from each Egyptian account and apply the same inclusion/exclusion filters as Stage 1. **REST version — use only as a fallback.**

**Input**: `egypt_combined_accounts.csv`

**Outputs**: `egypt_corpus.csv`, `egypt_filter_audit.csv`, `egypt_pull_log.jsonl`

**Difference from Stage 1**: Uses `/users/{login}/repos` and `/orgs/{login}/repos` instead of GitHub Search, since we are pulling directly by account rather than searching the whole of GitHub.

**Filtering applied**: Same as Stage 1 — I-1 through I-5, I-6, I-8, I-9, E-1, E-2, E-4.

**Performance**: ~4 REST calls per passing repo. For 300 accounts × 15 repos = slow (4+ hours). Prefer `stage2c_fast_graphql.py` instead.

---

### 3.6 `stage2c_fast_graphql.py`

**Purpose**: Same job as `Stage2c_egypt_corpus_direct_pull.py` but uses GraphQL batching — 10 accounts per request, fetching manifest presence, language breakdown, and commit count all in one query. **This is the version you should run.**

**Input**: `egypt_combined_accounts.csv`

**Output**: `egypt_corpus.csv` (same schema as REST version)

**GraphQL fields fetched per repo**:

```graphql
repositories(first: 100, isFork: false, privacy: PUBLIC) {
  nodes {
    name
    nameWithOwner
    stargazerCount
    pushedAt
    primaryLanguage { name }
    packageJson: object(expression: "HEAD:package.json") { id }   # ← I-9
    defaultBranchRef {
      target {
        ... on Commit {
          history { totalCount }                                    # ← I-4
        }
      }
    }
    languages(first: 10) {
      edges { size node { name } }                                  # ← I-8 byte share
    }
  }
}
```

**Filters applied inside `process_batch_data()`**: I-6, I-9, I-4, I-8 byte share, snapshot date bound.

**What is NOT checked** (known gap): contributor count (I-5). This check requires a separate REST call per repo and is not available via this GraphQL query. Mitigation: see Section 5.

**Performance**: ~20 GraphQL requests for 200 accounts → 5–10 minutes total.

---

## 4. Methodology Alignment Assessment

### 4.1 What is correctly implemented

| Methodology rule | Status | Script(s) |
|-----------------|--------|-----------|
| I-1: not a fork | ✅ | stage1, Stage2c (both) |
| I-2: not archived | ✅ | stage1, Stage2c REST |
| I-3: not disabled | ✅ | stage1, Stage2c REST |
| I-4: ≥10 commits | ✅ | stage1, Stage2c REST, stage2c_graphql |
| I-5: ≥2 contributors | ✅ (REST), ⚠️ (GraphQL) | stage1, Stage2c REST only |
| I-6: pushed ≥ 2023-01-01 | ✅ | all scripts |
| I-8: JS/TS language + byte share | ✅ | stage1, both Stage2c |
| I-9: package.json at root | ✅ | stage1, both Stage2c |
| E-1: tutorial patterns | ✅ | stage1, Stage2c REST |
| E-2: empty repos | ✅ | stage1, Stage2c REST |
| E-4: auto-generated name | ✅ | stage1, Stage2c REST |
| Shared constants match | ✅ | all scripts |
| `STUDY_SNAPSHOT_DATE` used as bound | ✅ | stage1, Stage2c REST |
| `filter_audit.csv` produced | ✅ | stage1, Stage2c REST |
| `pull_log.jsonl` produced | ✅ | stage1, Stage2c REST |
| Size stratum computed | ✅ | stage1, both Stage2c |
| `topic_id` and `ecosystem` in output | ✅ | stage1, both Stage2c |
| Arabic location terms in Stage 2a | ✅ | stage2a, Stage2b |
| Multi-round snowball (≤3 rounds) | ✅ | Stage2b |
| Snowball convergence detection | ✅ | Stage2b |
| `round` column in snowball output | ✅ | Stage2b |
| `discovered_from` column name | ✅ | Stage2b |
| Seed activity filter (followers/repos) | ✅ | stage2a |
| GraphQL batching for Egypt pull | ✅ | stage2c_fast_graphql |
| Rate-limit wait from `X-RateLimit-Reset` | ✅ | all scripts |
| Exponential backoff on network errors | ✅ | all scripts |

### 4.2 Partial implementations

| Methodology rule | Issue | Impact |
|-----------------|-------|--------|
| **I-5 in GraphQL version** | `stage2c_fast_graphql.py` does not check contributor count — GraphQL repos endpoint doesn't expose it | Some single-contributor repos may enter Egypt corpus. Low risk: most active repos have ≥2 contributors. Fix: post-processing REST call for repos that pass all other filters |
| **E-1, E-2, E-4 in GraphQL version** | `stage2c_fast_graphql.py` does not apply exclusion rules — GraphQL returns repo name but no description field in current query | Some tutorial/auto-generated repos may enter Egypt corpus. Fix: add `description` to GraphQL query and apply patterns post-parse |
| **E-3: bot-only repos** | Not implemented in any script — requires inspecting commit author logins for each commit, which is expensive | Some automated pipeline repos may enter the corpus. Estimated impact: low in JS/TS ecosystem. Recommended mitigation: flag repos where >95% of commits are from `[bot]` accounts during Stage 4 (signal detection), and remove them then |
| **`filter_audit.csv` in GraphQL Stage2c** | `stage2c_fast_graphql.py` does not produce an audit log | Rejected repos cannot be traced. Fix: collect rejections in `process_batch_data()` and save to a CSV at the end |
| **Snapshot date bound in Stage2c GraphQL** | `STUDY_SNAPSHOT_DATE` bound is applied to `pushedAt` only, not enforced as `until` on commit history | Commit counts may include commits after the snapshot. Impact: minor, since `history { totalCount }` counts all commits; we are using it only as a ≥10 check |

### 4.3 Not yet aligned — pipeline stages not started

The scripts only cover Stages 1 and 2. Stages 3–7 from the methodology have no scripts yet:

| Stage | Description | Status |
|-------|-------------|--------|
| Stage 3: Size stratification | `size_stratum` is computed inline — no dedicated validation or rebalancing script | Column exists, but no stratum balance check or minimum-N enforcement |
| Stage 4: Multi-signal detection | No script exists | **Not started** |
| Stage 5: Data infrastructure | No SQLite schema or ingestion script | **Not started** |
| Stage 6: Validation | No manual sampling or precision estimation script | **Not started** |
| Stage 7: Metrics & analysis | No analysis notebooks or metric calculation scripts | **Not started** |

---

## 5. Known Gaps — Not Yet Implemented

Listed in priority order (highest impact first):

### ~~Gap 1 — Stage 1 performance~~ ✅ Fixed
`stage1_fast_graphql.py` now exists. Use it instead of `stage1_corpus_build.py`.
See Section 3 for the dedicated entry.

### Gap 2 — Contributor count missing from GraphQL Stage2c (I-5)
**Problem**: `stage2c_fast_graphql.py` skips the ≥2-contributors check.  
**Fix**: After `stage2c_fast_graphql.py` finishes, run a short post-processing script that makes one REST call per repo in `egypt_corpus.csv` to verify contributor count and drops any with < 2.

### Gap 3 — Exclusion rules E-1, E-2, E-4 missing from GraphQL Stage2c
**Problem**: Tutorial and auto-generated repos are not excluded by the GraphQL version.  
**Fix**: Add `description` to the GraphQL query and apply the same regex patterns in `process_batch_data()`.

### Gap 4 — Exclusion rule E-3 (bot-only repos) not implemented anywhere
**Problem**: Repos where >95% of commits are from bot accounts should be excluded but currently aren't.  
**Fix**: Handle during Stage 4 (signal detection). When scanning commits for agent signals, track `bot_commit_ratio` per repo. Flag and remove repos above 0.95 before final analysis.

### Gap 5 — Stage 4: Multi-signal detection (not started)
This is the core of the thesis. The full detection script needs to implement all 6 signal types from `SHARED_CORPUS_METHODOLOGY.md` Section 6, and produce `signals.csv` and `monthly_metrics.csv`.

### Gap 6 — Stage 5: SQLite ingestion (not started)
The methodology calls for a `signals.db` SQLite database. Currently everything is in CSVs. A schema-creation and ingestion script is needed before Stage 7 analysis.

---

## 6. Running Order

Run scripts in this exact sequence. Do not skip the manual review step.

```
1. python scripts/stage1_fast_graphql.py         ← ~15 minutes
   (NOT stage1_corpus_build.py — ~1.5 hours)
   → produces: base_jsts_corpus_pilot.csv, filter_audit.csv, pull_log.jsonl

2. python scripts/stage2a_egypt_seed_discovery_v2.py
   → produces: egypt_seed_candidates.csv
   ⚠️  STOP: manually review egypt_seed_candidates.csv
       Remove false positives before continuing.

3. python scripts/Stage2b_snowball_expansion.py
   → reads:    egypt_seed_candidates.csv  (cleaned)
   → produces: egypt_snowball_candidates.csv

4. python scripts/combine_accounts.py
   → reads:    egypt_seed_candidates.csv + egypt_snowball_candidates.csv
   → produces: egypt_combined_accounts.csv

5. python scripts/stage2c_fast_graphql.py   ← use this one
   (NOT Stage2c_egypt_corpus_direct_pull.py — too slow)
   → reads:    egypt_combined_accounts.csv
   → produces: egypt_corpus.csv

── Stages 3–7 scripts not yet written ──────────────────────────
6. [TODO] Stage 3 validation: verify stratum balance
7. [TODO] Stage 4: multi-signal detection → signals.csv
8. [TODO] Stage 5: SQLite ingestion
9. [TODO] Stage 6: validation (manual precision check)
10.[TODO] Stage 7: metrics & analysis notebooks
```

---

*Reference version 1.0 — reflects scripts as of 2026-09-25.*
