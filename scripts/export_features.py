#!/usr/bin/env python3
"""Export Phase 5 feature vectors for the current top-100 submission."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from redrob_ranker.feature_vector import extract_feature_vector, write_feature_outputs  # noqa: E402
from redrob_ranker.io import iter_candidates  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Export explicit feature vectors for submission candidates.")
    parser.add_argument("--candidates", default=ROOT / "candidates.jsonl", type=Path)
    parser.add_argument("--submission", default=ROOT / "submission.csv", type=Path)
    parser.add_argument("--out-dir", default=ROOT / "reports", type=Path)
    args = parser.parse_args()

    ranked_ids = read_submission_ids(args.submission)
    wanted = set(ranked_ids)
    candidates = {candidate["candidate_id"]: candidate for candidate in iter_candidates(args.candidates) if candidate["candidate_id"] in wanted}
    vectors = [extract_feature_vector(candidates[candidate_id]) for candidate_id in ranked_ids if candidate_id in candidates]
    write_feature_outputs(vectors, args.out_dir)
    print(f"Wrote feature vectors to {args.out_dir}")
    print(f"Feature rows exported: {len(vectors)}")


def read_submission_ids(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda row: int(row["rank"]))
    return [row["candidate_id"] for row in rows]


if __name__ == "__main__":
    main()
