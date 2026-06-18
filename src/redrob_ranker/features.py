"""Feature extraction and scoring primitives."""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any

from .config import (
    ADJACENT_TITLE_PATTERNS,
    AI_SKILLS,
    GOOD_CITIES,
    GOOD_INDUSTRIES,
    MUST_HAVE_TERMS,
    NON_FIT_TITLES,
    SERVICE_INDUSTRIES,
    STRONG_TITLE_PATTERNS,
    TARGET_CITIES,
    TODAY,
)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9+#./ -]+", " ", text.lower())


def candidate_text(candidate: dict[str, Any]) -> str:
    profile = candidate["profile"]
    career = candidate.get("career_history", [])
    education = candidate.get("education", [])
    skills = candidate.get("skills", [])
    parts = [
        profile.get("headline", ""),
        profile.get("summary", ""),
        profile.get("current_title", ""),
        profile.get("current_industry", ""),
        " ".join(job.get("title", "") + " " + job.get("description", "") + " " + job.get("industry", "") for job in career),
        " ".join(item.get("degree", "") + " " + item.get("field_of_study", "") for item in education),
        " ".join(skill.get("name", "") for skill in skills),
    ]
    return normalize(" ".join(parts))


def title_score(candidate: dict[str, Any]) -> float:
    titles = [candidate["profile"].get("current_title", "")] + [
        job.get("title", "") for job in candidate.get("career_history", [])
    ]
    current = candidate["profile"].get("current_title", "").strip().lower()
    if current in NON_FIT_TITLES:
        return 0.05
    if any(pattern.search(title) for pattern in STRONG_TITLE_PATTERNS for title in titles):
        return 1.0
    if any(pattern.search(title) for pattern in ADJACENT_TITLE_PATTERNS for title in titles):
        return 0.55
    return 0.25


def skill_score(candidate: dict[str, Any]) -> tuple[float, list[str]]:
    score = 0.0
    matched: list[str] = []
    for skill in candidate.get("skills", []):
        name = skill.get("name", "")
        key = name.lower()
        is_relevant = key in AI_SKILLS or any(
            term in key for term in ["retrieval", "ranking", "embedding", "search", "llm"]
        )
        if not is_relevant:
            continue
        proficiency = {"beginner": 0.45, "intermediate": 0.7, "advanced": 0.9, "expert": 1.0}.get(
            skill.get("proficiency", ""), 0.5
        )
        duration = clamp(skill.get("duration_months", 0) / 36.0)
        endorsements = clamp(math.log1p(skill.get("endorsements", 0)) / math.log(80))
        score += 0.55 * proficiency + 0.25 * duration + 0.20 * endorsements
        matched.append(name)
    return clamp(score / 7.0), matched[:6]


def evidence_score(text: str) -> float:
    total = sum(weight for term, weight in MUST_HAVE_TERMS.items() if term in text)
    return clamp(total / 24.0)


def experience_score(years: float) -> float:
    if 5.0 <= years <= 9.0:
        return 1.0
    if 4.0 <= years < 5.0 or 9.0 < years <= 11.0:
        return 0.72
    if 3.0 <= years < 4.0 or 11.0 < years <= 13.0:
        return 0.45
    return 0.2


def company_score(candidate: dict[str, Any]) -> float:
    jobs = candidate.get("career_history", [])
    industries = [job.get("industry", "") for job in jobs]
    product_months = sum(job.get("duration_months", 0) for job in jobs if job.get("industry") in GOOD_INDUSTRIES)
    service_months = sum(job.get("duration_months", 0) for job in jobs if job.get("industry") in SERVICE_INDUSTRIES)
    total_months = max(1, sum(job.get("duration_months", 0) for job in jobs))
    product_ratio = product_months / total_months
    if product_ratio >= 0.5:
        return 1.0
    if any(industry in GOOD_INDUSTRIES for industry in industries):
        return 0.75
    if service_months == total_months:
        return 0.2
    return 0.45


def location_score(candidate: dict[str, Any]) -> float:
    profile = candidate["profile"]
    location = profile.get("location", "")
    if profile.get("country") != "India":
        return 0.15
    city = location.split(",")[0].strip()
    if city in TARGET_CITIES:
        return 1.0
    if city in GOOD_CITIES:
        return 0.82
    if candidate["redrob_signals"].get("willing_to_relocate"):
        return 0.65
    return 0.45


def behavior_score(candidate: dict[str, Any]) -> float:
    signals = candidate["redrob_signals"]
    last_active = parse_date(signals.get("last_active_date"))
    if last_active:
        days = max(0, (TODAY - last_active).days)
        recency = math.exp(-days / 120.0)
    else:
        recency = 0.2
    response = signals.get("recruiter_response_rate", 0.0)
    response_time = 1.0 / (1.0 + signals.get("avg_response_time_hours", 72.0) / 48.0)
    notice = 1.0 - clamp((signals.get("notice_period_days", 90) - 15) / 105.0)
    completeness = clamp(signals.get("profile_completeness_score", 0) / 100.0)
    interview = signals.get("interview_completion_rate", 0.0)
    github = signals.get("github_activity_score", -1)
    github_score = 0.5 if github < 0 else clamp(github / 100.0)
    open_to_work = 1.0 if signals.get("open_to_work_flag") else 0.35
    verified = (
        int(bool(signals.get("verified_email")))
        + int(bool(signals.get("verified_phone")))
        + int(bool(signals.get("linkedin_connected")))
    ) / 3
    return (
        0.20 * recency
        + 0.18 * response
        + 0.10 * response_time
        + 0.14 * notice
        + 0.10 * completeness
        + 0.12 * interview
        + 0.08 * github_score
        + 0.05 * open_to_work
        + 0.03 * verified
    )


def honeypot_risk(candidate: dict[str, Any]) -> tuple[float, list[str]]:
    risk = 0.0
    reasons: list[str] = []
    years = candidate["profile"].get("years_of_experience", 0.0)
    max_plausible_months = years * 12 + 18
    expert_zero = 0
    inflated = 0
    for skill in candidate.get("skills", []):
        duration = skill.get("duration_months", 0)
        if duration > max_plausible_months:
            inflated += 1
        if skill.get("proficiency") == "expert" and duration <= 3 and skill.get("endorsements", 0) == 0:
            expert_zero += 1
    if expert_zero:
        risk += min(0.35, 0.10 * expert_zero)
        reasons.append("untrusted expert skills")
    if inflated:
        risk += min(0.35, 0.08 * inflated)
        reasons.append("skill durations exceed experience")
    for job in candidate.get("career_history", []):
        start = parse_date(job.get("start_date"))
        end = parse_date(job.get("end_date")) or TODAY
        if start and end and start > end:
            risk += 0.35
            reasons.append("invalid career dates")
    signals = candidate["redrob_signals"]
    if signals.get("offer_acceptance_rate", 0) < 0 and signals.get("interview_completion_rate", 0) > 0.95:
        risk += 0.05
        reasons.append("behavioral history inconsistency")
    return clamp(risk, 0.0, 0.85), reasons
