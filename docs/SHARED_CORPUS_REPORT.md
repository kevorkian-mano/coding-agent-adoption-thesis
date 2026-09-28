# Shared Corpus Methodology Report
## Coding Agent Adoption Research Cluster


---

## Contents

1. [Overview](#1-overview)
2. [Repository Filtering Criteria](#2-repository-filtering-criteria)
3. [Size Stratification](#3-size-stratification)
4. [API Query Parameters](#4-api-query-parameters)
5. [Corpus Construction Pipeline](#5-corpus-construction-pipeline)
6. [Agent Adoption Detection Signals](#6-agent-adoption-detection-signals)
7. [Canonical Metric Definitions](#7-canonical-metric-definitions)
8. [Shared Output Schema](#8-shared-output-schema)
9. [Reproducibility Commitments](#9-reproducibility-commitments)
10. [Known Limitations](#10-known-limitations)

---

## 1. Overview

This document describes the shared corpus construction methodology agreed upon by the six-student research cluster studying coding agent adoption on GitHub. All six students focus on **Egyptian developers** and study how coding agents are adopted within their repositories. Each student covers a different programming language ecosystem, but all six apply the same repository filtering rules, the same Egyptian developer discovery pipeline, the same detection signals, and the same metric definitions — so findings are directly comparable across ecosystems.

### Research Cluster Topics

| Topic | Ecosystem | Package Manager |
|-------|-----------|----------------|
| 1 | — | — |
| **2** | **JavaScript / TypeScript** | **npm** |
| 3 | — | — |
| 4 | — | — |
| 5 | — | — |
| 6 | — | — |

### Study Snapshot Date

All data collection is bounded by **2026-09-01**. No commits, pull requests, or repository events after this date are included, ensuring the corpus is frozen and reproducible.

---

## 2. Repository Filtering Criteria

Every repo in every topic's corpus must pass all of the following rules. These rules are applied in order; a repo that fails any rule is excluded and logged with the rule ID that rejected it.

### 2.1 Inclusion Criteria

| Rule | Criterion | Rationale |
|------|-----------|-----------|
| I-1 | Not a fork | Forks inherit the parent's commit history, which would double-count agent signals |
| I-2 | Not archived | Archived repos receive no new commits; adoption trend analysis would be skewed |
| I-3 | Not disabled | Disabled repos are inaccessible via the API |
| I-4 | ≥ 10 commits (within snapshot window) | Ensures the repo has meaningful development activity |
| I-5 | ≥ 2 distinct contributors | Ensures the repo is not a solo personal project |
| I-6 | Last push ≥ 2023-01-01 | Ensures the repo was active during the coding agent adoption period |
| I-7 | Created before 2026-09-01 | Ensures the repo existed before the study snapshot date |
| I-8 | Primary language matches topic ecosystem | Each topic studies only repos in its target language |
| I-9 | Ecosystem manifest file present at root | e.g. `package.json` for npm; confirms the repo uses the target ecosystem |

### 2.2 Exclusion Criteria

| Rule | Criterion | Rationale |
|------|-----------|-----------|
| E-1 | Name/description does not match tutorial/course patterns | Tutorial repos are not production software projects |
| E-2 | Not a completely empty repo (stars=0, forks=0, commits<5) | Empty or placeholder repos add noise |
| E-3 | Not a known bot account owner | Bot-owned repos distort contribution and commit metrics |
| E-4 | Name does not match auto-generated patterns with empty description | Auto-generated repos from scaffolding tools are not real projects |
| E-5 | `size_kb > 0` | GitHub reports size=0 for repos with no committed files — structurally empty |
| E-6 | Description is not empty OR stars ≥ 1 | Repos with no description and zero stars are almost always abandoned placeholders |

### 2.3 Filter Audit Log

Every repo checked — whether it passes or fails — is logged to `filter_audit.csv` with the rule ID that rejected it. This provides full transparency and reproducibility of the filtering decisions.

---

## 3. Size Stratification

Repos are stratified by star count into three groups. Stars are used as a proxy for project visibility and community size. Stratification is applied **after** filtering — stars are not a filter criterion.

| Stratum | Star range | Interpretation |
|---------|-----------|----------------|
| Small | 0 – 50 stars | Emerging or niche projects |
| Medium | 51 – 500 stars | Established community projects |
| Large | > 500 stars | Widely-used open source projects |

> **Note on search cap:** GitHub's Search API returns at most 1,000 results per query. A single query sorted by stars would return only large repos. To ensure all strata are represented, the corpus construction runs **three separate search queries** — one per star band — each with its own 1,000-result quota.

---

## 4. API Query Parameters

This section documents the exact parameter values passed to the GitHub API at each stage of corpus construction. These values are fixed across all runs to ensure reproducibility.

### 4.1 Repository Search Parameters (Stage 1)

Three separate search queries are run — one per star band — to ensure all strata are represented.

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `language` | Varies per topic (see table below) | Each topic targets its own ecosystem language(s) |
| `fork` | `false` | Excludes forked repos at source (rule I-1) |
| `stars` | `0..50` / `51..500` / `>500` | Three bands bypass the 1,000-result search cap |
| `pushed` | `>2023-01-01` | Activity window — coding agents began mainstream adoption late 2022 |
| `created` | `<2026-09-01` | Snapshot bound — no repos created after the study window |
| `sort` | `stars` descending | Consistent ordering within each band |
| `per_page` | `100` | Maximum allowed by GitHub Search API |
| `max_pages` | `10` per band per language | Up to 1,000 results per band (API cap) |

**Language and manifest values per topic:**

| Topic | `language` query value(s) | Manifest file (I-9) | Ecosystem |
|-------|--------------------------|---------------------|-----------|
| 1 | — | — | — |
| **2** | `JavaScript`, `TypeScript` | `package.json` | npm |
| 3 | — | — | — |
| 4 | — | — | — |
| 5 | — | — | — |
| 6 | — | — | — |

> **Why 2023-01-01 as the activity cutoff?** GitHub Copilot became generally available in June 2022 and saw rapid adoption through 2023. Starting the window at 2023-01-01 ensures repos were active during the period when agent adoption was measurable.

### 4.2 Repository Verification Parameters (Stage 1, post-search)

After search, each candidate repo is verified with additional API calls:

| Check | Parameter / threshold | API call used |
|-------|-----------------------|---------------|
| Manifest file (I-9) | Ecosystem-specific filename at root (e.g. `package.json`) | `GET /repos/{owner}/{repo}/contents/{manifest}` |
| Language byte share (I-8) | ≥ 50% of total bytes in topic language(s) | `GET /repos/{owner}/{repo}/languages` |
| Commit count (I-4) | ≥ 10 commits before snapshot | `GET /repos/{owner}/{repo}/commits?per_page=1&until=2026-09-01` (Link header trick) |
| Contributor count (I-5) | ≥ 2 distinct contributors | `GET /repos/{owner}/{repo}/contributors?per_page=1` (Link header trick) |
| Repo size (E-5) | `size_kb > 0` | Available free in search result metadata |
| License present | `license != null` | Available free in search result metadata |
| Has CI/CD | `.github/workflows/` directory exists | Collected as a corpus column — not a hard filter |

### 4.3 Egyptian Developer Search Parameters (Stage 2a)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `location` terms (English) | `Egypt`, `Cairo`, `Alexandria`, `Giza` | Major Egyptian cities in English |
| `location` terms (Arabic) | `مصر`, `القاهرة`, `الإسكندرية`, `الجيزة` | Same cities in Arabic — required to avoid undercounting |
| `sort` | `repositories` descending | Prioritises active developers |
| `per_page` | `100` | Maximum per page |
| `max_pages` | `5` per term | 500 results per location term |
| Seed activity filter | `followers ≥ 10` OR `public_repos ≥ 5` | Ensures seed accounts are real, active developers |

### 4.4 Snowball Expansion Parameters (Stage 2b)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `MAX_CONNECTIONS_PER_SEED` | 30 | Followers + following fetched per account per round |
| `MAX_ROUNDS` | 3 | Maximum expansion rounds before stopping |
| `CONNECTIONS_BATCH_SIZE` | 5 | Accounts per GraphQL request |
| Convergence condition | 0 new Egypt-linked accounts found | Stops early if the network is exhausted |
| Location match | Any LOCATION_TERMS substring in profile location | Case-insensitive; English + Arabic |

### 4.5 GraphQL Batch Query Parameters (all stages)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Repos per account | `first: 50` | Balances completeness vs query complexity |
| Repo ordering | `PUSHED_AT DESC` | Fetches most recently active repos first |
| `isFork` | `false` | Excludes forks at query level (rule I-1) |
| `privacy` | `PUBLIC` | Public repos only — private repos inaccessible |
| Accounts per batch | 5–50 depending on stage | Tuned per stage to avoid HTTP 502 timeouts |
| Sleep between batches | 0.3–1.0s | Prevents hitting secondary rate limits |

### 4.6 Shared Constant Values

These values are defined identically in all pipeline scripts:

| Constant | Value | Scope |
|----------|-------|-------|
| `STUDY_SNAPSHOT_DATE` | `2026-09-01` | Shared — all topics |
| `MIN_COMMITS` | `10` | Shared — all topics |
| `MIN_CONTRIBUTORS` | `2` | Shared — all topics |
| `MIN_LAST_PUSH` | `2023-01-01` | Shared — all topics |
| `MIN_LANGUAGE_SHARE` | `0.50` | Shared — all topics (language name differs per topic) |
| `MAX_ROUNDS` | `3` | Shared — all topics (snowball expansion) |
| `MAX_CONNECTIONS_PER_SEED` | `30` | Shared — all topics (snowball expansion) |
| `TOPIC_ID` | 1–6 (varies per topic) | Per-topic |
| `ECOSYSTEM` | e.g. `npm`, `pip`, `cargo` (varies per topic) | Per-topic |
| `LANGUAGES` | e.g. `["JavaScript","TypeScript"]` (varies per topic) | Per-topic |
| `MANIFEST_FILE` | e.g. `package.json` (varies per topic) | Per-topic |

---

## 5. Corpus Construction Pipeline

Each topic follows the same seven-step sequence to build its corpus:

```
Step 1: Search GitHub for repos matching ecosystem + activity criteria
Step 2: Apply fast filters (fork, archived, language) from search result metadata
Step 3: Verify ecosystem manifest file exists (one API call per repo)
Step 4: Check language byte-share ≥ 50% (confirms language is primary, not incidental)
Step 5: Approximate commit count (Link header trick — no full history traversal)
Step 6: Get contributor count (Link header trick)
Step 7: Apply exclusion rules (tutorial, empty, auto-generated patterns)
```

Steps 2–7 are logged to `filter_audit.csv` with per-rule counts, enabling audit of how many repos each criterion removes.

### Egyptian Developer Sub-Corpus (all 6 topics)

All six topics construct an Egyptian developer sub-corpus alongside the global base corpus. The process is identical across topics — the only difference is the target language and manifest file used in Stage 2c.

1. **Seed discovery (Stage 2a):** Search GitHub users by Egypt-linked location terms (both English and Arabic: `Egypt`, `Cairo`, `Alexandria`, `Giza`, `مصر`, `القاهرة`, `الإسكندرية`, `الجيزة`), then filter by activity (≥10 followers OR ≥5 public repos). This produces the seed list of confirmed Egyptian developer accounts.

2. **Snowball expansion (Stage 2b):** For each seed account, pull their followers and following lists. Any new Egypt-linked accounts discovered become the next round's frontier. Runs up to 3 rounds or until no new accounts are found (convergence). This expands coverage beyond accounts discoverable by location search alone.

3. **Corpus pull (Stage 2c):** Combine seed + snowball accounts, then for each account pull their public repositories and apply the shared filtering criteria (I-1 to I-9, E-1 to E-6) using the topic's own language and manifest file.

The resulting `egypt_corpus.csv` is merged with the global `base_corpus.csv` in Stage 3, producing a `unified_corpus.csv` with a `corpus_source` column (`base` / `egypt` / `both`) that enables direct comparison of Egyptian developer adoption rates against the global sample. This comparison is a research question shared by all six topics.

---

## 6. Agent Adoption Detection Signals

The same signal taxonomy is applied across all six topics. A repository is classified as `agent_adopted = True` if **at least one** of the following signals is detected in the study window.

### 6.1 Commit-Level Signals

| Signal | Detection method |
|--------|----------------|
| Commit trailer: `Co-Authored-By: GitHub Copilot` | Regex on commit message |
| Commit trailer: `Co-Authored-By: cursor` | Regex on commit message |
| Commit trailer: `Generated with Claude Code` | Regex on commit message |
| Commit authored by a known bot login | Author login lookup |

### 6.2 Repository Configuration Signals

| Signal | File path checked |
|--------|------------------|
| GitHub Copilot instructions | `.github/copilot-instructions.md` |
| Cursor IDE configuration | `.cursor/` directory |
| Claude Code configuration | `CLAUDE.md` |
| Continue.dev configuration | `.continue/` directory |
| Codeium configuration | `.codeium/` directory |

### 6.3 Pull Request Signals

| Signal | Detection method |
|--------|----------------|
| PR body contains agent marker | Regex on PR description |
| PR label matches agent pattern | Label name lookup |
| PR branch name matches agent pattern | Branch name regex (e.g. `copilot/...`, `cursor/...`) |

### 6.4 Dependency Signals (ecosystem-specific — varies per topic)

Each topic checks for AI/agent-related packages in its ecosystem's manifest file. The signal logic is the same; only the package names differ.

| Topic | Ecosystem | Packages checked |
|-------|-----------|-----------------|
| **2** | npm | `@anthropic-ai/sdk`, `openai`, `@github-copilot/...` |
| Others | pip / cargo / etc. | Equivalent packages in each ecosystem |

The `first_detected_at` date is recorded as the earliest date any signal appears — this is used as the adoption date for before/after metric comparisons.

---

## 7. Canonical Metric Definitions

All six topics compute the same eight metrics using identical formulas, measured over a **±90-day window** around `first_detected_at`.

| # | Metric | Formula |
|---|--------|---------|
| M1 | Commit frequency | Commits per week (90 days before vs 90 days after adoption) |
| M2 | PR merge time | Median days from PR open to merge |
| M3 | Contributor growth | Distinct contributors (before vs after) |
| M4 | Issue close rate | Issues closed / issues opened per month |
| M5 | Code churn | (Lines added + lines deleted) per commit |
| M6 | PR acceptance rate | Merged PRs / total closed PRs |
| M7 | Commit message length | Median characters per commit message |
| M8 | Time to first review | Median hours from PR open to first review comment |

For repos where `agent_adopted = False`, metrics are computed over the equivalent trailing 90-day window to provide a comparable baseline.

### 7.2 Extended Metrics (shared — all 6 topics)

These metrics go beyond the core M1–M8 set and are collected by all six topics during Stage 4 (detection). They require no extra API calls beyond what detection already does.

| # | Metric | How collected | Why it matters |
|---|--------|--------------|----------------|
| M9 | `agent_name` | Which agent triggered detection (Copilot / Cursor / Claude / other) | Per-agent adoption breakdown — which tool dominates each ecosystem? |
| M10 | `signal_count` | Number of distinct signal types detected | Strength of evidence; 1 signal = weak, 3+ = strong. Used as a confidence filter |
| M11 | `multi_agent` | Boolean: >1 distinct agent detected | Identifies repos that use multiple agents or switched tools |
| M12 | `time_to_adoption` | Days from `created_at` to `first_detected_at` | Do newer repos adopt agents faster than older ones? |
| M13 | `adoption_month` | Calendar month of first signal (e.g. `2024-03`) | Temporal trend chart — when did adoption spike? |
| M14 | `has_github_actions` | Boolean: `.github/workflows/` directory exists | CI/CD as a covariate — automated repos are more likely to show agent signals |
| M15 | `corpus_source` | base / egypt / both | Egypt vs global adoption rate comparison — core cross-topic RQ |

### 7.3 Ecosystem-Specific Extended Metrics (per topic)

Each topic may add metrics specific to its ecosystem's package structure. These are not required of all topics but must follow the shared naming convention.

**Topic 2 (npm):**

| # | Metric | How collected | Why it matters |
|---|--------|--------------|----------------|
| M16 | `dependency_count` | Count of `dependencies` in `package.json` | Does agent adoption correlate with project complexity? |
| M17 | `devdep_count` | Count of `devDependencies` in `package.json` | Agents often add dev tooling — does devDep count grow after adoption? |

> **M9–M15** are derived at Stage 4 with no extra API calls beyond detection.  
> **M14** requires one file-existence check per repo (`.github/workflows/`).  
> **M16–M17** require fetching and parsing the manifest file — one API call per repo.

---

## 8. Shared Output Schema

Every topic produces output files that follow the same column schema, enabling cluster-level analysis.

### corpus.csv (shared columns — all 6 topics)

| Column | Type | Description |
|--------|------|-------------|
| `full_name` | string | `owner/repo` — primary key |
| `primary_language` | string | Detected primary language |
| `stars` | int | Star count at snapshot date |
| `size_stratum` | string | small / medium / large |
| `has_license` | bool | Whether a license file is present |
| `has_github_actions` | bool | Whether `.github/workflows/` exists (M14) |
| `agent_adopted` | bool | True if any signal detected |
| `first_detected_at` | date | Date of earliest signal |
| `agent_name` | string | Which agent triggered detection (M9) |
| `signal_count` | int | Number of distinct signal types triggered (M10) |
| `multi_agent` | bool | More than one agent detected (M11) |
| `time_to_adoption` | int | Days from repo creation to first signal (M12) |
| `adoption_month` | string | Calendar month of first signal e.g. `2024-03` (M13) |
| `corpus_source` | string | base / egypt / both (M15) |
| `seed_account` | string | Egyptian developer login (egypt/both rows only) |
| `topic_id` | int | Which topic (1–6) |
| `ecosystem` | string | Package manager |

### corpus.csv (ecosystem-specific columns — per topic)

Each topic appends columns specific to its ecosystem. Topic 2 example:

| Column | Type | Description |
|--------|------|-------------|
| `dependency_count` | int | Count of production dependencies in `package.json` (M16) |
| `devdep_count` | int | Count of dev dependencies in `package.json` (M17) |

### filter_audit.csv (shared — all topics)

One row per repo checked, with `passed_all` (bool) and `failed_rule` (rule ID) columns.

### signals.csv (shared — all topics, one row per detected signal)

| Column | Type | Description |
|--------|------|-------------|
| `full_name` | string | Repo the signal was found in |
| `signal_type` | string | commit_trailer / config_file / pr_body / dependency / branch_name |
| `agent_name` | string | Which agent the signal points to |
| `detected_at` | date | Date the signal-bearing commit/PR/file appeared |
| `evidence` | string | The raw string that triggered the match (commit trailer text, file path, etc.) |

---

## 9. Reproducibility Commitments

All six students adhere to the following rules to ensure reproducibility:

1. **Snapshot date fixed:** `STUDY_SNAPSHOT_DATE = "2026-09-01"` — no data after this date
2. **All API calls logged** to `pull_log.jsonl` with timestamp, endpoint, parameters, and response code
3. **Random seed fixed** for any sampling operations
4. **Filter audit logged** for every repo with the rule that excluded it
5. **GitHub token not committed** — set via environment variable only
6. **All shared constants** (`MIN_COMMITS`, `MIN_CONTRIBUTORS`, `MIN_LAST_PUSH`, `STRATA_BOUNDS`) are defined identically across all six topic scripts

---

## 10. Known Limitations

| Limitation | Scope | Mitigation |
|-----------|-------|-----------|
| GitHub Search caps at 1,000 results per query | All topics | Star-band queries run separately per stratum |
| Contributor count capped at 500 by GitHub API | All topics | Sufficient for MIN_CONTRIBUTORS = 2 check |
| Manifest file check skipped in Egypt sub-corpus (Stage 2c) | All topics | Documented; primaryLanguage used as proxy in Stage 2c |
| Commit count not fetched in GraphQL batch queries | All topics | `pushedAt` recency used as activity proxy |
| Location-based user discovery misses developers with no location set | All topics | Snowball expansion partially compensates by discovering unlisted accounts through network connections |
| Snowball expansion limited to 3 rounds | All topics | Convergence detected; additional rounds yield diminishing returns |
| Detection signals based on publicly observable markers only | All topics | Private/implicit agent use cannot be detected — acknowledged as a study boundary |
| `corpus_source = "egypt"` rows have less complete metadata than base rows | All topics | Base-corpus rows kept where overlap exists; Egypt-only rows documented as partial |
