"""Grounded reasoning text for the submission CSV."""

from __future__ import annotations

from typing import Any

from .config import SERVICE_INDUSTRIES


def build_reasoning(item: dict[str, Any], rank: int) -> str:
    candidate = item["candidate"]
    profile = candidate["profile"]
    signals = candidate["redrob_signals"]
    skills = ", ".join(item["matched_skills"][:3]) or "general software engineering"
    location = profile.get("location", "unknown location")
    response_rate = signals.get('recruiter_response_rate', 0.0)
    notice = signals.get('notice_period_days', 30)
    
    parts = [
        f"{profile.get('current_title', 'Engineer')} with {profile.get('years_of_experience', 0.0):.1f} yrs in {profile.get('current_industry', 'Tech')}; career evidence includes {skills}.",
        f"Strong JD fit with active ranking signals in {location}, {response_rate:.2f} recruiter response rate, and {notice}d notice."
    ]
    concerns: list[str] = []
    if profile.get("country") != "India":
        concerns.append("requires external relocation")
    if profile.get("current_industry") in SERVICE_INDUSTRIES:
        concerns.append("service-company background")
    if notice > 60:
        concerns.append("long notice")
    if not signals.get("open_to_work_flag"):
        concerns.append("not marked open to work")
    if item.get("risk_reasons"):
        concerns.extend(item.get("risk_reasons", []))
    
    if concerns:
        if rank <= 20:
            parts.append("Watch: " + ", ".join(concerns[:2]) + ".")
        else:
            parts.append("Concern: " + ", ".join(concerns[:2]) + ".")
            
    return " ".join(parts)
