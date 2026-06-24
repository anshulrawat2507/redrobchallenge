# Architecture Note

## Pipeline

```text
JD interpretation
  -> structured rubric
  -> candidate JSONL streaming parser
  -> multi-retriever source detection
  -> explicit feature-vector extraction
  -> Phase 6 hybrid ranking model
  -> Phase 7 trap-defense guardrails
  -> Phase 8 manual label review loop
  -> deterministic top-100 sort
  -> grounded reasoning generator
  -> CSV validator
```

## JD Interpretation

The target profile is a Senior AI Engineer for Redrob's founding AI team:

- 5-9 years preferred, with flexibility for strong adjacent signals
- production embeddings, retrieval, ranking, hybrid search, and vector database
  experience
- strong Python and ranking evaluation knowledge
- product-engineering mindset, not pure research-only or framework-demo work
- product-company experience preferred over pure services/consulting
- Pune/Noida preferred, major Indian cities acceptable
- available and responsive enough for recruiters to actually reach

Phase 3 stores this interpretation in `src/redrob_ranker/rubric.py`, where the
JD is split into must-have signals, nice-to-have signals, negative signals, and
logistics/hireability signals. Scoring and profiling consume the same rubric so
the implementation stays aligned with the JD.

Phase 4 adds `src/redrob_ranker/retrieval.py`, a multi-retriever layer that
identifies independent candidate-source paths: title fit, career retrieval
evidence, ranking evaluation evidence, production system evidence, trusted skill
clusters, product-company context, logistics, hireability, and caution flags.
The final score includes a small retrieval-agreement component to reward
candidates supported by several independent paths.

Phase 5 adds `src/redrob_ranker/feature_vector.py`, which turns every candidate
into explicit, auditable subfeatures: title fit, seniority, JD evidence, ranking
evaluation evidence, production evidence, trusted skills, skill assessments,
product-company context, services penalty, logistics, hireability, retrieval
agreement, and honeypot risk.

Phase 6 adds `src/redrob_ranker/ranking_model.py`, which owns the final weighted
formula, guardrail penalties, and quality tiers. This keeps the model
inspectable and avoids burying ranking logic inside ad hoc code.

Phase 7 adds `src/redrob_ranker/trap_detector.py`, which explicitly flags
keyword stuffing, impossible skill duration, unsupported expert claims,
AI-curiosity-only profiles, stale/unresponsive behavior, pure-services risk, and
behavioral history inconsistencies. Trap risk is included in feature vectors,
model penalties, and submission audit reports.

Phase 8 adds `src/redrob_ranker/review_loop.py`, which exports a curated manual
label review pack and analyzes completed labels with NDCG diagnostics and
feature-alignment tables. This keeps weight tuning separate from the official
submission path while still making calibration systematic.

## Feature Groups

### 1. Role And Career Fit

Current and previous titles are scored first because the dataset contains many
non-technical profiles with AI keyword stuffing. Strong titles include AI
Engineer, ML Engineer, Applied ML Engineer, Search Engineer, Recommendation
Systems Engineer, Data Scientist, NLP Engineer, and similar variants.

### 2. JD Evidence

Profile summaries, career descriptions, education, title text, industries, and
skill names are normalized into one searchable text field. JD-specific concepts
such as embeddings, retrieval, vector search, ranking, BM25, FAISS, Qdrant,
Pinecone, NDCG, MRR, A/B testing, production, and deployment increase evidence
score.

### 3. Trusted Skill Match

Skills are scored by relevance, proficiency, duration, and endorsements. This is
deliberately not a raw keyword count; a skill with duration and endorsements is
more trustworthy than an isolated expert label.

### 4. Company Context

The JD rejects pure consulting/services trajectories. Product industries such as
Software, SaaS, AI/ML, Fintech, E-commerce, EdTech, Gaming, and Food Delivery get
positive weight. A pure IT Services or Consulting career is down-weighted unless
other role evidence is very strong.

### 5. Logistics And Availability

Location and behavioral signals are scored because the JD wants candidates who
can actually be hired. The ranker uses India/Pune/Noida fit, relocation,
last-active date, open-to-work flag, recruiter response rate, response time,
notice period, interview completion, GitHub activity, and verification status.

### 6. Honeypot Risk

The challenge warns about subtly impossible profiles. The ranker applies a
penalty for suspicious evidence, including:

- expert skills with almost no duration and zero endorsements
- skill durations greater than plausible total experience
- invalid career date ranges
- inconsistent behavioral edge cases

### 7. Manual Calibration

Phase 8 turns the ranking output into a human review pack with labeled buckets:

- top-ranked submission candidates
- boundary cases near the cutoff
- trap-watchlist candidates
- product-watchlist candidates that may be false negatives
- non-fit watchlist candidates that test keyword stuffing and title drift

The labeled set is evaluated with NDCG@10 and NDCG@50 so you can tune weights
based on observed behavior instead of intuition alone.

## Scoring Formula

```text
base =
  0.22 * title
+ 0.22 * JD evidence
+ 0.17 * trusted skills
+ 0.10 * company context
+ 0.09 * experience fit
+ 0.05 * location/logistics
+ 0.09 * Redrob behavior
+ 0.06 * (retrieval agreement, evaluation, etc.)

final = base * (1 - honeypot_risk) * penalty_multiplier
```

The top 100 are sorted by final score descending, then by lower risk, then by
candidate ID for deterministic tie-breaking.

## Explainability (Phase 9)

Each row's reasoning mentions:

- current title and years of experience
- current industry
- top matched evidence skills
- location, recruiter response rate, and notice period
- honest concerns for lower-ranked or imperfect candidates (e.g., "long notice", "service-company background")

Reasoning is generated only from candidate fields using a strict natural language template, so it is safe for manual review and avoids hallucinated claims.

## Evaluation Harness (Phase 10)

The `tests/test_ranking.py` suite explicitly verifies:
- Validation CSV limits (exactly 100 outputs).
- Perfect determinism checking.
- Output arrays having monotonic decreasing scores.
- Honeypot volume protection.

## Demo Script (Phase 11)

To demonstrate the system to judges interactively, the ranker has been wrapped in a local Streamlit application (`app.py`). 

1. Show the JD and explain the target: production AI/search/ranking engineer,
   not keyword-stuffed AI profiles.
2. Run the UI:

   ```bash
   python -m streamlit run app.py
   ```
3. Upload `candidates.jsonl` dynamically into the browser to trigger memory-safe processing without dependencies. 
4. Hit download to extract the strictly compliant formatted `submission.csv`!
