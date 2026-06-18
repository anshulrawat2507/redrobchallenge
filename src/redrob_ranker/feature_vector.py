"""Phase 5 feature-vector extraction.

The ranker still writes a simple CSV, but internally each candidate now has a
reviewable set of feature scores. This makes tuning safer and helps explain the
system during manual review or interviews.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Any

from .config import AI_SKILLS, GOOD_INDUSTRIES, SERVICE_INDUSTRIES, TODAY
from .features import (
    behavior_score,
    candidate_text,
    clamp,
    company_score,
    evidence_score,
    experience_score,
    honeypot_risk,
    location_score,
    parse_date,
    skill_score,
    title_score,
)
from .retrieval import EVALUATION_TERMS, PRODUCTION_TERMS, retrieval_signals
from .trap_detector import detect_traps


@dataclass
class CandidateFeatureVector:
    candidate_id: str
    title_fit: float
    seniority: float
    experience_band: float
    jd_evidence: float
    ranking_evaluation: float
    production_evidence: float
    trusted_skills: float
    skill_assessment: float
    product_company: float
    services_penalty: float
    location: float
    notice_period: float
    activity: float
    response: float
    github: float
    profile_completeness: float
    hireability: float
    behavior: float
    retrieval_agreement: float
    honeypot_risk: float
    trap_risk: float
    matched_skills: list[str]
    retrieval_sources: list[str]
    risk_reasons: list[str]
    trap_flags: list[str]
    trap_warnings: list[str]

    def as_row(self) -> dict[str, Any]:
        row = asdict(self)
        row["matched_skills"] = "|".join(self.matched_skills)
        row["retrieval_sources"] = "|".join(self.retrieval_sources)
        row["risk_reasons"] = "|".join(self.risk_reasons)
        row["trap_flags"] = "|".join(self.trap_flags)
        row["trap_warnings"] = "|".join(self.trap_warnings)
        return row


def extract_feature_vector(candidate: dict[str, Any]) -> CandidateFeatureVector:
    text = candidate_text(candidate)
    signals = candidate["redrob_signals"]
    skill_value, matched_skills = skill_score(candidate)
    risk, risk_reasons = honeypot_risk(candidate)
    retrieval = retrieval_signals(candidate, text)
    trap = detect_traps(
        candidate,
        text=text,
        title_fit=title_score(candidate),
        jd_evidence=evidence_score(text),
        trusted_skills=skill_value,
        product_company=company_score(candidate),
    )
    return CandidateFeatureVector(
        candidate_id=candidate["candidate_id"],
        title_fit=title_score(candidate),
        seniority=seniority_score(candidate),
        experience_band=experience_score(candidate["profile"].get("years_of_experience", 0.0)),
        jd_evidence=evidence_score(text),
        ranking_evaluation=term_group_score(text, EVALUATION_TERMS, target_hits=2),
        production_evidence=term_group_score(text, PRODUCTION_TERMS, target_hits=3),
        trusted_skills=skill_value,
        skill_assessment=skill_assessment_score(candidate),
        product_company=company_score(candidate),
        services_penalty=services_penalty(candidate),
        location=location_score(candidate),
        notice_period=notice_period_score(signals.get("notice_period_days", 90)),
        activity=activity_score(signals),
        response=response_score(signals),
        github=github_score(signals.get("github_activity_score", -1)),
        profile_completeness=clamp(signals.get("profile_completeness_score", 0) / 100.0),
        hireability=hireability_score(signals),
        behavior=behavior_score(candidate),
        retrieval_agreement=retrieval["agreement_score"],
        honeypot_risk=risk,
        trap_risk=trap.risk_score,
        matched_skills=matched_skills,
        retrieval_sources=retrieval["sources"],
        risk_reasons=sorted(set(risk_reasons + trap.flags)),
        trap_flags=trap.flags,
        trap_warnings=trap.warnings,
    )


def seniority_score(candidate: dict[str, Any]) -> float:
    profile = candidate["profile"]
    title = profile.get("current_title", "").lower()
    years = profile.get("years_of_experience", 0.0)
    title_signal = 0.55
    if any(term in title for term in ["senior", "lead", "staff"]):
        title_signal = 1.0
    elif any(term in title for term in ["ml engineer", "ai engineer", "data scientist", "search engineer"]):
        title_signal = 0.82
    if years < 4:
        experience_signal = 0.35
    elif years < 5:
        experience_signal = 0.65
    elif years <= 9:
        experience_signal = 1.0
    elif years <= 12:
        experience_signal = 0.70
    else:
        experience_signal = 0.45
    return clamp(0.55 * experience_signal + 0.45 * title_signal)


def term_group_score(text: str, terms: set[str], target_hits: int) -> float:
    hits = sum(1 for term in terms if term in text)
    return clamp(hits / max(1, target_hits))


def skill_assessment_score(candidate: dict[str, Any]) -> float:
    scores = []
    assessments = candidate["redrob_signals"].get("skill_assessment_scores", {})
    for name, score in assessments.items():
        key = name.lower()
        if key in AI_SKILLS or any(term in key for term in ["retrieval", "ranking", "embedding", "search", "llm", "nlp"]):
            scores.append(float(score) / 100.0)
    return clamp(mean(scores)) if scores else 0.0


def services_penalty(candidate: dict[str, Any]) -> float:
    jobs = candidate.get("career_history", [])
    if jobs and all(job.get("industry") in SERVICE_INDUSTRIES for job in jobs):
        return 1.0
    if candidate["profile"].get("current_industry") in SERVICE_INDUSTRIES:
        return 0.5
    return 0.0


def notice_period_score(days: int | float) -> float:
    return 1.0 - clamp((float(days) - 15.0) / 105.0)


def activity_score(signals: dict[str, Any], today: date = TODAY) -> float:
    last_active = parse_date(signals.get("last_active_date"))
    if not last_active:
        recency = 0.2
    else:
        days = max(0, (today - last_active).days)
        if days <= 30:
            recency = 1.0
        elif days <= 90:
            recency = 0.75
        elif days <= 180:
            recency = 0.45
        else:
            recency = 0.20
    open_to_work = 1.0 if signals.get("open_to_work_flag") else 0.35
    applications = clamp(signals.get("applications_submitted_30d", 0) / 10.0)
    saves = clamp(signals.get("saved_by_recruiters_30d", 0) / 15.0)
    return clamp(0.45 * recency + 0.30 * open_to_work + 0.10 * applications + 0.15 * saves)


def response_score(signals: dict[str, Any]) -> float:
    rate = clamp(signals.get("recruiter_response_rate", 0.0))
    speed = 1.0 / (1.0 + signals.get("avg_response_time_hours", 72.0) / 48.0)
    return clamp(0.75 * rate + 0.25 * speed)


def github_score(value: int | float) -> float:
    if value < 0:
        return 0.35
    return clamp(float(value) / 100.0)


def hireability_score(signals: dict[str, Any]) -> float:
    verified = (
        int(bool(signals.get("verified_email")))
        + int(bool(signals.get("verified_phone")))
        + int(bool(signals.get("linkedin_connected")))
    ) / 3
    return clamp(
        0.25 * activity_score(signals)
        + 0.25 * response_score(signals)
        + 0.20 * notice_period_score(signals.get("notice_period_days", 90))
        + 0.20 * signals.get("interview_completion_rate", 0.0)
        + 0.10 * verified
    )


def summarize_feature_vectors(vectors: list[CandidateFeatureVector]) -> dict[str, Any]:
    feature_names = [
        "title_fit",
        "seniority",
        "experience_band",
        "jd_evidence",
        "ranking_evaluation",
        "production_evidence",
        "trusted_skills",
        "skill_assessment",
        "product_company",
        "services_penalty",
        "location",
        "notice_period",
        "activity",
        "response",
        "github",
        "profile_completeness",
        "hireability",
        "behavior",
        "retrieval_agreement",
        "honeypot_risk",
        "trap_risk",
    ]
    rows = [vector.as_row() for vector in vectors]
    return {
        "candidate_count": len(vectors),
        "feature_means": {
            name: round(mean(float(row[name]) for row in rows), 4) if rows else 0.0
            for name in feature_names
        },
        "risk_candidate_count": sum(1 for vector in vectors if max(vector.honeypot_risk, vector.trap_risk) > 0),
        "low_hireability_count": sum(1 for vector in vectors if vector.hireability < 0.45),
        "low_evidence_count": sum(1 for vector in vectors if vector.jd_evidence < 0.45),
    }


def render_feature_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Phase 5 Feature Engineering Report",
        "",
        f"- Candidate rows analyzed: {summary['candidate_count']}",
        f"- Risk-flagged candidates: {summary['risk_candidate_count']}",
        f"- Low-hireability candidates: {summary['low_hireability_count']}",
        f"- Low-JD-evidence candidates: {summary['low_evidence_count']}",
        "",
        "## Feature Means",
        "",
    ]
    for name, value in summary["feature_means"].items():
        lines.append(f"- {name}: {value}")
    lines.extend(
        [
            "",
            "## How Phase 5 Helps",
            "",
            "- Each candidate can be audited as a row of explicit model features.",
            "- Ranking changes can be debugged by checking which feature moved, not by guessing from a single score.",
            "- The feature report supports manual top-100 review before final submission.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_feature_outputs(vectors: list[CandidateFeatureVector], out_dir: Path) -> None:
    import csv

    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [vector.as_row() for vector in vectors]
    summary = summarize_feature_vectors(vectors)
    (out_dir / "feature_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "feature_summary.md").write_text(render_feature_report(summary), encoding="utf-8")
    if not rows:
        (out_dir / "feature_vectors_top100.csv").write_text("", encoding="utf-8")
        return
    with (out_dir / "feature_vectors_top100.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
