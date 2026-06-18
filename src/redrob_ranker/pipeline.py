"""End-to-end ranking pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import DEFAULT_LIMIT
from .explanations import build_reasoning
from .io import iter_candidates, write_submission
from .scoring import score_candidate


def rank_candidates(candidates_path: Path, limit: int = DEFAULT_LIMIT) -> list[dict[str, Any]]:
    scored = [score_candidate(candidate) for candidate in iter_candidates(candidates_path)]
    scored.sort(key=lambda item: (-item["score"], item["risk"], item["candidate"]["candidate_id"]))
    top = scored[:limit]
    for rank, item in enumerate(top, start=1):
        item["reasoning"] = build_reasoning(item, rank)
    return top


def run_ranking(candidates_path: Path, out_path: Path, limit: int = DEFAULT_LIMIT) -> None:
    write_submission(rank_candidates(candidates_path, limit), out_path)
