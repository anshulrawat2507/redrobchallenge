#!/usr/bin/env python3
"""Generate Phase 2 data intelligence reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from redrob_ranker.profiling import profile_dataset, write_profile_outputs  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile the Redrob candidate dataset for Phase 2 analysis.")
    parser.add_argument("--candidates", default=ROOT / "candidates.jsonl", type=Path)
    parser.add_argument("--out-dir", default=ROOT / "reports", type=Path)
    parser.add_argument("--top-n", default=30, type=int)
    args = parser.parse_args()

    profile = profile_dataset(args.candidates, top_n=args.top_n)
    write_profile_outputs(profile, args.out_dir)
    print(f"Wrote Phase 2 reports to {args.out_dir}")
    print(f"Total candidates profiled: {profile['total_candidates']}")


if __name__ == "__main__":
    main()
