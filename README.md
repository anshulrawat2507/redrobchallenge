# Redrob Intelligent Candidate Discovery Ranker

Phase 1 is a compliance-first, reproducible baseline for the Redrob Track 1
challenge. It ranks the top 100 candidates for the released Senior AI Engineer
JD and writes the exact CSV required by the official validator.

## Official Reproduction Command

Run from this folder:

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
python validate_submission.py ./submission.csv
```

The ranking step is deterministic, CPU-only, and uses no network calls.

## Challenge Constraints Covered

- Output is CSV only.
- Header is exactly `candidate_id,rank,score,reasoning`.
- Exactly 100 candidate rows are written.
- Ranks are exactly `1` through `100`.
- Candidate IDs are unique and use the released `CAND_XXXXXXX` format.
- Scores are monotonically non-increasing by rank.
- Reasoning is grounded in fields from each candidate profile.
- Ranking uses local files only, with no hosted LLM/API calls.
- The ranker works with `.jsonl` and `.jsonl.gz` inputs.

## Project Structure

```text
.
├── rank.py                         # stable CLI entry point for judges
├── validate_submission.py          # official challenge validator
├── submission_metadata.yaml        # portal/reproducibility metadata
├── requirements.txt                # no third-party runtime dependencies
├── COMPLIANCE.md                   # Phase 1 rule checklist
├── ARCHITECTURE.md                 # system explanation for deck/review
├── DECK_OUTLINE.md                 # PDF deck content outline
├── scripts/
│   ├── build_retrieval_pool.py     # Phase 4 multi-retriever reports
│   ├── export_rubric.py            # Phase 3 JD rubric report
│   ├── export_features.py          # Phase 5 top-100 feature vectors
│   ├── export_model_report.py      # Phase 6 hybrid model breakdown
│   ├── export_review_pack.py       # Phase 8 manual label workbook
│   ├── analyze_review_labels.py    # Phase 8 label diagnostics
│   ├── profile_data.py             # Phase 2 dataset intelligence reports
│   └── audit_submission.py         # Phase 2 current top-100 audit
├── reports/                        # generated Phase 2 analysis outputs
└── src/
    └── redrob_ranker/
        ├── cli.py                  # argparse interface
        ├── config.py               # JD-specific rubric constants
        ├── feature_vector.py       # Phase 5 explicit model features
        ├── io.py                   # JSONL streaming and CSV writing
        ├── features.py             # feature extraction primitives
        ├── profiling.py            # dataset profiling and trap discovery
        ├── ranking_model.py        # Phase 6 final hybrid model formula
        ├── retrieval.py            # Phase 4 multi-retriever source signals
        ├── rubric.py               # Phase 3 structured JD interpretation
        ├── scoring.py              # weighted hybrid score
        ├── explanations.py         # grounded reasoning strings
        └── pipeline.py             # end-to-end ranking orchestration
