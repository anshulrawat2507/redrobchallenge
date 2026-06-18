"""Input/output helpers for challenge files."""

from __future__ import annotations

import csv
import gzip
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .config import CSV_HEADER


def iter_candidates(path: Path) -> Iterator[dict[str, Any]]:
    """Stream candidate records from .jsonl or .jsonl.gz without network access."""

    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_submission(rows: list[dict[str, Any]], out_path: Path) -> None:
    """Write the exact CSV shape expected by the official validator."""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_HEADER)
        previous_score = 1.0
        for rank, row in enumerate(rows, start=1):
            score = min(previous_score, round(row["score"], 6))
            previous_score = score
            writer.writerow(
                [
                    row["candidate"]["candidate_id"],
                    rank,
                    f"{score:.6f}",
                    row["reasoning"],
                ]
            )
