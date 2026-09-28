# Methodology: Coding Agent Adoption in JavaScript/TypeScript/npm

**Thesis**: Coding Agent Adoption, Coding Agent Adoption Research Cluster

---



---

## 1. Research Questions

### RQ1 — Adoption Rate & Trend (+ Undercounting)
> *What is the rate and trend of coding agent adoption in JavaScript/TypeScript/npm repositories on GitHub, and by how much does single-signal detection undercount actual adoption?*

**Sub-questions:**
- What percentage of JS/TS repositories show at least one coding agent signal by the end of the study window?
- How has the monthly adoption rate changed over time (2023–2026)?
- What is the gap between single-signal detection and multi-signal detection (the undercounting delta)?

### RQ2 — Egyptian Developer Community Comparison
> *How does coding agent adoption among Egyptian JavaScript/TypeScript developers compare to the general JS/TS GitHub population, when stratified by repository size?*

**Sub-questions:**
- Is the adoption gap statistically significant at each size stratum (small/medium/large)?
- Does the temporal adoption curve differ (earlier or later inflection points)?
- Does the tool distribution (Claude Code, Copilot, Cursor, etc.) differ between Egyptian and general populations?

---



| Term | Definition |
|------|-----------|
| **Coding Agent** | An AI tool that autonomously generates, commits, or reviews code, typically operated through an agentic loop (plan → act → verify). Includes: Claude Code, GitHub Copilot, Cursor, Aider, Codeium, Codex CLI, Devin, and ~59 others. |
| **Agent Adoption** | A repository or author is considered to have *adopted* a coding agent if at least one verifiable agent signal is found in its commit history, PR metadata, or file structure. |
| **Detection Signal** | Any artifact in a repository that indicates agent involvement. Signals are classified by source: commit trailer, bot account, PR body marker, email domain, file-based config artifact, or structural/statistical anomaly. |
| **Multi-Method Detection** | The combination of ≥2 independent signal types to classify a commit/PR/repository as agent-authored, reducing undercounting relative to single-signal approaches. |
| **Configuration Artifact** | A file whose presence in the repository implies a specific coding agent was configured: `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.copilot/`, `.aider.conf.yml`, etc. |

---

## 2. Overview: 7-Stage Pipeline

```
Stage 1 ──► Stage 2 ──► Stage 3
  │             │           │
Base JS/TS   Egyptian    Size
Corpus       Sub-corpus  Strata
                │
              ▼ ▼ ▼
            Stage 4: Multi-Signal Detection
                │
              Stage 5: Data Infrastructure
                │
              Stage 6: Validation
                │
              Stage 7: Metrics & Analysis
```

Each stage produces structured output (CSV / SQLite tables) consumed by the next stage. Stages 1–3 are corpus construction; stages 4–7 are detection, storage, validation, and analysis.

---

## 3. Stage 1: Base JS/TS Corpus Construction

### Goal
Assemble a representative sample of GitHub repositories whose primary language is JavaScript or TypeScript and which have npm as their package manager.

### Selection Criteria
- Primary language: `JavaScript` or `TypeScript` (as reported by GitHub Linguist)
- Package manager indicator: `package.json` present at repository root
- Minimum activity: ≥10 commits, ≥1 contributor, not a fork
- Minimum recency: last push after 2023-01-01 (to allow detection of modern agents)
- Not archived, not disabled

### Sampling Strategy
The baseline study ("Agentic Much?") used 128,018 projects. This thesis targets a stratified random sample large enough for significance at each size stratum:

| Stratum | Stars Range | Target N |
|---------|-------------|----------|
| Small   | 0–50        | ~TBD     |
| Medium  | 51–500      | ~TBD     |
| Large   | >500        | ~TBD     |

Final sample sizes are determined in Stage 3 based on desired power (α=0.05, power=0.80, expected effect size from prior work).

### Data Source
- **GitHub Search API (REST)** — `q=language:javascript+language:typescript` with star-range filters
- **GH Archive / BigQuery** — for bulk commit-level data within the corpus
- **GitHub REST `/repos/{owner}/{repo}/commits`** — for per-repo commit retrieval

### Output
`base_jsts_corpus.csv` — columns: `repo_id`, `owner`, `name`, `stars`, `forks`, `created_at`, `pushed_at`, `primary_language`, `size_stratum`

---

## 4. Stage 2: Egyptian Developer Sub-Corpus

### Goal
Identify GitHub repositories whose primary contributor(s) are Egyptian developers, forming the comparison group for RQ2.

### Two-Step Approach

