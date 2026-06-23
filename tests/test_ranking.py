from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from redrob_ranker.cli import main
from redrob_ranker.pipeline import rank_candidates
from redrob_ranker.config import NON_FIT_TITLES

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CANDIDATES = ROOT / "sample_candidates.jsonl"


def test_validator_row_count_and_format(tmp_path: Path) -> None:
    # We create a dummy 100-row file to test exact output row limit and validation format
    dummy_input = tmp_path / "dummy_100.jsonl"
    out_csv = tmp_path / "out.csv"
    
    # Read the existing sample and replicate to make >= 100 rows
    base_data = []
    with SAMPLE_CANDIDATES.open("r", encoding="utf-8") as f:
        for line in f:
            base_data.append(json.loads(line))
            
    with dummy_input.open("w", encoding="utf-8") as f:
        for i in range(120):
            item = dict(base_data[i % len(base_data)])
            item["candidate_id"] = f"CAND_{str(i+1).zfill(7)}"
            f.write(json.dumps(item) + "\n")
            
    # Run the ranker
    result = rank_candidates(dummy_input, limit=100)
    
    assert len(result) == 100
    
    # Ensure IDs are unique
    ids = [r["candidate"]["candidate_id"] for r in result]
    assert len(ids) == len(set(ids))

    # Ensure score monotonicity
    scores = [r["score"] for r in result]
    for i in range(1, len(scores)):
        assert scores[i] <= scores[i-1], "Scores must remain monotonic descending"


def test_determinism(tmp_path: Path) -> None:
    run1 = rank_candidates(SAMPLE_CANDIDATES)
    run2 = rank_candidates(SAMPLE_CANDIDATES)
    
    ids1 = [r["candidate"]["candidate_id"] for r in run1]
    ids2 = [r["candidate"]["candidate_id"] for r in run2]
    
    assert ids1 == ids2, "Ranker must perfectly reproduce identical order every time"


def test_top_results_quality(tmp_path: Path) -> None:
    result = rank_candidates(SAMPLE_CANDIDATES)
    
    # Assuming top 5 for the small 50 count sample
    top_items = result[:5]
    for item in top_items:
        title = item["candidate"]["profile"].get("current_title", "").strip().lower()
        if title in NON_FIT_TITLES:
            # If it's a non fit title, the JD evidence must be exceptionally high
            assert item["features"].jd_evidence > 0.60
            
    # Test honeypot rate in overall results (for the mock sample it shouldn't be extremely high)
    honeypots = sum(1 for item in result if item["features"].honeypot_risk > 0)
    assert honeypots / len(result) < 0.50, "Honeypot risk threshold exceeded in results"
