#!/usr/bin/env python3
"""Analyze Phase 8 manual labels and export tuning diagnostics."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from redrob_ranker.review_loop import evaluate_review_labels, write_review_label_outputs  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze the Phase 8 labeled review pack.")
    parser.add_argument("--labels", default=ROOT / "reports" / "review_pack.csv", type=Path)
    parser.add_argument("--out-dir", default=ROOT / "reports", type=Path)
    args = parser.parse_args()

    rows = read_rows(args.labels)
    summary = evaluate_review_labels(rows)
    write_review_label_outputs(summary, args.out_dir)
    print(f"Wrote label diagnostics to {args.out_dir}")
    print(f"Labeled rows analyzed: {summary['labeled_rows']}")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    main()