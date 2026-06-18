"""Phase 6 hybrid ranking model.

This module owns the final scoring formula. Earlier phases extract evidence;
this layer turns those features into a deterministic, inspectable rank score.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from .config import NON_FIT_TITLES
from .feature_vector import CandidateFeatureVector
from .features import clamp


@dataclass(frozen=True)
class ModelWeight:
    feature: str
    weight: float
    reason: str


@dataclass
class ModelDecision:
    score: float
    base_score: float
    penalty_multiplier: float
    quality_tier: str
    components: dict[str, float]
    penalties: list[str]


HYBRID_MODEL_WEIGHTS = (
    ModelWeight("title_fit", 0.190, "Current/recent role must be applied AI, ML, search, ranking, or data-science oriented."),
    ModelWeight("jd_evidence", 0.200, "The JD primarily asks for retrieval, ranking, search, embeddings, and evaluation evidence."),
    ModelWeight("trusted_skills", 0.150, "Skill lists matter only when supported by proficiency, duration, and endorsements."),
    ModelWeight("product_company", 0.115, "Product-company context is explicitly preferred over pure services trajectories."),
    ModelWeight("experience_band", 0.095, "The role prefers 5-9 years, with flexibility for strong adjacent signals."),
    ModelWeight("behavior", 0.110, "Redrob behavioral signals determine whether the candidate is actually reachable."),
    ModelWeight("location", 0.075, "Pune/Noida and major Indian cities are logistically stronger."),
    ModelWeight("retrieval_agreement", 0.035, "Candidates found by multiple independent retrievers are more trustworthy."),
    ModelWeight("production_evidence", 0.010, "Production/deployment language separates real systems from demos."),
    ModelWeight("ranking_evaluation", 0.005, "NDCG/MRR/MAP/A-B evidence is a direct JD match."),
    ModelWeight("skill_assessment", 0.005, "Redrob skill assessments add light trust to claimed skills."),
    ModelWeight("hireability", 0.010, "Notice, activity, response, and interview reliability are practical hiring signals."),
)


def score_features(features: CandidateFeatureVector, current_title: str) -> ModelDecision:
    components = {
        weight.feature: getattr(features, weight.feature) * weight.weight
        for weight in HYBRID_MODEL_WEIGHTS
    }
    base_score = sum(components.values())
    penalty_multiplier = 1.0
    penalties: list[str] = []
    title = current_title.strip().lower()

    if title in NON_FIT_TITLES and features.jd_evidence < 0.65:
        penalty_multiplier *= 0.42
        penalties.append("non-fit title without enough JD evidence")
    if features.services_penalty >= 1.0 and features.product_company < 0.5 and features.jd_evidence < 0.85:
        penalty_multiplier *= 0.90
        penalties.append("pure services career without strong product AI evidence")
    if features.hireability < 0.35:
        penalty_multiplier *= 0.92
        penalties.append("low hireability")
    if features.title_fit < 0.55 and features.jd_evidence < 0.70:
        penalty_multiplier *= 0.70
        penalties.append("weak role and JD evidence")
    combined_risk = max(features.honeypot_risk, features.trap_risk)
    if combined_risk > 0:
        penalties.extend(features.risk_reasons or ["trap risk"])

    risk_multiplier = 1.0 - min(0.95, combined_risk * 3.0)
    final_score = clamp(base_score * penalty_multiplier * risk_multiplier)
    return ModelDecision(
        score=final_score,
        base_score=base_score,
        penalty_multiplier=penalty_multiplier * risk_multiplier,
        quality_tier=quality_tier(features),
        components=components,
        penalties=penalties,
    )


def quality_tier(features: CandidateFeatureVector) -> str:
    core = mean([features.title_fit, features.jd_evidence, features.trusted_skills, features.retrieval_agreement])
    logistics = mean([features.experience_band, features.product_company, features.location, features.hireability])
    if (
        core >= 0.92
        and logistics >= 0.72
        and max(features.honeypot_risk, features.trap_risk) == 0
        and features.services_penalty < 0.5
    ):
        return "A"
    if core >= 0.78 and max(features.honeypot_risk, features.trap_risk) <= 0.10:
        return "B"
    if core >= 0.55:
        return "C"
    return "D"


def model_weight_rows() -> list[dict[str, Any]]:
    return [
        {"feature": weight.feature, "weight": weight.weight, "reason": weight.reason}
        for weight in HYBRID_MODEL_WEIGHTS
    ]


def write_model_report(decisions: list[dict[str, Any]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize_model_decisions(decisions)
    (out_dir / "ranking_model_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "ranking_model_summary.md").write_text(render_model_report(summary), encoding="utf-8")
    _write_rows(out_dir / "ranking_model_weights.csv", model_weight_rows())
    _write_rows(out_dir / "ranking_model_top100.csv", decisions)


def summarize_model_decisions(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    tier_counts: dict[str, int] = {}
    penalty_counts: dict[str, int] = {}
    for row in decisions:
        tier_counts[row["quality_tier"]] = tier_counts.get(row["quality_tier"], 0) + 1
        for penalty in row["penalties"].split("|"):
            if penalty:
                penalty_counts[penalty] = penalty_counts.get(penalty, 0) + 1
    component_names = [weight.feature for weight in HYBRID_MODEL_WEIGHTS]
    return {
        "rows": len(decisions),
        "tier_counts": tier_counts,
        "penalty_counts": penalty_counts,
        "mean_score": round(mean(float(row["score"]) for row in decisions), 6) if decisions else 0.0,
        "mean_base_score": round(mean(float(row["base_score"]) for row in decisions), 6) if decisions else 0.0,
        "mean_penalty_multiplier": round(mean(float(row["penalty_multiplier"]) for row in decisions), 6) if decisions else 0.0,
        "mean_components": {
            name: round(mean(float(row[f"component_{name}"]) for row in decisions), 6) if decisions else 0.0
            for name in component_names
        },
        "weights": model_weight_rows(),
    }


def render_model_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Phase 6 Hybrid Ranking Model Report",
        "",
        f"- Rows analyzed: {summary['rows']}",
        f"- Mean final score: {summary['mean_score']}",
        f"- Mean base score: {summary['mean_base_score']}",
        f"- Mean penalty multiplier: {summary['mean_penalty_multiplier']}",
        "",
        "## Quality Tier Counts",
        "",
    ]
    for tier, count in sorted(summary["tier_counts"].items()):
        lines.append(f"- Tier {tier}: {count}")
    lines.extend(["", "## Penalty Counts", ""])
    if summary["penalty_counts"]:
        for penalty, count in sorted(summary["penalty_counts"].items()):
            lines.append(f"- {penalty}: {count}")
    else:
        lines.append("- none")
    lines.extend(["", "## Model Weights", ""])
    for row in summary["weights"]:
        lines.append(f"- {row['feature']}: {row['weight']} - {row['reason']}")
    lines.extend(["", "## Mean Weighted Components", ""])
    for feature, value in summary["mean_components"].items():
        lines.append(f"- {feature}: {value}")
    lines.extend(
        [
            "",
            "## How Phase 6 Helps",
            "",
            "- The final model is a named hybrid formula rather than scattered constants.",
            "- Guardrails make weak-role, pure-services, low-hireability, and risk cases visible.",
            "- Quality tiers make top-10/top-50 review faster before final submission.",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
