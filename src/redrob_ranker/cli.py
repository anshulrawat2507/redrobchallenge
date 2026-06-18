"""Command-line interface for the ranking pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import DEFAULT_LIMIT
from .pipeline import run_ranking


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rank Redrob candidates for the Senior AI Engineer JD.")
    parser.add_argument("--candidates", default="candidates.jsonl", type=Path, help="Input .jsonl or .jsonl.gz candidate file.")
    parser.add_argument("--out", default="submission.csv", type=Path, help="Output CSV path.")
    parser.add_argument("--limit", default=DEFAULT_LIMIT, type=int, help="Number of candidates to rank; final submission uses 100.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run_ranking(args.candidates, args.out, args.limit)
