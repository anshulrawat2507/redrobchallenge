#!/usr/bin/env python3
"""Export the Phase 3 JD rubric report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from redrob_ranker.rubric import write_rubric_report  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the structured Senior AI Engineer JD rubric.")
    parser.add_argument("--out", default=ROOT / "reports" / "jd_rubric.md", type=Path)
    args = parser.parse_args()
    write_rubric_report(args.out)
    print(f"Wrote JD rubric report to {args.out}")


if __name__ == "__main__":
    main()