```

## Current Ranking Method

The baseline is intentionally transparent. It scores each candidate on:

- role/title fit for AI, ML, search, recommendation, ranking, NLP, or data
  science work
- JD evidence in profile and career text, including embeddings, retrieval,
  vector search, ranking, BM25, FAISS, Qdrant, Pinecone, Elasticsearch,
  production deployment, and evaluation terms
- trusted AI/search skills using proficiency, duration, and endorsements
- product-company context versus pure services/consulting trajectory
- preferred 5-9 year experience band
- India/Pune/Noida or major-city logistics
- Redrob behavioral availability signals
- honeypot-risk indicators such as suspicious expert skills or impossible skill
  durations

This is Phase 1, so the emphasis is valid, reproducible, explainable output. The
next phases should add stronger retrieval, manual review labels, weight tuning,
and a Streamlit/Hugging Face demo.

## Phase 2 Data Intelligence

Generate analysis reports with:

```bash
python scripts/profile_data.py --candidates ./candidates.jsonl --out-dir ./reports
python scripts/audit_submission.py --candidates ./candidates.jsonl --submission ./submission.csv --out-dir ./reports
```

The profiler streams the dataset once and writes:

- `reports/profile_summary.md`
- `reports/profile_summary.json`
- `reports/risk_examples.csv`
- `reports/strong_pool_examples.csv`
- `reports/submission_audit.md`
- `reports/submission_top_rows.csv`
- `reports/submission_risk_rows.csv`

These files support strategy, trap discovery, and manual review. They do not
change the official ranking command.

## Phase 3 JD Rubric

Export the structured JD interpretation with:

```bash
python scripts/export_rubric.py --out ./reports/jd_rubric.md
```

The rubric defines:

- must-have technical signals
- nice-to-have signals
- negative/trap signals
- logistics and Redrob hireability signals

Scoring and profiling both consume this rubric so the implementation remains
aligned with the JD rather than drifting into generic keyword matching.

## Phase 4 Multi-Retriever Pool

Generate the retrieval pool report with:

```bash
python scripts/build_retrieval_pool.py --candidates ./candidates.jsonl --out-dir ./reports --top-n 500
```

Phase 4 adds independent retrieval sources:

- strong AI/search title
- adjacent engineering title
- career retrieval/ranking evidence
- ranking evaluation evidence
- production system evidence
- trusted AI/search skill cluster
- product-company context
- viable location
- hireability via Redrob signals
- trap/pure-services caution flags

The final ranker uses a small retrieval-agreement score so candidates supported
by multiple independent JD-aligned paths get a modest lift without overpowering
the core scoring model.

## Phase 5 Feature Engineering

Export feature vectors for the current top-100 submission with:

```bash
python scripts/export_features.py --candidates ./candidates.jsonl --submission ./submission.csv --out-dir ./reports
```

Phase 5 makes the ranker inspectable through explicit features:

- title fit and seniority
- JD evidence, ranking-evaluation evidence, and production evidence
- trusted skills and Redrob skill assessments
- product-company context and services penalty
- location, notice period, activity, response, GitHub, and hireability
- retrieval agreement and honeypot risk

The reports are written to `reports/feature_summary.md`,
`reports/feature_summary.json`, and `reports/feature_vectors_top100.csv`.

## Phase 6 Hybrid Ranking Model

Export the final model breakdown with:

```bash
python scripts/export_model_report.py --candidates ./candidates.jsonl --submission ./submission.csv --out-dir ./reports
```

Phase 6 separates the final score into:

- named weighted model components
- quality tiers for top-100 review
- guardrail penalties for weak-role, pure-services, low-hireability, and risk cases
- per-candidate weighted component rows

The reports are written to `reports/ranking_model_summary.md`,
`reports/ranking_model_summary.json`, `reports/ranking_model_weights.csv`, and
`reports/ranking_model_top100.csv`.

## Phase 7 Trap Defense

Export trap and honeypot analysis with:

```bash
python scripts/export_trap_report.py --candidates ./candidates.jsonl --out-dir ./reports --top-n 100
```

Phase 7 detects unsupported expert claims, impossible skill durations, invalid
career dates, AI keyword stuffing, AI-curiosity/tutorial-only profiles,
pure-services profiles without product AI evidence, stale or unresponsive
profiles, long-notice low-response profiles, and behavioral history
inconsistencies. Trap risk is integrated into feature vectors, model penalties,
and submission audits.

## Phase 8 Manual Label Review Loop

Export the review pack for human labeling with:

```bash
python scripts/export_review_pack.py --candidates ./candidates.jsonl --submission ./submission.csv --out-dir ./reports
```

Then fill the `human_label` column in `reports/review_pack.csv` using the
0-5 scale shown in `reports/review_pack.md`, and analyze the labeled set with:

```bash
python scripts/analyze_review_labels.py --labels ./reports/review_pack.csv --out-dir ./reports
```

Phase 8 adds the calibration loop that makes the ranker stronger without
changing the official submission contract. It focuses review time on:

- top-ranked submission candidates
- boundary candidates near the cutoff
- trap-watchlist candidates with high honeypot risk
- product-watchlist candidates that may be false negatives
- non-fit watchlist candidates for keyword-stuffing checks

The generated label summary reports NDCG@10 and NDCG@50, plus feature
alignment tables that show which signals are separating good and bad candidates
in the right direction.

## Submission Files To Prepare

For the portal you will need:

- public GitHub repository URL
- PDF deck under 5 MB
- final ranked CSV, named using your registered participant/team ID
- sandbox/demo link
- completed `submission_metadata.yaml`

Do not submit `sample_submission.csv`; it is only a format example and is not a
quality ranking.
