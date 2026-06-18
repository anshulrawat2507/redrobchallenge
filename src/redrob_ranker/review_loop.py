"""Phase 8 manual label review loop.

This module does not alter the official submission ranker. It exports a
curated review pack for human labeling and evaluates the labels with simple
ranking diagnostics so Phase 6 weights can be tuned against real feedback.
"""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from .config import NON_FIT_TITLES
from .explanations import build_reasoning
from .io import iter_candidates
from .ranking_model import HYBRID_MODEL_WEIGHTS
from .scoring import score_candidate


LABEL_GUIDE = {
    0: "reject / trap",
    1: "weak fit",
    2: "adjacent",
    3: "maybe",
    4: "strong fit",
    5: "perfect fit",
}

POSITIVE_FEATURES = [
    "current_score",
    "title_fit",
    "jd_evidence",
    "trusted_skills",
    "product_company",
    "experience_band",
    "behavior",
    "retrieval_agreement",
    "hireability",
]

RISK_FEATURES = ["honeypot_risk", "trap_risk", "services_penalty"]


def build_review_pack(
    candidates_path: Path,
    submission_path: Path,
    top_n: int = 150,
    boundary_n: int = 50,
    trap_n: int = 50,
    product_n: int = 50,
    non_fit_n: int = 50,
) -> list[dict[str, Any]]:
    ranked_ids = read_submission_ids(submission_path)
    candidates = {candidate["candidate_id"]: candidate for candidate in iter_candidates(candidates_path)}
    scored = [score_candidate(candidate) for candidate in candidates.values()]
    scored.sort(key=_ranking_key)

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_candidates(items: list[dict[str, Any]], bucket: str, limit: int) -> None:
        added = 0
        for item in items:
            candidate_id = item["candidate"]["candidate_id"]
            if candidate_id in seen:
                continue
            rows.append(_review_row(item, bucket, len(rows) + 1, ranked_ids))
            seen.add(candidate_id)
            added += 1
            if added >= limit:
                break

    add_candidates(scored[:top_n], "submission_top", top_n)
    add_candidates(scored[top_n : top_n + boundary_n], "boundary_watchlist", boundary_n)

    trap_watchlist = sorted(
        (item for item in scored if item["candidate"]["candidate_id"] not in seen),
        key=lambda item: (-_combined_risk(item), item["candidate"]["candidate_id"]),
    )
    add_candidates(trap_watchlist, "trap_watchlist", trap_n)

    product_watchlist = sorted(
        (item for item in scored if item["candidate"]["candidate_id"] not in seen),
        key=lambda item: (
            -item["scores"]["company"],
            -item["scores"]["evidence"],
            -item["scores"].get("retrieval", 0.0),
            item["candidate"]["candidate_id"],
        ),
    )
    add_candidates(product_watchlist, "product_watchlist", product_n)

    non_fit_watchlist = sorted(
        (
            item
            for item in scored
            if item["candidate"]["candidate_id"] not in seen
            and item["candidate"]["profile"].get("current_title", "").strip().lower() in NON_FIT_TITLES
        ),
        key=lambda item: (-item["scores"]["evidence"], -item["scores"]["skills"], item["candidate"]["candidate_id"]),
    )
    add_candidates(non_fit_watchlist, "non_fit_watchlist", non_fit_n)
    return rows


def evaluate_review_labels(rows: list[dict[str, Any]]) -> dict[str, Any]:
    labeled_rows = [row for row in rows if _label_value(row) is not None]
    if not labeled_rows:
        return {
            "labeled_rows": 0,
            "label_counts": {},
            "bucket_counts": dict(Counter(row.get("review_bucket", "unknown") for row in rows)),
            "ndcg_at_10": 0.0,
            "ndcg_at_50": 0.0,
            "signal_rows": [],
        }

    ranked_by_model = sorted(labeled_rows, key=lambda row: (-float(row.get("current_score", 0.0)), row["candidate_id"]))
    ideal = sorted(labeled_rows, key=lambda row: (-_label_value(row), row["candidate_id"]))
    signal_rows = _signal_rows(labeled_rows)
    return {
        "labeled_rows": len(labeled_rows),
        "label_counts": dict(sorted(Counter(_label_value(row) for row in labeled_rows).items())),
        "bucket_counts": dict(sorted(Counter(row.get("review_bucket", "unknown") for row in rows).items())),
        "ndcg_at_10": round(_ndcg(ranked_by_model, ideal, 10), 6),
        "ndcg_at_50": round(_ndcg(ranked_by_model, ideal, 50), 6),
        "mean_label": round(mean(_label_value(row) for row in labeled_rows), 6),
        "mean_model_score": round(mean(float(row.get("current_score", 0.0)) for row in labeled_rows), 6),
        "signal_rows": signal_rows,
        "top_signal_features": [row["feature"] for row in signal_rows[:5]],
        "bottom_signal_features": [row["feature"] for row in signal_rows[-5:]],
    }


