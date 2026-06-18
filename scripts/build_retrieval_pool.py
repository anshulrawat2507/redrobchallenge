#!/usr/bin/env python3
"""Generate Phase 4 multi-retriever candidate pool reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from redrob_ranker.retrieval import build_retrieval_pool, write_retrieval_outputs  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Phase 4 multi-retriever candidate pool.")
    parser.add_argument("--candidates", default=ROOT / "candidates.jsonl", type=Path)
    parser.add_argument("--out-dir", default=ROOT / "reports", type=Path)
    parser.add_argument("--top-n", default=500, type=int)
    args = parser.parse_args()

    pool = build_retrieval_pool(args.candidates, top_n=args.top_n)
    write_retrieval_outputs(pool, args.out_dir)
    print(f"Wrote retrieval pool reports to {args.out_dir}")
    print(f"Pool candidates with positive agreement: {pool['total_pool_candidates']}")


if __name__ == "__main__":
    main()
