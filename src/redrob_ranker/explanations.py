"""Grounded reasoning text for the submission CSV."""

from __future__ import annotations

from typing import Any

from .config import SERVICE_INDUSTRIES


def build_reasoning(item: dict[str, Any], rank: int) -> str:
    candidate = item["candidate"]
    profile = candidate["profile"]
    signals = candidate["redrob_signals"]
    skills = ", ".join(item["matched_skills"][:3]) or "limited named AI skills"
    location = profile.get("location", "unknown location")
    parts = [
        f"{profile.get('current_title')} with {profile.get('years_of_experience'):.1f} yrs in {profile.get('current_industry')}; evidence includes {skills}.",
        f"Fit drivers: title {item['scores']['title']:.2f}, JD evidence {item['scores']['evidence']:.2f}, retrieval agreement {item['scores'].get('retrieval', 0):.2f}, hireability {item['scores'].get('hireability', 0):.2f}, response {signals.get('recruiter_response_rate', 0):.2f}, notice {signals.get('notice_period_days')}d, {location}.",
    ]
    concerns: list[str] = []
    if profile.get("country") != "India":
        concerns.append("outside India")
    if profile.get("current_industry") in SERVICE_INDUSTRIES:
        concerns.append("service-company background")
    if signals.get("notice_period_days", 0) > 60:
        concerns.append("long notice")
    if not signals.get("open_to_work_flag"):
        concerns.append("not marked open to work")
    if item["risk_reasons"]:
        concerns.append("; ".join(item["risk_reasons"]))
    if rank > 50 and concerns:
        parts.append("Concern: " + ", ".join(concerns[:2]) + ".")
    elif concerns and rank <= 20:
        parts.append("Watch: " + ", ".join(concerns[:1]) + ".")
    return " ".join(parts)