def write_review_pack_outputs(rows: list[dict[str, Any]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize_review_pack(rows)
    (out_dir / "review_pack.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "review_pack.md").write_text(render_review_pack_report(summary), encoding="utf-8")
    _write_csv(out_dir / "review_pack.csv", rows)


def write_review_label_outputs(summary: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "review_label_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "review_label_summary.md").write_text(render_label_summary(summary), encoding="utf-8")
    _write_csv(out_dir / "review_label_signals.csv", summary.get("signal_rows", []))


def summarize_review_pack(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "review_rows": len(rows),
        "bucket_counts": dict(sorted(Counter(row["review_bucket"] for row in rows).items())),
        "label_guide": LABEL_GUIDE,
        "weights": _weight_rows(),
    }


def render_review_pack_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Phase 8 Manual Label Review Pack",
        "",
        f"- Rows exported: {summary['review_rows']}",
        "",
        "## Review Buckets",
        "",
    ]
    for bucket, count in summary["bucket_counts"].items():
        lines.append(f"- {bucket}: {count}")
    lines.extend(["", "## Label Guide", ""])
    for label, description in summary["label_guide"].items():
        lines.append(f"- {label}: {description}")
    lines.extend(
        [
            "",
            "## How Phase 8 Helps",
            "",
            "- Review time is concentrated on the cutoff, false negatives, and trap cases.",
            "- Labels can be evaluated with NDCG without changing the submission path.",
            "- The exported features let you tune Phase 6 weights with evidence instead of guesswork.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_label_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# Phase 8 Label Review Summary",
        "",
        f"- Labeled rows: {summary['labeled_rows']}",
        f"- NDCG@10: {summary['ndcg_at_10']}",
        f"- NDCG@50: {summary['ndcg_at_50']}",
        f"- Mean label: {summary.get('mean_label', 0.0)}",
        f"- Mean model score: {summary.get('mean_model_score', 0.0)}",
        "",
        "## Label Counts",
        "",
    ]
    if summary["label_counts"]:
        for label, count in summary["label_counts"].items():
            lines.append(f"- {label}: {count}")
    else:
        lines.append("- none")
    lines.extend(["", "## Bucket Counts", ""])
    for bucket, count in summary["bucket_counts"].items():
        lines.append(f"- {bucket}: {count}")
    lines.extend(["", "## Signal Alignment", ""])
    if summary.get("signal_rows"):
        for row in summary["signal_rows"]:
            lines.append(
                f"- {row['feature']}: alignment {row['alignment']} (good {row['good_mean']}, bad {row['bad_mean']})"
            )
    else:
        lines.append("- no labels yet")
    lines.extend(
        [
            "",
            "## How Phase 8 Helps",
            "",
            "- The label set converts intuition into a repeatable feedback loop.",
            "- Alignment shows which features separate good and bad candidates in the right direction.",
            "- Use this only for tuning and validation; keep the official CSV contract untouched.",
        ]
    )
    return "\n".join(lines) + "\n"


def read_submission_ids(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda row: int(row["rank"]))
    return [row["candidate_id"] for row in rows]


def _review_row(item: dict[str, Any], review_bucket: str, bucket_rank: int, ranked_ids: list[str]) -> dict[str, Any]:
    candidate = item["candidate"]
    profile = candidate["profile"]
    features = item["features"]
    return {
        "candidate_id": candidate["candidate_id"],
        "submission_rank": _rank_of(candidate["candidate_id"], ranked_ids),
        "review_bucket": review_bucket,
        "bucket_rank": bucket_rank,
        "current_score": round(float(item["score"]), 6),
        "base_score": round(float(item["model_decision"].base_score), 6),
        "penalty_multiplier": round(float(item["model_decision"].penalty_multiplier), 6),
        "quality_tier": item["model_decision"].quality_tier,
        "current_title": profile.get("current_title", ""),
        "current_industry": profile.get("current_industry", ""),
        "years_of_experience": float(profile.get("years_of_experience", 0.0)),
        "location": profile.get("location", ""),
        "country": profile.get("country", ""),
        "title_fit": round(features.title_fit, 6),
        "jd_evidence": round(features.jd_evidence, 6),
        "trusted_skills": round(features.trusted_skills, 6),
        "product_company": round(features.product_company, 6),
        "experience_band": round(features.experience_band, 6),
        "behavior": round(features.behavior, 6),
        "retrieval_agreement": round(features.retrieval_agreement, 6),
        "hireability": round(features.hireability, 6),
        "honeypot_risk": round(features.honeypot_risk, 6),
        "trap_risk": round(features.trap_risk, 6),
        "services_penalty": round(features.services_penalty, 6),
        "matched_skills": "|".join(features.matched_skills),
        "retrieval_sources": "|".join(features.retrieval_sources),
        "risk_reasons": "|".join(features.risk_reasons),
        "trap_flags": "|".join(features.trap_flags),
        "trap_warnings": "|".join(features.trap_warnings),
        "reasoning": build_reasoning(item, _rank_of(candidate["candidate_id"], ranked_ids) or bucket_rank),
        "human_label": "",
        "human_notes": "",
    }


def _ndcg(ranked: list[dict[str, Any]], ideal: list[dict[str, Any]], k: int) -> float:
    ranked_k = ranked[:k]
    ideal_k = ideal[:k]
    return _dcg(ranked_k) / _dcg(ideal_k) if ideal_k and _dcg(ideal_k) > 0 else 0.0


def _dcg(rows: list[dict[str, Any]]) -> float:
    total = 0.0
    for index, row in enumerate(rows, start=1):
        label = _label_value(row) or 0
        total += (2**label - 1) / math.log2(index + 1)
    return total


def _label_value(row: dict[str, Any]) -> int | None:
    value = row.get("human_label") or row.get("label")
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    if text.isdigit():
        label = int(text)
    else:
        label = {"reject": 0, "trap": 0, "weak": 1, "adjacent": 2, "maybe": 3, "strong": 4, "perfect": 5}.get(text)
    return label if label is not None and 0 <= label <= 5 else None


def _signal_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signal_rows = []
    for feature in POSITIVE_FEATURES + RISK_FEATURES:
        good = [float(row.get(feature, 0.0)) for row in rows if (_label_value(row) or 0) >= 4]
        bad = [float(row.get(feature, 0.0)) for row in rows if (_label_value(row) or 0) <= 1]
        good_mean = round(mean(good), 6) if good else 0.0
        bad_mean = round(mean(bad), 6) if bad else 0.0
        alignment = round((good_mean - bad_mean) if feature not in RISK_FEATURES else (bad_mean - good_mean), 6)
        signal_rows.append(
            {
                "feature": feature,
                "current_weight": _current_weight(feature),
                "good_mean": good_mean,
                "bad_mean": bad_mean,
                "alignment": alignment,
                "recommendation": _recommendation(feature, alignment),
            }
        )
    signal_rows.sort(key=lambda row: (-row["alignment"], row["feature"]))
    return signal_rows


def _current_weight(feature: str) -> float:
    for weight in HYBRID_MODEL_WEIGHTS:
        if weight.feature == feature:
            return weight.weight
    return 0.0


def _recommendation(feature: str, alignment: float) -> str:
    if feature in RISK_FEATURES:
        return "risk separation looks strong" if alignment >= 0.15 else "consider a stronger risk penalty"
    return "signal is separating good and bad rows" if alignment >= 0.15 else "candidate for weight review"


def _combined_risk(item: dict[str, Any]) -> float:
    return max(float(item["risk"]), float(item["features"].trap_risk), float(item["features"].honeypot_risk))


def _rank_of(candidate_id: str, ranked_ids: list[str]) -> int:
    try:
        return ranked_ids.index(candidate_id) + 1
    except ValueError:
        return 0


def _ranking_key(item: dict[str, Any]) -> tuple[float, float, str]:
    return (-float(item["score"]), float(item["risk"]), item["candidate"]["candidate_id"])


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _weight_rows() -> list[dict[str, Any]]:
    return [{"feature": weight.feature, "weight": weight.weight, "reason": weight.reason} for weight in HYBRID_MODEL_WEIGHTS]