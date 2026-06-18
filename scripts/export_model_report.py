#!/usr/bin/env python3
"""Export Phase 6 hybrid ranking model reports for the current submission."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from redrob_ranker.io import iter_candidates  # noqa: E402
from redrob_ranker.ranking_model import HYBRID_MODEL_WEIGHTS, write_model_report  # noqa: E402
from redrob_ranker.scoring import score_candidate  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the Phase 6 hybrid ranking model report.")
    parser.add_argument("--candidates", default=ROOT / "candidates.jsonl", type=Path)
    parser.add_argument("--submission", default=ROOT / "submission.csv", type=Path)
    parser.add_argument("--out-dir", default=ROOT / "reports", type=Path)
    args = parser.parse_args()

    ranked = read_ranked_submission(args.submission)
    ranked_ids = [row["candidate_id"] for row in ranked]
    wanted = set(ranked_ids)
    candidates = {
        candidate["candidate_id"]: candidate
        for candidate in iter_candidates(args.candidates)
        if candidate["candidate_id"] in wanted
    }
    rows = []
    for row in ranked:
        candidate = candidates.get(row["candidate_id"])
        if not candidate:
            continue
        scored = score_candidate(candidate)
        decision = scored["model_decision"]
        out = {
            "rank": row["rank"],
            "candidate_id": row["candidate_id"],
            "score": round(decision.score, 6),
            "base_score": round(decision.base_score, 6),
            "penalty_multiplier": round(decision.penalty_multiplier, 6),
            "quality_tier": decision.quality_tier,
            "penalties": "|".join(decision.penalties),
            "title": candidate["profile"].get("current_title", ""),
            "years": candidate["profile"].get("years_of_experience", 0.0),
            "industry": candidate["profile"].get("current_industry", ""),
            "location": candidate["profile"].get("location", ""),
        }
        for weight in HYBRID_MODEL_WEIGHTS:
            out[f"component_{weight.feature}"] = round(decision.components.get(weight.feature, 0.0), 6)
        rows.append(out)
    write_model_report(rows, args.out_dir)
    print(f"Wrote ranking model report to {args.out_dir}")
    print(f"Model rows exported: {len(rows)}")


def read_ranked_submission(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda row: int(row["rank"]))
    return rows


if __name__ == "__main__":
    main()
