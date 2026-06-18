#!/usr/bin/env python3
"""Audit the generated top-100 submission for Phase 2 review."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from redrob_ranker.profiling import audit_submission, write_submission_audit  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit the current Redrob submission CSV.")
    parser.add_argument("--candidates", default=ROOT / "candidates.jsonl", type=Path)
    parser.add_argument("--submission", default=ROOT / "submission.csv", type=Path)
    parser.add_argument("--out-dir", default=ROOT / "reports", type=Path)
    parser.add_argument("--top-n", default=30, type=int)
    args = parser.parse_args()

    audit = audit_submission(args.candidates, args.submission, top_n=args.top_n)
    write_submission_audit(audit, args.out_dir)
    print(f"Wrote submission audit to {args.out_dir}")
    print(f"Submission rows audited: {audit['submission_rows']}")


if __name__ == "__main__":
    main()
