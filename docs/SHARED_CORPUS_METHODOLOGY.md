# Shared Corpus & Metrics Methodology
## Coding Agent Adoption Research Cluster — All 6 Topics

**Version**: 1.0  
**Applies to**: All students in the "Coding Agent Adoption on GitHub" research cluster  
**Purpose**: Unify the repository pulling pipeline, filtering criteria, and metric definitions so that findings across topics are directly comparable

---

## Table of Contents

1. [Cluster Overview](#1-cluster-overview)
2. [Shared Filtering Criteria (Universal Rules)](#2-shared-filtering-criteria-universal-rules)
3. [Ecosystem-Specific Parameters](#3-ecosystem-specific-parameters)
4. [Size Stratification](#4-size-stratification)
5. [GitHub API Pull Sequence](#5-github-api-pull-sequence)
6. [Detection Signal Taxonomy](#6-detection-signal-taxonomy)
7. [Canonical Metric Definitions](#7-canonical-metric-definitions)
8. [Output Schemas (Shared Contract)](#8-output-schemas-shared-contract)
9. [Rate Limiting & Reproducibility Rules](#9-rate-limiting--reproducibility-rules)
10. [What Each Topic Adds on Top](#10-what-each-topic-adds-on-top)

---

## 1. Cluster Overview

Six students independently study coding agent adoption in different package ecosystems on GitHub. Each topic targets one ecosystem but every topic:

- Applies the **same repository filtering rules** (Section 2)
- Applies the **same detection signal set** (Section 6)
- Computes the **same metrics** using the **same formulas** (Section 7)
- Produces **output files that match the same schema** (Section 8)

This makes cross-ecosystem comparison possible at the cluster level even though each thesis focuses on one ecosystem.

### Topic Assignments

| Topic | Ecosystem | Package Manager | Student |
|-------|-----------|----------------|---------|
| 1 | — | — | — |
| **2** | **JavaScript / TypeScript** | **npm** | **Manuel Youssef Haik Kevorkian** |
| 3 | — | — | — |
| 4 | — | — | — |
| 5 | — | — | — |
| 6 | — | — | — |

> Fill in other topics as they are confirmed. The methodology below is written to be ecosystem-agnostic; ecosystem-specific parameters are isolated in Section 3.

---

## 2. Shared Filtering Criteria (Universal Rules)

These rules apply to **every topic** regardless of ecosystem. A repository must pass **all** of the following to be included in any topic's corpus.

### 2.1 Inclusion Criteria

| # | Rule | Rationale |
|---|------|-----------|
| I-1 | Repository is **not a fork** (`fork == false`) | Forks inherit the parent's commit history, which would double-count agent signals |
| I-2 | Repository is **not archived** (`archived == false`) | Archived repos receive no new commits; adoption trend analysis would be skewed |
| I-3 | Repository is **not disabled** (`disabled == false`) | Disabled repos are inaccessible for full data pull |
| I-4 | **At least 10 commits** total in the default branch | Filters trivially small or test repositories |
| I-5 | **At least 2 distinct commit authors** | Filters single-developer throw-away repos and bot-only repos |
| I-6 | **Last push date ≥ 2023-01-01** | Ensures the repo was active during the modern coding agent era |
| I-7 | **Created date ≤ study snapshot date** | Obvious: repo must exist |
| I-8 | Primary language matches the topic's ecosystem (see Section 3) | Scopes the corpus to the target ecosystem |
| I-9 | Package manager manifest present at repository root (see Section 3) | Confirms the repo actually uses the target package manager |

### 2.2 Exclusion Criteria

| # | Rule | Rationale |
|---|------|-----------|
| E-1 | Repository name or description matches known **tutorial/course patterns** (`awesome-*`, `*-tutorial`, `*-course`, `*-bootcamp`, `*-exercises`, `*-solutions`) | These repos are collections, not real projects |
| E-2 | Repository has **0 stars AND 0 forks AND < 5 commits** | Extremely low-signal repos inflate the corpus without contributing to adoption analysis |
| E-3 | More than **95% of commits are by a single bot account** | Bot-only repos are not developer-adopting-agent; they are automated pipelines |
| E-4 | Repository name matches `^[a-z0-9]+-[a-z0-9]+-[a-z0-9]+$` with a generic description | Common pattern for auto-generated GitHub Action repos |

> **Important**: E-1 through E-4 are applied **after** the API pull, during the cleaning step. Do not pre-filter with the search query — collect first, clean second, to keep the pull auditable.

### 2.3 Snapshot Date

All topics use the **same snapshot date** for the study window end:

```
STUDY_SNAPSHOT_DATE = 2026-09-01
```

All corpus pulls and metric calculations are bounded by this date. Commits or PRs after this date are excluded. This ensures cross-topic comparability.

---

## 3. Ecosystem-Specific Parameters

Each topic fills in the following four parameters. Everything else in this document uses these parameters without change.

### Template

```yaml
topic_id: <1–6>
primary_languages:          # GitHub Linguist language names (exact strings)
  - "<Language>"
manifest_filename:          # File that must exist at repo root
  - "<filename>"
search_query_language:      # Value(s) for `language:` in GitHub Search
  - "<language>"
additional_search_terms:    # Optional extra qualifiers (e.g. topic:npm)
  - "<term>"
```

### Topic 2 — JavaScript / TypeScript / npm

```yaml
topic_id: 2
primary_languages:
  - "JavaScript"
  - "TypeScript"
manifest_filename:
  - "package.json"
search_query_language:
  - "javascript"
  - "typescript"
additional_search_terms: []
```

**Language rule for Topic 2**: A repository qualifies if its GitHub-detected primary language is `JavaScript` OR `TypeScript`. Repos where JS/TS is secondary (e.g. a Python project with some JS) are excluded.

**Manifest rule for Topic 2**: `package.json` must be present at the root of the default branch (not in a subdirectory). This confirms npm as the package manager.

---

## 4. Size Stratification

All topics use the **same three strata** defined by star count. Stars are fetched at pull time and recorded; a repo's stratum is fixed at the snapshot date.

| Stratum | Star Count (at snapshot) | Label in data |
|---------|--------------------------|---------------|
| Small   | 0 – 50                   | `small`       |
| Medium  | 51 – 500                 | `medium`      |
| Large   | > 500                    | `large`       |

**Why stars?** The baseline study ("Agentic Much?") uses stars as the primary size proxy. It correlates with community visibility, contributor count, and maintenance activity. Using the same proxy ensures our results are comparable with the baseline.

**No upsampling**: If a topic's ecosystem is naturally skewed (e.g. very few large repos), strata are reported as-is with statistical power caveats. Never oversample to compensate.

**Minimum per stratum**: Aim for ≥ 500 repositories per stratum per topic for sufficient statistical power (α = 0.05, power = 0.80 at a 5 pp minimum detectable effect).

---

## 5. GitHub API Pull Sequence

All topics follow this exact sequence. Deviations must be documented.

### Step 1 — Search (Repository Discovery)

**Endpoint**: `GET https://api.github.com/search/repositories`

**Query construction**:
```
q = language:<L1> language:<L2> ... pushed:>2023-01-01 fork:false
sort = stars
order = desc
per_page = 100
```

- Run one query per language in `search_query_language`
- Paginate until no more results or until the target sample size is reached
- De-duplicate by `repo_id` (repos that match multiple language queries appear once)
- **Record the exact query string and timestamp for each page** in `pull_log.jsonl`

**Fields to capture per repo**:

| Field | GitHub API key | Notes |
|-------|---------------|-------|
| `repo_id` | `id` | Stable numeric ID |
| `owner_login` | `owner.login` | |
| `repo_name` | `name` | |
| `full_name` | `full_name` | `owner/repo` format |
| `primary_language` | `language` | GitHub Linguist primary |
| `stars` | `stargazers_count` | At pull time |
| `forks` | `forks_count` | |
| `created_at` | `created_at` | ISO 8601 |
| `pushed_at` | `pushed_at` | ISO 8601 |
| `default_branch` | `default_branch` | |
| `archived` | `archived` | |
| `fork` | `fork` | |
| `disabled` | `disabled` | |
| `description` | `description` | For E-1 cleaning |
| `topics` | `topics` | Array |
| `size_kb` | `size` | GitHub's size unit |
| `open_issues` | `open_issues_count` | |

### Step 2 — Manifest Verification

For each repo from Step 1, verify the package manager manifest exists at root:

**Endpoint**: `GET https://api.github.com/repos/{owner}/{repo}/contents/{manifest}`

- If HTTP 200 → manifest present → `has_manifest = true`
- If HTTP 404 → `has_manifest = false` → repo is excluded (rule I-9)
- Record response status in `manifest_check_log.jsonl`

> **Optimization**: Use the GraphQL API to batch manifest checks for up to 100 repos per request, reducing API call count significantly. See Section 5 GraphQL template below.

### Step 3 — Commit Count & Author Count

**Endpoint**: `GET https://api.github.com/repos/{owner}/{repo}/commits`  
**Params**: `per_page=1&sha={default_branch}`  
**Extract**: `Link` response header, last page number = total commit count approximation

For exact counts and author data, use the **Contributors endpoint**:  
`GET https://api.github.com/repos/{owner}/{repo}/contributors?per_page=100`

- `total_commits` = sum of `contributions` across all contributors
- `contributor_count` = number of entries returned
- Apply rules I-4 and I-5

### Step 4 — Apply Filtering & Assign Stratum

After Steps 1–3, apply all inclusion/exclusion rules from Section 2. Record each repo's filter outcome:

```csv
repo_id, full_name, passed_all, failed_rule, size_stratum
```

This audit log is required. It lets you reproduce the corpus exactly and justify the final N.

### Step 5 — Commit Pull (Signal Detection Feed)

For each repo that passes all filters:

**Endpoint**: `GET https://api.github.com/repos/{owner}/{repo}/commits`  
**Params**: `per_page=100&sha={default_branch}&until={STUDY_SNAPSHOT_DATE}T00:00:00Z`  
Paginate through all pages.

**Fields to capture per commit**:

| Field | GitHub API key | Notes |
|-------|---------------|-------|
| `repo_id` | — | Join key |
| `commit_sha` | `sha` | |
| `author_login` | `author.login` | GitHub account; nullable for unlinked authors |
| `author_email` | `commit.author.email` | From git config |
| `author_name` | `commit.author.name` | From git config |
| `committed_at` | `commit.author.date` | ISO 8601 |
| `message` | `commit.message` | Full message, not truncated |
| `additions` | `stats.additions` | Requires separate call per commit (see note) |
| `deletions` | `stats.deletions` | Same |
| `changed_files` | `stats.total` | Same |
| `parents_count` | `len(parents)` | 2+ = merge commit |

> **Note on stats**: The list commits endpoint does not return `stats`. You must call `GET /repos/{owner}/{repo}/commits/{sha}` individually per commit to get additions/deletions. Only do this for commits that are already flagged with a signal (lazy loading) unless your RQ explicitly requires size metrics for all commits.

### Step 6 — Pull Request Pull

**Endpoint**: `GET https://api.github.com/repos/{owner}/{repo}/pulls`  
**Params**: `state=all&per_page=100&sort=created&direction=asc`  
Paginate through all pages. Filter out PRs created after `STUDY_SNAPSHOT_DATE`.

**Fields to capture per PR**:

| Field | GitHub API key |
|-------|---------------|
| `repo_id` | — |
| `pr_number` | `number` |
| `author_login` | `user.login` |
| `created_at` | `created_at` |
| `merged_at` | `merged_at` |
| `state` | `state` |
| `body` | `body` |
| `labels` | `labels[].name` |
| `head_branch` | `head.ref` |
| `merge_commit_sha` | `merge_commit_sha` |

### Step 7 — File Tree Scan (Config Artifact Detection)

**Endpoint**: `GET https://api.github.com/repos/{owner}/{repo}/git/trees/{sha}?recursive=1`  
Use `HEAD` SHA of the default branch.

Extract the full flat list of file paths. Match against the artifact list in Section 6.3.

> **Alternative for bulk**: Use GH Archive / BigQuery to pull file trees at scale — significantly faster than per-repo API calls for large corpora.

---

### GraphQL Batch Template (Steps 2 + 7 combined)

```graphql
query BatchRepoCheck($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    id
    packageJson: object(expression: "HEAD:package.json") { id }
    claudeMd: object(expression: "HEAD:CLAUDE.md") { id }
    agentsMd: object(expression: "HEAD:AGENTS.md") { id }
    cursorRules: object(expression: "HEAD:.cursorrules") { id }
    aiderConf: object(expression: "HEAD:.aider.conf.yml") { id }
    copilotDir: object(expression: "HEAD:.copilot") { id }
  }
}
```

Run with batched aliases for up to 100 repos per request (GraphQL aliases).

---

## 6. Detection Signal Taxonomy

This is the **complete shared signal set**. Every topic applies all signal types. A repo is labeled `agent_adopted = true` if **any** signal fires.

### 6.1 Commit Trailer Signals

Scan the raw `message` field of every commit. Use **case-insensitive** regex.

| Agent | Pattern | Notes |
|-------|---------|-------|
| Claude Code | `co-authored-by:\s*claude\s+<` | Anthropic trailer |
| Claude Code | `co-authored-by:\s*claude sonnet` | |
| Claude Code | `co-authored-by:\s*claude opus` | |
| Claude Code | `co-authored-by:\s*claude haiku` | |
| GitHub Copilot | `co-authored-by:\s*github-copilot\[bot\]` | |
| Copilot (generic) | `co-authored-by:\s*copilot\s*<` | |
| Aider | `co-authored-by:\s*aider` | |
| Cursor | `co-authored-by:\s*cursor` | |
| Devin | `co-authored-by:\s*devin` | |
| Codex CLI | `co-authored-by:\s*codex` | |
| Generic AI | `generated (with\|by\|using) (claude\|copilot\|cursor\|gpt\|aider\|devin\|codeium\|gemini)` | Match in body, not just trailers |

> Regex must be applied to the **full commit message** including body (not just the first line). Trailers appear after a blank line at the end of the message.

### 6.2 Bot Account Signals

Check `author_login` against the known bot account list.

| Bot Login | Agent |
|-----------|-------|
| `github-copilot[bot]` | GitHub Copilot |
| `copilot[bot]` | GitHub Copilot |
| `aider-bot` | Aider |
| `devin-ai-integration[bot]` | Devin |
| `coderabbitai[bot]` | CodeRabbit |
| `sourcery-ai[bot]` | Sourcery |
| `sweep-ai[bot]` | Sweep |
| `cursor-bot` | Cursor |
| `codiumai[bot]` | Codium AI |
| `greptile-bot` | Greptile |

Match rule: `author_login` (lowercased) **ends with `[bot]`** OR is in the above list.  
Flag: `signal_type = 'bot_account'`

### 6.3 Configuration Artifact Signals

Check the file tree from Step 7 for the following filenames (exact match, case-sensitive as shown, at any path depth unless marked root-only).

| Filename / Path | Agent | Root only? |
|----------------|-------|-----------|
| `CLAUDE.md` | Claude Code | No |
| `AGENTS.md` | Claude Code / OpenAI Codex | No |
| `.cursorrules` | Cursor | Root |
| `.cursor/rules` | Cursor | Root |
| `.aider.conf.yml` | Aider | Root |
| `.aider.model.settings.yml` | Aider | Root |
| `.copilot/` *(directory)* | GitHub Copilot | Root |
| `.github/copilot-instructions.md` | GitHub Copilot | Root |
| `devin.yaml` | Devin | Root |
| `.codeium/` *(directory)* | Codeium | Root |
| `.roomodes` | Roo Code | Root |
| `.clinerules` | Cline | Root |
| `windsurf.config.js` | Windsurf | Root |
| `.windsurfrules` | Windsurf | Root |

Flag: `signal_type = 'config_artifact'`, `agent_name = <agent>`

### 6.4 PR Body Signals

Scan `body` of every PR (case-insensitive regex).

| Pattern | Agent |
|---------|-------|
| `🤖 generated with \[claude code\]` | Claude Code |
| `co-authored-by: github-copilot\[bot\]` | GitHub Copilot |
| `generated by claude` | Claude Code |
| `created by devin` | Devin |
| `opened by sweep` | Sweep |
| `(aider\|cursor\|copilot\|devin\|codeium) (generated\|created\|authored)` | Generic |

Flag: `signal_type = 'pr_body'`

### 6.5 Branch Name Signals

Match `head_branch` of PRs.

| Pattern (regex) | Agent |
|----------------|-------|
| `^copilot\/` | GitHub Copilot |
| `^codex\/` | Codex CLI |
| `^devin\/` | Devin |
| `^sweep\/` | Sweep |
| `^aider\/` | Aider |
| `^cursor\/` | Cursor |

Flag: `signal_type = 'branch_name'`

### 6.6 PR Label Signals

Match `labels` array of PRs.

| Label value (exact, lowercase) | Agent |
|-------------------------------|-------|
| `codex` | Codex CLI |
| `copilot` | GitHub Copilot |
| `ai-generated` | Generic |
| `claude` | Claude Code |

Flag: `signal_type = 'pr_label'`

### 6.7 Signal Aggregation Rules

- A **commit** is `agent_authored = true` if any signal fires on that commit (trailer or bot account).
- A **PR** is `agent_authored = true` if any signal fires on that PR (body, branch, label) OR if its merge commit is `agent_authored`.
- A **repo** is `agent_adopted = true` if any commit, PR, or config artifact signal fires.
- When multiple signals fire on the same entity, record all of them. Do not collapse to one.

---

## 7. Canonical Metric Definitions

These are the exact metric definitions every topic must compute. Use these formulas verbatim. Do not rename metrics.

### M1 — Repository Adoption Rate

```
adoption_rate = count(repos where agent_adopted = true) / count(repos in corpus)
```

Computed at the **full corpus level** and **per stratum**.  
Unit: percentage (0–100). Report with 95% Wilson confidence interval.

### M2 — Commit Agent Ratio (per repo)

```
commit_agent_ratio(repo) = count(commits where agent_authored = true) / count(all commits in repo)
```

Unit: percentage (0–100) per repo.  
Aggregate: report **median** and **IQR** across all repos (distribution is non-normal; do not report mean only).

### M3 — Signal Type Breakdown

```
for each signal_type s:
    signal_rate(s) = count(repos with ≥1 signal of type s) / count(repos in corpus)
```

Reported as a stacked bar. This is used to quantify the undercounting delta (RQ1):

```
undercounting_delta = adoption_rate(all signals) − adoption_rate(co_authored_by_only)
```

Unit: percentage points (pp). Always report in pp, never as a relative % change.

### M4 — Monthly Adoption Rate (Trend)

```
for each calendar month m in [earliest repo creation, STUDY_SNAPSHOT_DATE]:
    active_repos(m) = repos with ≥1 commit in month m
    adopted_repos(m) = active_repos(m) where first_signal_date ≤ last day of m
    monthly_adoption_rate(m) = adopted_repos(m) / active_repos(m)
```

Unit: percentage per month. Plot as a time series with a 3-month rolling average smoothing line.

### M5 — Time to First Agent Commit (Repo Lag)

```
repo_lag(repo) = first_signal_date − repo.created_at
```

Measured in **days**. Only computed for `agent_adopted = true` repos.  
Aggregate: report median and IQR. Plot as CDF.

### M6 — Time to First Agent Commit (Author Lag)

```
author_lag(author) = first_agent_commit_date(author) − first_any_commit_date(author)
```

Measured in **days**. Only computed for authors with ≥1 agent commit.  
Aggregate: report median and IQR. Plot as CDF.

### M7 — Tool Distribution

```
for each agent A:
    tool_share(A) = count(repos where ≥1 signal names agent A) / count(agent_adopted repos)
```

A repo may count toward multiple agents if multiple tools were used.  
Report as a frequency table sorted descending. Visualize as horizontal bar chart.

### M8 — Commit Size (Agent vs. Human)

```
for each commit c:
    commit_size(c) = c.additions + c.deletions
```

Compare `commit_size` distributions:
- `agent_authored = true` commits vs. `agent_authored = false` commits
- Test: Mann-Whitney U  
- Report: median lines-changed for each group, effect size (rank-biserial correlation r)

---

## 8. Output Schemas (Shared Contract)

Every topic must produce the following files with these exact column names and types. This enables cluster-level meta-analysis.

### 8.1 `corpus.csv`

| Column | Type | Description |
|--------|------|-------------|
| `repo_id` | int | GitHub numeric repo ID |
| `full_name` | str | `owner/repo` |
| `primary_language` | str | GitHub Linguist primary language |
| `stars` | int | At snapshot date |
| `forks` | int | At snapshot date |
| `created_at` | ISO date | |
| `pushed_at` | ISO date | Last push before snapshot |
| `contributor_count` | int | |
| `total_commits` | int | In default branch before snapshot |
| `size_stratum` | str | `small` / `medium` / `large` |
| `has_manifest` | bool | Package manager manifest at root |
| `agent_adopted` | bool | ≥1 signal found |
| `topic_id` | int | 1–6, identifies the student's topic |
| `ecosystem` | str | e.g. `npm`, `pypi`, `maven` |

### 8.2 `signals.csv`

| Column | Type | Description |
|--------|------|-------------|
| `repo_id` | int | FK → corpus |
| `entity_type` | str | `commit` / `pr` / `repo` |
| `entity_id` | str | SHA for commits, number for PRs, repo_id for repo-level |
| `signal_type` | str | `commit_trailer` / `bot_account` / `config_artifact` / `pr_body` / `branch_name` / `pr_label` |
| `agent_name` | str | Detected agent name (e.g. `claude_code`, `copilot`, `aider`) |
| `detected_at` | ISO date | Date of the commit/PR/file |
| `raw_match` | str | The exact string that triggered the signal (for auditability) |
| `topic_id` | int | |

### 8.3 `monthly_metrics.csv`

| Column | Type | Description |
|--------|------|-------------|
| `year_month` | str | `YYYY-MM` format |
| `active_repos` | int | Repos with ≥1 commit that month |
| `adopted_repos` | int | Active repos with first_signal_date ≤ end of month |
| `monthly_adoption_rate` | float | 0.0–1.0 |
| `new_adoptions` | int | Repos whose first signal appeared this month |
| `topic_id` | int | |
| `ecosystem` | str | |

### 8.4 `filter_audit.csv`

| Column | Type | Description |
|--------|------|-------------|
| `repo_id` | int | |
| `full_name` | str | |
| `passed_all` | bool | |
| `failed_rule` | str | Rule ID from Section 2 (e.g. `I-4`, `E-1`), null if passed |
| `topic_id` | int | |

---

## 9. Rate Limiting & Reproducibility Rules

### 9.1 API Rate Limits

| API | Limit | Strategy |
|-----|-------|----------|
| GitHub REST (authenticated) | 5,000 req/hr | Respect `X-RateLimit-Remaining`; sleep until `X-RateLimit-Reset` when < 100 remaining |
| GitHub GraphQL | 5,000 points/hr | Each node costs 1 point; batch where possible |
| GitHub Search API | 30 req/min | Add 2s delay between search pages |
| GH Archive / BigQuery | No hard limit | Cache all results locally; never re-query the same range twice |

### 9.2 Reproducibility Requirements

- **Log every API call** to `pull_log.jsonl` with: timestamp, endpoint, params, HTTP status, response size
- **Pin your snapshot date** (`STUDY_SNAPSHOT_DATE = 2026-09-01`) in all scripts as a constant
- **Store raw API responses** in a `raw/` directory before parsing — parsing bugs can be fixed without re-pulling
- **Commit your corpus CSVs** to the repository so results are reproducible without re-running the pull
- **Record your GitHub API token scope** (must be public repo read access only — no write scopes)

### 9.3 Shared Constants

All topics must use these constants identically:

```python
STUDY_SNAPSHOT_DATE = "2026-09-01"
MIN_COMMITS        = 10
MIN_CONTRIBUTORS   = 2
MIN_LAST_PUSH      = "2023-01-01"
STRATA_BOUNDS      = {"small": (0, 50), "medium": (51, 500), "large": (501, None)}
ALPHA              = 0.05
POWER_TARGET       = 0.80
```

---

## 10. What Each Topic Adds on Top

The above is the **shared base**. Each topic adds its own contribution on top:

| Addition | Who adds it | Where documented |
|----------|------------|-----------------|
| Egyptian developer sub-corpus (seed + snowball) | Topic 2 (Manuel) | `METHODOLOGY.md` Stage 2 |
| Community comparison statistical tests (RQ2) | Topic 2 (Manuel) | `METHODOLOGY.md` Stage 7 |
| Ecosystem-specific additional signals | Each topic if applicable | Each topic's own METHODOLOGY.md |
| Additional RQs beyond adoption rate | Each topic | Each topic's own METHODOLOGY.md |

Topics should **not** alter the shared metrics defined in Section 7 or the output schemas in Section 8. Additions go in new columns or new files, not replacements.

---

## Appendix A — Agent Name Normalization

When writing to `signals.csv`, normalize `agent_name` to these canonical lowercase strings:

| Canonical name | Covers |
|---------------|--------|
| `claude_code` | Claude Code, claude-code, Anthropic Claude |
| `copilot` | GitHub Copilot, copilot[bot] |
| `cursor` | Cursor, cursor-bot |
| `aider` | Aider, aider-bot |
| `devin` | Devin, devin-ai |
| `codeium` | Codeium, codeium[bot] |
| `sweep` | Sweep, sweep-ai[bot] |
| `coderabbit` | CodeRabbit, coderabbitai[bot] |
| `sourcery` | Sourcery, sourcery-ai[bot] |
| `codex_cli` | Codex CLI, openai codex |
| `greptile` | Greptile |
| `cline` | Cline |
| `roo_code` | Roo Code, Roo Cline |
| `windsurf` | Windsurf |
| `unknown` | Signal fired but agent identity unclear |

---

## Appendix B — Undercounting Illustration

This diagram illustrates how multi-signal detection compares to single-signal (Co-Authored-By only):

```
Repos in corpus: 10,000

Single-signal only (Co-Authored-By):
  Detected as adopted: 1,800  →  18.0%

Multi-signal (all types):
  Commit trailers:      1,800
  Bot accounts:         +400  (not caught by trailers)
  Config artifacts:     +600  (not caught by trailers or bots)
  PR body/branch/label: +150
  ─────────────────────────
  Total detected:       2,950  →  29.5%

Undercounting delta: 29.5% − 18.0% = 11.5 pp
```

The exact numbers will vary by ecosystem. This is the contribution of the undercounting sub-question in RQ1.

---

*Document version 1.0 — authored by Topic 2 for cluster-wide alignment.*  
*All 6 topics should review and propose amendments before data collection begins.*