#### Step 2a — Seed Discovery
Identify candidate Egyptian developer accounts using location-based signals:
- GitHub profile `location` field containing: `Egypt`, `مصر`, `Cairo`, `القاهرة`, `Alexandria`, `الإسكندرية`, `Giza`, `الجيزة`, and other major Egyptian cities
- **API**: `GET /search/users?q=location:Egypt+language:javascript`
- Filter: accounts with ≥1 public JS/TS repository, ≥10 followers OR ≥5 public repos (to reduce noise)

#### Step 2b — Snowball Expansion
Expand the seed set by following social graph links:
- Retrieve followers/following of seed accounts
- Retrieve stargazers/contributors of seed repos
- Apply same location filter to newly discovered accounts
- Stop when no new accounts are added in a round (convergence) or after 3 rounds

#### Step 2c — Repository Pull
For each confirmed Egyptian developer account:
- Pull all public JS/TS repositories meeting the same criteria as Stage 1
- Deduplicate (a repo owned by two Egyptian devs counts once)

### Known Limitation
GitHub location is self-reported and unverified. Geo-attribution accuracy is a threat to validity (see Section 12). The methodology accepts this as a lower-bound estimate consistent with prior community-comparison studies.

### Output
- `egypt_seed_candidates.csv` — columns: `github_login`, `location_raw`, `public_repos`, `followers`
- `egypt_snowball_candidates.csv` — columns: same + `discovered_from`, `round`
- `egypt_combined_accounts.csv` — deduplicated union of seeds and snowball accounts
- `egypt_jsts_corpus.csv` — repositories from Egyptian accounts meeting Stage 1 criteria

---

## 5. Stage 3: Size Stratification

### Goal
Divide both the base corpus and the Egyptian sub-corpus into three size strata so that comparisons in RQ2 are controlled for repository scale.

### Stratification Variable
**Star count** is used as the proxy for repository size/popularity, following the baseline study. Thresholds:

| Stratum | Star Count | Rationale |
|---------|-----------|-----------|
| Small   | 0–50      | Hobbyist/student projects |
| Medium  | 51–500    | Active open-source projects |
| Large   | >500      | High-visibility / widely used libraries |

### Balancing
If the Egyptian sub-corpus is under-represented in a stratum relative to the base corpus (as expected for large repos), a note is added to the analysis but no upsampling is performed — results for that stratum are reported with appropriate power caveats.

### Output
Both corpora gain a `size_stratum` column: `small | medium | large`.

---

## 6. Stage 4: Multi-Signal Detection

### Goal
Label each repository, PR, and commit with agent-authorship signals using the full multi-signal detection suite.

### Detection Signal Taxonomy

| Signal Type | Examples | Source |
|-------------|---------|--------|
| **Commit trailer** | `Co-Authored-By: Claude <noreply@anthropic.com>` | Git commit message |
| **Bot account authorship** | Commits by `github-actions[bot]`, `copilot[bot]`, `aider-bot` | Commit author login |
| **PR body marker** | `🤖 Generated with Claude Code`, `Co-authored-by: github-copilot[bot]` | Pull request body |
| **Author email domain** | `*@users.noreply.github.com` with known bot patterns | Commit author email |
| **Config artifact (file-based)** | `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.copilot/`, `.aider.conf.yml`, `.roomodes` | Repo file tree |
| **Branch name** | `copilot/fix-*`, `codex/*` | Branch naming convention |
| **PR label** | `codex` label on pull request | PR metadata |

### Heuristics Coverage
Based on the baseline study, the full suite covers **63 coding agents** with:
- 93 file-based heuristics
- 79 author-based heuristics
- 20 branch-based heuristics
- 4 label-based heuristics

This thesis applies the same heuristic set, filtered to JS/TS-relevant agents.

### Single vs. Multi-Signal Detection
A key contribution of RQ1 is quantifying undercounting. Each repository is labeled independently by:
1. **Single-signal (Co-Authored-By only)** — replicating the most common approach in literature
2. **Full multi-signal** — union of all signal types above

The **undercounting delta** = (multi-signal positive rate) − (single-signal positive rate).

### Critical Limitation
Codex/IDE-integrated tools (e.g., GitHub Copilot in VS Code, Cursor in default mode) leave **no explicit trace** unless the developer opts into commit trailers or PR markers. Every adoption label in this study is therefore a **lower bound**. This is consistent across all 6 topics in the research cluster.

### Implementation
- Commit trailer parsing: Python `re` regex on raw commit messages
- Bot account detection: lookup against a maintained list of known bot logins
- File artifact detection: `GET /repos/{owner}/{repo}/contents/` + recursive tree traversal
- PR body scanning: `GET /repos/{owner}/{repo}/pulls` paginated

