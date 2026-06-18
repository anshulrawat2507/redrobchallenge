# Phase 1 Compliance Checklist

This file tracks the non-negotiable rules from the challenge documents.

## Ranking Command

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

## Required Output Format

- File type: `.csv`
- Encoding: UTF-8
- Header: `candidate_id,rank,score,reasoning`
- Data rows: exactly 100
- Rank values: exactly 1 through 100
- Candidate IDs: unique, `CAND_XXXXXXX`
- Scores: non-increasing by rank
- Reasoning: 1-2 grounded sentences, no hallucinated claims

## Compute Rules

- CPU only
- No GPU
- No network calls during ranking
- No hosted LLM/API calls during ranking
- Target runtime: under 5 minutes
- Target memory: under 16 GB RAM

## Repository Rules

- Include the full source code that produced the CSV.
- Include a clear README with setup and reproduction command.
- Include `requirements.txt` or equivalent dependency file.
- Include `submission_metadata.yaml`.
- Keep the ranking step reproducible with no hidden manual edits.

## Phase 1 Status

- CLI entry point: complete
- Structured source layout: complete
- Official validator compatibility: verify after every ranking run
- Metadata template: present, still requires real team details
- Demo/sandbox: pending for later phase
- PDF deck: pending for later phase

## Phase 2 Status

- Dataset profiler: complete
- Generated analysis reports: complete
- Risk example export: complete
- Strong candidate pool export: complete
- Current submission audit: complete
- Ranker integration: intentionally separate until manual review/tuning

## Phase 3 Status

- Structured JD rubric: complete
- Rubric report export: verify after running `scripts/export_rubric.py`
- Scoring constants wired to rubric: complete
- Profiling JD terms wired to rubric: complete

## Phase 4 Status

- Multi-retriever source detector: complete
- Retrieval pool report script: complete
- Retrieval agreement integrated into scoring: complete
- Explanation includes retrieval agreement: complete
- Official validator after Phase 4: passing

## Phase 5 Status

- Explicit feature-vector extractor: complete
- Feature export script: complete
- Scoring routed through feature vector: complete
- Explanation includes hireability feature: complete
- Official validator after Phase 5: passing

## Phase 6 Status

- Named hybrid ranking model: complete
- Model report export script: complete
- Scoring routed through model decision: complete
- Guardrail penalties and quality tiers: complete
- Official validator after Phase 6: passing

## Phase 7 Status

- Trap/honeypot detector: complete
- Trap report export script: complete
- Trap risk integrated into feature vector: complete
- Trap risk integrated into ranking model: complete
- Submission audit uses Phase 7 risk: complete
- Official validator after Phase 7: passing
