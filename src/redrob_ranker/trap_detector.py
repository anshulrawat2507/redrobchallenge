"""Phase 7 honeypot and trap detection.

The challenge explicitly warns about keyword stuffers, plain-language strong
candidates, behavioral twins, and subtle honeypots. This module makes those
checks explicit and reportable.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import NON_FIT_TITLES, SERVICE_INDUSTRIES, TODAY
from .features import candidate_text, company_score, evidence_score, parse_date, skill_score, title_score
from .io import iter_candidates


AI_CURIOSITY_TERMS = (
    "curious about ai",
    "chatgpt",
    "ai tools",
    "productivity and content creation",
    "ai-assisted content",
    "side project",
    "tutorial",
)


@dataclass
class TrapReport:
    candidate_id: str
    risk_score: float
    severity: str
    flags: list[str]
    warnings: list[str]

    def as_row(self) -> dict[str, Any]:
        row = asdict(self)
        row["flags"] = "|".join(self.flags)
        row["warnings"] = "|".join(self.warnings)
        return row


def detect_traps(
    candidate: dict[str, Any],
    text: str | None = None,
    title_fit: float | None = None,
    jd_evidence: float | None = None,
    trusted_skills: float | None = None,
    product_company: float | None = None,
) -> TrapReport:
    text = text if text is not None else candidate_text(candidate)
    profile = candidate["profile"]
    signals = candidate["redrob_signals"]
    jobs = candidate.get("career_history", [])
    title = profile.get("current_title", "").strip().lower()
    years = float(profile.get("years_of_experience", 0.0))
    title_fit = title_score(candidate) if title_fit is None else title_fit
    jd_evidence = evidence_score(text) if jd_evidence is None else jd_evidence
    trusted_skills = skill_score(candidate)[0] if trusted_skills is None else trusted_skills
    product_company = company_score(candidate) if product_company is None else product_company

    risk = 0.0
    flags: list[str] = []
    warnings: list[str] = []

    expert_zero = 0
    inflated_duration = 0
    max_plausible_months = years * 12 + 18
    for skill in candidate.get("skills", []):
        duration = skill.get("duration_months", 0)
        if skill.get("proficiency") == "expert" and duration <= 3 and skill.get("endorsements", 0) == 0:
            expert_zero += 1
        if duration > max_plausible_months:
            inflated_duration += 1
    if expert_zero:
        risk += min(0.35, 0.12 * expert_zero)
        flags.append("unsupported_expert_claims")
    if inflated_duration:
        risk += min(0.35, 0.10 * inflated_duration)
        flags.append("skill_duration_exceeds_experience")

    for job in jobs:
        start = parse_date(job.get("start_date"))
        end = parse_date(job.get("end_date")) or TODAY
        if start and end and start > end:
            risk += 0.35
            flags.append("invalid_career_dates")
            break

    if title in NON_FIT_TITLES:
        warnings.append("non_fit_current_title")
        if trusted_skills >= 0.45 and jd_evidence < 0.45:
            risk += 0.25
            flags.append("keyword_stuffing_non_fit_title")

    has_ai_curiosity_signal = any(term in text for term in AI_CURIOSITY_TERMS)
    if has_ai_curiosity_signal and title in NON_FIT_TITLES and trusted_skills >= 0.50 and jd_evidence < 0.55:
        risk += 0.12
        flags.append("ai_curiosity_or_tutorial_signal")
    elif has_ai_curiosity_signal and title_fit < 0.55 and trusted_skills >= 0.45 and jd_evidence < 0.45:
        risk += 0.10
        flags.append("ai_curiosity_or_tutorial_signal")
    elif has_ai_curiosity_signal and title_fit < 0.55:
        warnings.append("ai_curiosity_or_tutorial_signal")

    if jobs and all(job.get("industry") in SERVICE_INDUSTRIES for job in jobs):
        warnings.append("pure_services_career")
        if product_company <= 0.25 and jd_evidence < 0.65:
            risk += 0.12
            flags.append("pure_services_without_product_ai_evidence")

    last_active = parse_date(signals.get("last_active_date"))
    stale_days = (TODAY - last_active).days if last_active else 999
    if not signals.get("open_to_work_flag"):
        warnings.append("not_open_to_work")
    if stale_days > 180 and signals.get("recruiter_response_rate", 0.0) < 0.15 and not signals.get("open_to_work_flag"):
        risk += 0.15
        flags.append("stale_unresponsive_profile")

    if (
        signals.get("notice_period_days", 0) >= 120
        and signals.get("recruiter_response_rate", 0.0) < 0.25
        and stale_days > 90
    ):
        risk += 0.05
        flags.append("long_notice_low_response")
    elif signals.get("notice_period_days", 0) > 90:
        warnings.append("long_notice")

    if profile.get("country") != "India" and not signals.get("willing_to_relocate"):
        warnings.append("outside_india_no_relocation")

    if signals.get("offer_acceptance_rate", 0) < 0 and signals.get("interview_completion_rate", 0) > 0.95:
        risk += 0.05
        flags.append("behavioral_history_inconsistency")

    risk = min(0.95, risk)
    if risk >= 0.30:
        severity = "high"
    elif risk >= 0.10:
        severity = "medium"
    elif risk > 0:
        severity = "low"
    else:
        severity = "clean"
    return TrapReport(candidate["candidate_id"], round(risk, 4), severity, sorted(set(flags)), sorted(set(warnings)))


def build_trap_report(candidates_path: Path, top_n: int = 100) -> dict[str, Any]:
    reports = []
    flag_counts: Counter[str] = Counter()
    warning_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()
    for candidate in iter_candidates(candidates_path):
        report = detect_traps(candidate)
        severity_counts[report.severity] += 1
        for flag in report.flags:
            flag_counts[flag] += 1
        for warning in report.warnings:
            warning_counts[warning] += 1
        if report.risk_score > 0:
            profile = candidate["profile"]
            row = report.as_row()
            row.update(
                {
                    "title": profile.get("current_title", ""),
                    "industry": profile.get("current_industry", ""),
                    "location": profile.get("location", ""),
                    "country": profile.get("country", ""),
                    "years": profile.get("years_of_experience", 0.0),
                }
            )
            reports.append(row)
    reports.sort(key=lambda row: (-float(row["risk_score"]), row["candidate_id"]))
    return {
        "severity_counts": dict(severity_counts),
        "flag_counts": flag_counts.most_common(),
        "warning_counts": warning_counts.most_common(),
        "risk_candidate_count": len(reports),
        "top_risk_examples": reports[:top_n],
    }


def write_trap_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "trap_summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out_dir / "trap_summary.md").write_text(render_trap_summary(report), encoding="utf-8")
    _write_rows(out_dir / "trap_examples.csv", report["top_risk_examples"])


def render_trap_summary(report: dict[str, Any]) -> str:
    lines = [
        "# Phase 7 Trap Defense Report",
        "",
        f"- Risk-flagged candidates: {report['risk_candidate_count']}",
        "",
        "## Severity Counts",
        "",
    ]
    for severity, count in sorted(report["severity_counts"].items()):
        lines.append(f"- {severity}: {count}")
    lines.extend(["", "## Trap Flag Counts", ""])
    for flag, count in report["flag_counts"]:
        lines.append(f"- {flag}: {count}")
    lines.extend(["", "## Warning Counts", ""])
    for warning, count in report["warning_counts"]:
        lines.append(f"- {warning}: {count}")
    lines.extend(
        [
            "",
            "## How Phase 7 Helps",
            "",
            "- Trap checks are explicit and auditable instead of hidden in the final score.",
            "- Strong flags become model risk penalties; warnings remain visible for manual review.",
            "- The final top 100 can be audited against the same detector before submission.",
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
