# Submission Deck Outline

Use this as the content for the required PDF deck.

## Slide 1: Title

Redrob Intelligent Candidate Discovery & Ranking Engine

Track 1: AI & Datathon Arena

## Slide 2: Problem

Recruiting search fails when it relies on keyword matching. The JD asks for a
rare Senior AI Engineer profile: production retrieval/ranking experience,
product-company judgment, strong Python, evaluation literacy, and actual
availability.

## Slide 3: Key Insight From The JD

The correct target is not "most AI keywords." The target is a candidate who has
actually shipped AI/search/ranking systems to users and is reachable for hiring.

The ranker therefore combines career evidence, skill trust, product context,
location/logistics, Redrob activity, and honeypot-risk checks.

## Slide 4: System Architecture

```text
Candidate JSONL
  -> streaming parser
  -> text and structured feature extraction
  -> weighted hybrid scorer
  -> honeypot-risk penalty
  -> deterministic top-100 ranking
  -> grounded reasoning generator
  -> validated CSV
```

## Slide 5: Scoring Components

- Title and career fit: AI/ML/search/recommendation/ranking roles
- JD evidence: embeddings, retrieval, vector search, BM25, FAISS, NDCG, A/B tests
- Trusted skills: proficiency + duration + endorsements
- Company context: product industries over pure services/consulting
- Experience: strongest for 5-9 years
- Logistics: Pune/Noida, major Indian cities, relocation
- Behavior: recency, response rate, notice, interview completion, verification

## Slide 6: Honeypot And Trap Handling

The system down-weights suspicious profiles:

- non-technical titles with AI keyword stuffing
- expert skills with near-zero duration and zero endorsements
- skill durations that exceed plausible experience
- invalid career date ranges
- low availability or stale Redrob activity

## Slide 7: Explainability

Every CSV row includes candidate-specific reasoning:

- role title and years of experience
- matched AI/retrieval/ranking evidence
- location, notice period, response rate
- honest concerns for weaker candidates

Reasoning is generated from candidate fields only, avoiding hallucinations.

## Slide 8: Reproducibility

Command:

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
python validate_submission.py ./submission.csv
```

Runtime observed locally: about 24 seconds for 100K candidates on CPU.

No network, no GPU, no third-party packages.

## Slide 9: Output

The generated `submission.csv` contains:

- 100 candidates
- ranks 1-100 exactly once
- non-increasing scores
- unique candidate IDs
- grounded reasoning for manual review

Official validator result: `Submission is valid.`

## Slide 10: Future Improvements

- Add offline BM25 or TF-IDF retrieval as a candidate-stage filter
- Train a lightweight learning-to-rank model from manually labeled samples
- Add richer temporal consistency checks for honeypots
- Tune weights using a small human-labeled validation set
- Build a Streamlit/HuggingFace demo for small-sample upload and CSV export
