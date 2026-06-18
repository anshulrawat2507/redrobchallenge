#!/usr/bin/env python3
"""Export a Phase 8 manual review pack."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from redrob_ranker.review_loop import build_review_pack, write_review_pack_outputs  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the Phase 8 review pack for human labeling.")
    parser.add_argument("--candidates", default=ROOT / "candidates.jsonl", type=Path)
    parser.add_argument("--submission", default=ROOT / "submission.csv", type=Path)
    parser.add_argument("--out-dir", default=ROOT / "reports", type=Path)
    parser.add_argument("--top-n", default=150, type=int)
    parser.add_argument("--boundary-n", default=50, type=int)
    parser.add_argument("--trap-n", default=50, type=int)
    parser.add_argument("--product-n", default=50, type=int)
    parser.add_argument("--non-fit-n", default=50, type=int)
    args = parser.parse_args()

    rows = build_review_pack(
        args.candidates,
        args.submission,
        top_n=args.top_n,
        boundary_n=args.boundary_n,
        trap_n=args.trap_n,
        product_n=args.product_n,
        non_fit_n=args.non_fit_n,
    )
    write_review_pack_outputs(rows, args.out_dir)
    print(f"Wrote review pack to {args.out_dir}")
    print(f"Review rows exported: {len(rows)}")


if __name__ == "__main__":
    main()