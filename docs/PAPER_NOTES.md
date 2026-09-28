# Paper Notes — Coding Agent Adoption Research

**Purpose**: Study notes on the two baseline papers and the cluster research methods guide.  
**For**: Manuel Youssef Haik Kevorkian — Thesis Topic 2 (JS/TS/npm)

---

## Table of Contents

1. [Paper 1 — "Agentic Much?"](#1-paper-1--agentic-much)
2. [Paper 2 — "Agentic Very Much!"](#2-paper-2--agentic-very-much)
3. [ResearchMethods.pdf — Cluster Methodology Guide](#3-researchmethodspdf--cluster-methodology-guide)
4. [Cross-Paper Synthesis](#4-cross-paper-synthesis)


---

## 1. Paper 1 — "Agentic Much?"
### *Adoption of Coding Agents on GitHub*

---

### 1.1 At a Glance

| Field | Detail |
|-------|--------|
| Type | Large-scale empirical study |
| Corpus | 128,018 GitHub repositories |
| Snapshot date | February 21, 2026 |
| Agents covered | 63 coding agents |
| Total heuristics | 196 (93 file + 79 author + 20 branch + 4 label) |
| Pages | 42 |

This is the **primary baseline** for your thesis. Every number in your results will be compared to or contextualized against this paper.

---

### 1.2 Research Questions

The paper addresses six RQs:

| RQ | Question | Short answer |
|----|----------|-------------|
| **RQ1** | What is the overall adoption rate of coding agents on GitHub? | 22.20%–28.66% of studied projects |
| **RQ2** | What project characteristics are associated with coding agent adoption? | Larger, more active, more starred repos adopt more |
| **RQ3** | In what development contexts are coding agents used? | Feature work (35.7%) and bug fixing (29.9%) dominate |
| **RQ4** | How has adoption evolved over time? | Rapid growth, especially after mid-2025 |
| **RQ5** | How do AI-authored commits differ in size from human commits? | AI commits are 3× larger (median 31 vs 11 lines added) |
| **RQ6** | What types of contributions do coding agents make? | Feature additions most common, followed by bug fixes |

---

### 1.3 Methodology

#### Corpus Construction
- 128,018 GitHub repositories sampled across languages and sizes
- Filtering: active repos (not archived, not forks, recent push)
- Languages: not restricted to one ecosystem — cross-language study

#### Detection Approach: Heuristic-Based
The paper uses a **single-pass heuristic detection** method with 196 heuristics across 4 signal types:

| Signal Type | Count | Examples |
|------------|-------|---------|
| **File-based** | 93 | `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.aider.conf.yml`, `.copilot/` |
| **Author-based** | 79 | `Co-Authored-By: Claude`, `Co-Authored-By: github-copilot[bot]`, bot login patterns |
| **Branch-based** | 20 | `copilot/fix-*`, `codex/*`, `aider/*` |
| **Label-based** | 4 | PR labels: `codex`, `copilot`, `ai-generated` |

These heuristics cover **63 distinct coding agents**, making this the most comprehensive detection study to date.

#### Adoption Categories
Repositories are grouped into adoption categories based on the *fraction* of commits with agent signals:
- **None**: 0% agent commits
- **Peripheral**: very small fraction
- **Moderate**: noticeable but not dominant fraction
- **Pervasive**: majority of commits are agent-authored

---

### 1.4 Key Findings

#### Overall Adoption (RQ1)
- **22.20%** of repositories show at least one agent signal using strict heuristics
- **28.66%** when using the full heuristic set
- The gap (6.46 percentage points) illustrates that **single-signal detection significantly undercounts** — directly motivating RQ1 of your thesis

#### Commit Size Comparison (RQ5) — Most Cited Finding
> **AI-authored commits are 3× larger than human commits**
- Median lines added by AI commits: **31**
- Median lines added by human commits: **11**
- This is a consistent, strong signal across all agent types
- Deletions show a similar but smaller ratio

#### Commit Type Distribution (RQ6)
| Commit Type | Share |
|------------|-------|
| Feature (feat) | 35.7% |
| Fix (fix) | 29.9% |
| Chore / refactor / docs | remaining |

Most AI-authored commits are not just bug fixes — agents are participating in primary feature development.

#### Temporal Evolution (RQ4)
- Adoption was very low before 2024
- Inflection point around mid-2024 (GitHub Copilot becoming widespread in IDEs)
- Second rapid acceleration from Q3 2025 onward (Claude Code, Devin, and agentic loop tools)

---

### 1.5 Key Limitations (from the paper itself)

1. **Lower bound problem**: IDE-integrated tools (Copilot in VS Code, Cursor default mode) leave no trace unless the developer opts into trailers. The 22–28% figure is a minimum estimate.
2. **Heuristic precision not 100%**: Some file-based heuristics can appear in repos that use the tool for non-coding purposes (e.g. a `CLAUDE.md` used for documentation).
3. **Single snapshot**: The Feb 2026 snapshot captures a point in time; the field is evolving rapidly.
4. **Cross-language aggregation**: By aggregating all languages, ecosystem-specific patterns are hidden — this is exactly the gap your thesis addresses for JS/TS.

---

### 1.6 Why This Paper Matters for Your Thesis

| What the paper does | What your thesis adds |
|--------------------|----------------------|
| Measures adoption across all languages | Zooms into JS/TS/npm specifically |
| Uses single-signal detection in some comparisons | Quantifies the undercounting delta with multi-signal |
| Does not compare community subgroups | Compares Egyptian developers vs. general population |
| Reports aggregate adoption rate | Reports stratum-specific rates (small/medium/large repos) |

Your JS/TS results will either confirm or diverge from the 22–28% baseline — either outcome is an interesting finding.

---

## 2. Paper 2 — "Agentic Very Much!"
### *Adoption of Coding Agents in New GitHub Projects*

---

### 2.1 At a Glance

| Field | Detail |
|-------|--------|
| Type | Companion empirical study to Paper 1 |
| Corpus | 12,794 new GitHub repositories |
| "New" definition | Created after August 29, 2025 |
| Adoption rate found | 71.83%–76.15% |
| Pages | 16 |

This paper is a **companion study** to Paper 1. It answers the question: *does the adoption rate look different if you only look at projects that started after modern coding agents existed?*

The answer is a dramatic yes.

---

### 2.2 Core Finding: New Projects Adopt at 3× the Rate

| Metric | Older projects (Paper 1) | New projects (Paper 2) |
|--------|--------------------------|------------------------|
| Adoption rate | 22–28% | **71–76%** |
| Median commit agent ratio | ~10% | **~30%** |
| Most common category | Moderate | **Pervasive** |
| Pervasive category share | 21.1% | **41.2%** |

The implication is significant: **the 22–28% from Paper 1 is heavily dragged down by older projects that pre-date the agent era**. New projects are being built with agents from day one.

---

### 2.3 Tool Distribution in New Projects

| Finding | Detail |
|---------|--------|
| Dominant tool | **Claude Code** |
| Claude Code vs Copilot | Claude Code is **3× more popular** in new projects |
| Why | Claude Code was released in early 2025 and became the leading agentic coding tool quickly |

This is relevant for your thesis because JS/TS is Claude Code's native ecosystem (it runs in the terminal, works well with npm projects, and the `CLAUDE.md` file convention originated there).

---

### 2.4 Methodology Differences from Paper 1

Paper 2 uses the **same heuristics** as Paper 1 (196 heuristics, 63 agents) but:
- Restricts corpus to repos created after Aug 29, 2025
- Compares commit ratios (not just binary adopted/not adopted)
- Focuses on the Pervasive adoption category as the key metric

---

### 2.5 Key Insight: Undetected Adoption Is Even Higher

The paper makes an important argument: if 76% of new repos have *explicit* agent signals, and we know IDE tools leave no trace, then the *true* adoption rate could be approaching 90%+.

> "The pervasive presence of coding agent signals in new GitHub projects suggests that agentic development may already be the default for new open-source projects, with the remaining undetected portion driven by IDE-integrated tools that leave no commit-level trace."

This directly justifies your multi-signal detection approach — the gap between single-signal and multi-signal detection is the measurable piece of a larger undetected iceberg.

---

### 2.6 Key Limitations

1. **Short observation window**: Projects created after Aug 2025 have at most a few months of history at the time of the study. Adoption patterns may shift.
2. **Selection bias**: Developers who create new projects in late 2025 are likely early adopters — not representative of all developers.
3. **Same lower-bound problem**: The 76% is still a lower bound for the same reasons as Paper 1.

---

### 2.7 Why This Paper Matters for Your Thesis

- **Sets the expectation**: Your JS/TS corpus will contain both old and new repos. Expect the adoption rate for new repos (post-Aug 2025) to be much higher than for old ones.
- **Claude Code is the dominant tool**: Your detection suite must cover Claude Code signals thoroughly (`CLAUDE.md`, `Co-Authored-By: Claude`, `🤖 Generated with Claude Code` PR body marker).
- **Justifies the temporal analysis**: Your RQ1 trend curve should show the same inflection — a jump around mid-2025 driven by Claude Code's launch.
- **Replication opportunity**: You can replicate this new-vs-old comparison within JS/TS specifically, adding ecosystem-level nuance.

---

## 3. ResearchMethods.pdf — Cluster Methodology Guide

---

### 3.1 What This Document Is

This is a **shared methodology guide written by the supervisor** for all 6 students in the "Coding Agent Adoption on GitHub" research cluster. It is not a published paper — it is internal guidance. All 6 topics draw from the same detection methodology, making their findings cross-comparable.

---

### 3.2 The Six Topics in the Cluster

| Topic | Ecosystem | Student |
|-------|-----------|---------|
| 1 | — | — |
| **2** | **JavaScript / TypeScript / npm** | **Manuel Youssef Haik Kevorkian** |
| 3 | — | — |
| 4 | — | — |
| 5 | — | — |
| 6 | — | — |

Each topic targets one language ecosystem. Because all topics use the same detection signals and metric definitions, the supervisor can aggregate findings into a cross-ecosystem comparison paper at the cluster level.

---

### 3.3 Agent-Authorship Detection Signals

The document defines the canonical set of signals that all 6 topics must use. This is reproduced in your `SHARED_CORPUS_METHODOLOGY.md` but worth understanding conceptually here.

| Signal Type | What it looks like | Reliability |
|------------|-------------------|-------------|
| **Co-Authored-By trailer** | `Co-Authored-By: Claude <noreply@anthropic.com>` in commit message | High — developer opted in explicitly |
| **Bot account authorship** | Commits authored by `github-copilot[bot]`, `aider-bot`, etc. | High — account login is verifiable |
| **PR body marker** | `🤖 Generated with Claude Code` in pull request description | Medium — PR body is free text, easy to add/remove |
| **Author email domain** | Commit email matching known bot patterns | Medium — not all tools set this |
| **Structural/statistical** | Config artifact files (`CLAUDE.md`, `.cursorrules`, etc.) | Medium — file presence ≠ active use, but strong signal |

**Critical limitation stated in the document:**
> "Codex and IDE-integrated tools (GitHub Copilot in VS Code, Cursor in default mode) leave no explicit trace unless the developer opts into commit trailers or PR markers. Every adoption label produced by any topic in this cluster is therefore a lower bound on true adoption."

This is the most important methodological constraint. You must state it explicitly in your thesis threats-to-validity section.

---

### 3.4 GitHub API Surface

The document maps each research need to the appropriate GitHub API endpoint:

| Need | API | Notes |
|------|-----|-------|
| Repository discovery | REST Search API | 1,000 results/query cap; need date/star splits for larger corpora |
| Commit metadata + messages | REST `/repos/{owner}/{repo}/commits` | Paginated; bounded by date for snapshot consistency |
| Pull request body + labels | REST `/repos/{owner}/{repo}/pulls` | State=all to capture merged PRs |
| File tree (config artifacts) | REST `/repos/{owner}/{repo}/git/trees/{sha}?recursive=1` | Use GraphQL for batching |
| Multi-field repo queries | **GitHub GraphQL API** | Most efficient for batching; 5,000 points/hr |
| Large-scale historical data | **GH Archive + BigQuery** | Public dataset; SQL queries; cached locally |
| Compare endpoint | REST `/repos/{owner}/{repo}/compare` | Used for diff-level analysis |
| Code scanning alerts | REST Code Scanning API | Optional; not needed for basic adoption detection |

Your scripts (`stage1_fast_graphql.py`, `stage2c_fast_graphql.py`) already use GraphQL for batching — this is exactly what the document recommends.

---

### 3.5 Other Research Clusters (Context)

The document also describes three other research clusters that other student groups are working on. Understanding these helps avoid conceptual overlap and shows where your work fits:

#### Cluster B — "AI-Authored Commits Reverted/Hotfixed"
- Question: Are AI-authored commits more likely to be reverted or followed by a hotfix?
- Method: Detect reverts using `git log --all --grep="Revert"` patterns; match to prior AI-authored commits
- Your topic overlaps: you both identify AI-authored commits, but your purpose is adoption rate, theirs is quality/stability

#### Cluster C — "Code Review Burden"
- Question: Do PRs with AI-authored code take longer to review? Are they harder to approve?
- Method: Compare review time, comment count, approval round count between AI and human PRs
- Your topic overlaps: you both analyze PRs, but you use PR signals for detection while they analyze review behavior

#### Cluster D — "Fingerprint Classifier"
- Question: Can a trained classifier detect AI-generated commits without explicit signals (for tools that leave no trace)?
- Method: Train on labeled AI/human commits; extract statistical features (commit size distribution, time-of-day patterns, message structure)
- Your topic is complementary: if their classifier works, it could close the "undetected adoption" gap you describe as a threat to validity

#### Cluster E — "Longitudinal Adoption"
- Question: How does adoption evolve month-by-month at the individual developer level?
- Method: Track when each developer first uses an agent and model the diffusion curve
- Your topic overlaps significantly: your RQ1 trend analysis (M4: monthly adoption rate) produces similar data, but aggregated at the repo level rather than the developer level

---

### 3.6 Key Methodological Principles from the Document

These are stated rules that all topics must follow:

1. **Lower-bound framing**: Always say "at least X% of repositories" — never claim the number is exact.
2. **Snapshot date consistency**: All topics use the same `STUDY_SNAPSHOT_DATE = 2026-09-01` so cross-ecosystem comparisons are apples-to-apples.
3. **Effect sizes in percentage points**: Report undercounting delta and comparisons in pp (percentage points), not relative % change. E.g. "29.5% − 18.0% = 11.5 pp" not "63% more".
4. **Stratified analysis**: Size stratification (small/medium/large by star count) is mandatory for all topics to control for the known correlation between repo size and adoption rate.
5. **Reproducibility**: Every corpus pull must be logged (`pull_log.jsonl`), every filtering decision audited (`filter_audit.csv`), and corpora committed to the repo so results are reproducible.

---

## 4. Cross-Paper Synthesis

### 4.1 The Three Key Numbers to Internalize

| Number | Source | What it means |
|--------|--------|---------------|
| **22–28%** | Paper 1 | Baseline adoption across all GitHub (lower bound) |
| **71–76%** | Paper 2 | Adoption in new projects (lower bound) |
| **3×** | Both papers | AI commits are 3× larger AND Claude Code is 3× more popular than Copilot in new projects |

### 4.2 The Undetected Adoption Argument

Both papers agree on a crucial point that motivates your multi-signal detection work:

```
Detected (signals)          Undetected (no trace)
─────────────────           ──────────────────────────────────
Co-authored-by trailers     Copilot in VS Code (no trailer by default)
Bot account commits         Cursor in default mode
Config artifact files       ChatGPT-assisted code (no agent, just copy-paste)
PR body markers             Any tool where developer didn't opt into trailers
```

The left column is what you measure. The right column is why your number is always a lower bound. Your RQ1 contribution (undercounting delta) makes the left column larger by combining all signal types — but can never reach the full truth.

### 4.3 Evolution of the Field (Timeline)

```
2022        GitHub Copilot becomes generally available
            → first Co-Authored-By trailers appear

2023–2024   Cursor, Aider, Codeium, Devin emerge
            → adoption still < 10% of repos

Early 2025  Claude Code released
            → rapid adoption jump, especially in new projects

Mid-2025    GitHub Copilot adds agent mode
            → second jump

Aug 2025    Paper 2's cutoff date for "new projects"
            → 71–76% adoption in repos created after this point

Feb 2026    Paper 1's snapshot date
            → 22–28% across all repos (including old ones)

Sep 2026    Your study snapshot date
            → expect higher than Feb 2026 due to continued growth
```

### 4.4 What Both Papers Don't Do (Your Contribution Space)

| Gap | Your thesis addresses it |
|-----|------------------------|
| JS/TS ecosystem specifically | ✅ RQ1 |
| Multi-signal vs. single-signal undercounting | ✅ RQ1 |
| Community comparison (Egyptian devs vs. general) | ✅ RQ2 |
| Size-stratified comparison | ✅ RQ2 |
| npm package manager as a filter | ✅ Your ecosystem scope |

---