### Output
`signals.db` (SQLite) — tables:
- `commit_signals(repo_id, commit_sha, signal_type, agent_name, detected_at)`
- `pr_signals(repo_id, pr_number, signal_type, agent_name, detected_at)`
- `repo_signals(repo_id, signal_type, agent_name, first_seen_at)`

---

## 7. Stage 5: Data Infrastructure

### Goal
Store all raw and processed data in a reproducible, queryable format.

### Architecture

```
GitHub API / BigQuery
        │
        ▼
  Raw Fetchers (Python)
        │
        ▼
  SQLite Database (signals.db)
   ├── repos
   ├── commits
   ├── pull_requests
   ├── commit_signals
   ├── pr_signals
   └── repo_signals
        │
        ▼
  pandas DataFrames
        │
        ▼
  Jupyter Notebooks (analysis)
```

### Rate Limit Management
- GitHub REST API: 5,000 req/hr (authenticated). Use `Retry-After` headers; batch requests where possible.
- GitHub GraphQL API: 5,000 points/hr. Use for multi-field queries (commits + PRs + file tree in one request) to maximize efficiency.
- BigQuery (GH Archive): batch SQL queries; cache results locally to avoid re-billing.

---



### Goal
Estimate the precision and recall of the detection pipeline.

### Approach

#### Precision (Manual Verification)
- Random sample 100 repositories labeled as agent-adopted
- Manually verify each: inspect the commit, PR, or file that triggered the signal
- Compute: `precision = true positives / (true positives + false positives)`

#### Recall (Lower Bound Estimation)
- Full recall is unknowable (no ground truth for all GitHub)
- Estimate: compare detection rate on a known-agentic benchmark (e.g., repositories from SkillsBench arXiv:2602.12670, or repos that explicitly announce AI usage in README)
- Report recall as a lower bound with caveats

#### Inter-Rater Reliability
- A random subset of 50 manual checks is double-coded by a second reviewer
- Cohen's κ reported

### Output
Validation report table: signal type → precision, with 95% CIs.

---

## 8. Stage 7: Metrics and Analysis

### Primary Metrics

| Metric | Definition | Used in |
|--------|-----------|---------|
| **Adoption rate** | % of repos with ≥1 agent signal | RQ1, RQ2 |
| **Commit agent ratio** | % of commits in a repo with an agent signal | RQ1 |
| **Time-to-first-agent-commit (repo lag)** | Months from repo creation to first agent commit | RQ1 |
| **Time-to-first-agent-commit (author lag)** | Months from author's first commit ever to first agent commit | RQ1 |
| **Monthly adoption rate** | % of active repos with ≥1 agent signal in that calendar month | RQ1 trend |
| **Tool distribution** | Frequency of each detected coding agent | RQ1, RQ2 |
| **Undercounting delta** | Multi-signal rate − single-signal rate (percentage points) | RQ1 |

### Statistical Tests (RQ2)

| Comparison | Test | Justification |
|-----------|------|---------------|
| Adoption rate: Egyptian vs. general | Fisher's exact test (or χ²) per stratum | Binary outcome, independent groups |
| Commit ratio: Egyptian vs. general | Mann-Whitney U | Non-normal distribution expected |
| Adoption trend curves | Permutation test on area-under-curve difference | Time-series, non-parametric |

All tests: α = 0.05. Effect sizes reported in **percentage points**, not relative %. Multiple comparisons corrected with Benjamini-Hochberg (3 strata × 3 metrics = 9 tests).

### Visualizations
- Monthly adoption rate curve (line chart, with confidence band)
- Signal type breakdown stacked bar chart
- Egyptian vs. general adoption comparison by stratum (grouped bar)
- Tool distribution treemap
- Time-to-adoption CDF curves

---

## 9. Tools and Technologies

| Tool / Library | Purpose |
|----------------|---------|
| **Python 3.11+** | All scripting and analysis |
| **GitHub REST API** | Repo metadata, commits, PRs, file trees |
| **GitHub GraphQL API** | Efficient multi-field queries |
| **GH Archive + BigQuery** | Large-scale historical commit mining |
| **npm Registry API** | Package metadata (optional enrichment) |
| **GitPython** | Local git repo cloning and log parsing |
| **SQLite** | Structured storage for all signals and metadata |
| **pandas** | Data wrangling and aggregation |
| **re (regex)** | Commit message and file path pattern matching |
| **YAML** | Heuristic rule definitions |
| **scipy.stats** | Statistical tests (Mann-Whitney, Fisher's exact) |
| **matplotlib / seaborn** | Plotting |
| **Jupyter Notebook** | Exploratory analysis and reproducible reporting |

---

