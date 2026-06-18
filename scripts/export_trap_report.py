#!/usr/bin/env python3
"""Export Phase 7 trap and honeypot reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from redrob_ranker.trap_detector import build_trap_report, write_trap_outputs  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Export trap and honeypot detection report.")
    parser.add_argument("--candidates", default=ROOT / "candidates.jsonl", type=Path)
    parser.add_argument("--out-dir", default=ROOT / "reports", type=Path)
    parser.add_argument("--top-n", default=100, type=int)
    args = parser.parse_args()

    report = build_trap_report(args.candidates, top_n=args.top_n)
    write_trap_outputs(report, args.out_dir)
    print(f"Wrote trap report to {args.out_dir}")
    print(f"Risk-flagged candidates: {report['risk_candidate_count']}")


if __name__ == "__main__":
    main()
