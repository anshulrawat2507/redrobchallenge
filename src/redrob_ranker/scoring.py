"""Candidate scoring orchestration."""

from __future__ import annotations

from typing import Any

from .feature_vector import extract_feature_vector
from .ranking_model import score_features


def score_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    features = extract_feature_vector(candidate)
    decision = score_features(features, candidate["profile"].get("current_title", ""))
    scores = {
        "title": features.title_fit,
        "skills": features.trusted_skills,
        "evidence": features.jd_evidence,
        "experience": features.experience_band,
        "company": features.product_company,
        "location": features.location,
        "behavior": features.behavior,
        "retrieval": features.retrieval_agreement,
        "assessment": features.skill_assessment,
        "hireability": features.hireability,
        "seniority": features.seniority,
        "production": features.production_evidence,
        "evaluation": features.ranking_evaluation,
    }
    return {
        "candidate": candidate,
        "score": decision.score,
        "scores": scores,
        "model_decision": decision,
        "features": features,
        "matched_skills": features.matched_skills,
        "retrieval_sources": features.retrieval_sources,
        "risk": features.honeypot_risk,
        "risk_reasons": features.risk_reasons,
    }
