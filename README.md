# Coding Agent Adoption
### Bachelor's Thesis 


---

## What This Thesis Is About

This thesis investigates how coding agents (GitHub Copilot, Cursor, Claude Code, and similar AI-assisted development tools) are being adopted on GitHub, with a focus on the Egyptian developers specifically.

Two research questions drive the study(For: JS/TS/npm):

- **RQ1 — Adoption rate:** What proportion of active JS/TS repositories show evidence of coding agent use? How does adoption vary by project visibility (star stratum) and over time?
- **RQ2 — Impact:** Does the introduction of a coding agent measurably change repository activity — commit frequency, PR merge time, contributor growth, code churn?

The study is part of a six-student research cluster. All six topics study the same research questions for Egyptian developers, each covering a different programming language ecosystem. Shared methodology ensures findings are directly comparable across ecosystems.

---



## Pipeline Overview

The data collection pipeline runs in 7 stages. Stages 1–3 are complete.

```
Stage 1 ── Search GitHub for active JS/TS repos (global sample)
              └─► base_jsts_corpus_pilot.csv  (4,372 repos)

Stage 2a ── Discover Egyptian developer accounts by location search
              └─► egypt_seed_candidates.csv   (1,876 accounts)

Stage 2b ── Snowball-expand the seed list through follower/following networks
              └─► egypt_snowball_candidates.csv  (19,347 new accounts)

              combine_accounts.py
              └─► egypt_combined_accounts.csv  (21,223 total accounts)

Stage 2c ── Pull JS/TS repos from all Egyptian developer accounts
              └─► egypt_corpus.csv  (72,946 repos)

Stage 3 ── Merge and deduplicate both corpora
              └─► unified_corpus.csv  (77,315 unique repos)

Stage 4 ── [TODO] Detect coding agent adoption signals in each repo
              └─► signals.csv + agent_adopted column filled in

Stage 5 ── [TODO] Compute before/after metrics for adopted repos
              └─► metrics.csv + SQLite database

Stage 6 ── [TODO] Manual validation sample (~50 repos)
              └─► validation_sample.csv

Stage 7 ── [TODO] Statistical analysis — answer RQ1 and RQ2
              └─► results tables + plots for thesis
```

---

## Running the Pipeline

### Requirements

```bash
pip install requests pandas
export GITHUB_TOKEN=ghp_your_token_here
```

A GitHub Personal Access Token is required. Without it the API rate limit is 60 requests/hour, making large-scale collection impossible. With a token: 5,000 REST requests/hour, 5,000 GraphQL points/hour.

### Stage 1 — Base Corpus

```bash
cd scripts/stage1
python3 stage1_fast_graphql.py
# Output: ../../data/base_jsts_corpus_pilot.csv
```

### Stage 2 — Egyptian Developer Corpus

```bash
cd scripts/stage2

python3 stage2a_egypt_seed_discovery_v2.py
# Output: ../../data/egypt_seed_candidates.csv
# ↓ manually review for false positives, then:

python3 Stage2b_snowball_expansion.py
# Output: ../../data/egypt_snowball_candidates.csv

python3 combine_accounts.py
# Output: ../../data/egypt_combined_accounts.csv

python3 stage2c_fast_graphql.py
# Output: ../../data/egypt_corpus.csv
```

### Stage 3 — Merge

```bash
cd scripts/stage3
python3 stage3_merge_corpora.py
# Output: ../../data/unified_corpus.csv
```

---

## Key Numbers (Stages 1–3 complete)

| Metric | Value |
|--------|-------|
| Egyptian seed accounts | 1,876 |
| Accounts after snowball expansion | 21,223 |
| Global JS/TS repos (base corpus) | 4,372 |
| Egyptian developer JS/TS repos | 72,946 |
| Repos in both corpora | 3 |
| **Total unique repos (unified corpus)** | **77,315** |
| JavaScript repos | 46,973 (60.8%) |
| TypeScript repos | 30,342 (39.2%) |
| Small stratum (0–50 stars) | 74,162 (95.9%) |
| Medium stratum (51–500 stars) | 1,522 (2.0%) |
| Large stratum (>500 stars) | 1,631 (2.1%) |

---

## Shared Methodology

This thesis is one of six in a research cluster. The shared methodology — covering repository filtering rules, Egyptian developer discovery pipeline, detection signals, and metric definitions.



The only differences between topics are the target programming language, the ecosystem manifest file checked, and any ecosystem-specific dependency signals.

---

