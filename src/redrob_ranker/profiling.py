"""Dataset profiling for Phase 2 data intelligence."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Any

from .config import GOOD_INDUSTRIES, SERVICE_INDUSTRIES, TODAY
from .features import honeypot_risk
from .io import iter_candidates
from .rubric import evidence_terms
from .trap_detector import detect_traps


AI_TITLE_PATTERN = re.compile(
    r"\b(ai|ml|machine learning|data scientist|applied ml|applied scientist|search|recommendation|ranking|nlp)\b",
    re.I,
)
ADJACENT_TITLE_PATTERN = re.compile(
    r"\b(data engineer|analytics engineer|backend engineer|software engineer|cloud engineer|devops|full stack|python developer)\b",
    re.I,
)
NON_FIT_TITLES = {
    "hr manager",
    "marketing manager",
    "content writer",
    "accountant",
    "sales executive",
    "graphic designer",
    "mechanical engineer",
    "civil engineer",
    "customer support",
    "operations manager",
}

JD_EVIDENCE_TERMS = list(evidence_terms())


def _safe_average(values: list[float]) -> float:
    return round(mean(values), 4) if values else 0.0


def _safe_median(values: list[float]) -> float:
    return round(median(values), 4) if values else 0.0


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * pct)))
    return round(ordered[index], 4)


def _candidate_text(candidate: dict[str, Any]) -> str:
    profile = candidate["profile"]
    jobs = candidate.get("career_history", [])
    skills = candidate.get("skills", [])
    parts = [
        profile.get("headline", ""),
        profile.get("summary", ""),
        profile.get("current_title", ""),
        profile.get("current_industry", ""),
        " ".join(job.get("title", "") + " " + job.get("description", "") for job in jobs),
        " ".join(skill.get("name", "") for skill in skills),
    ]
    return " ".join(parts).lower()


def _days_since(date_value: str | None) -> int | None:
    if not date_value:
        return None
    try:
        return (TODAY - datetime.strptime(date_value[:10], "%Y-%m-%d").date()).days
    except ValueError:
        return None


def _bucket_experience(years: float) -> str:
    if years < 3:
        return "under_3"
    if years < 5:
        return "3_to_5"
    if years <= 9:
        return "5_to_9"
    if years <= 12:
        return "9_to_12"
    return "over_12"


def _bucket_notice(days: int) -> str:
    if days <= 30:
        return "0_to_30"
    if days <= 60:
        return "31_to_60"
    if days <= 90:
        return "61_to_90"
    return "over_90"


def profile_dataset(candidates_path: Path, top_n: int = 30) -> dict[str, Any]:
    counters = {
        "titles": Counter(),
        "industries": Counter(),
        "countries": Counter(),
        "locations": Counter(),
        "skills": Counter(),
        "experience_buckets": Counter(),
        "notice_buckets": Counter(),
        "risk_reasons": Counter(),
        "jd_terms": Counter(),
    }
    numeric = {
        "experience": [],
        "response_rate": [],
        "avg_response_hours": [],
        "profile_completeness": [],
        "github_activity": [],
        "interview_completion": [],
        "saved_by_recruiters_30d": [],
        "applications_submitted_30d": [],
    }
    segments = Counter()
    risk_examples: list[dict[str, Any]] = []
    strong_pool_examples: list[dict[str, Any]] = []

    total = 0
    for candidate in iter_candidates(candidates_path):
        total += 1
        profile = candidate["profile"]
        signals = candidate["redrob_signals"]
        jobs = candidate.get("career_history", [])
        title = profile.get("current_title", "")
        industry = profile.get("current_industry", "")
        country = profile.get("country", "")
        text = _candidate_text(candidate)

        counters["titles"][title] += 1
        counters["industries"][industry] += 1
        counters["countries"][country] += 1
        counters["locations"][profile.get("location", "")] += 1
        counters["experience_buckets"][_bucket_experience(profile.get("years_of_experience", 0.0))] += 1
        counters["notice_buckets"][_bucket_notice(signals.get("notice_period_days", 0))] += 1
        for skill in candidate.get("skills", []):
            counters["skills"][skill.get("name", "")] += 1
        for term in JD_EVIDENCE_TERMS:
            if term in text:
                counters["jd_terms"][term] += 1

        numeric["experience"].append(float(profile.get("years_of_experience", 0.0)))
        numeric["response_rate"].append(float(signals.get("recruiter_response_rate", 0.0)))
        numeric["avg_response_hours"].append(float(signals.get("avg_response_time_hours", 0.0)))
        numeric["profile_completeness"].append(float(signals.get("profile_completeness_score", 0.0)))
        numeric["github_activity"].append(float(signals.get("github_activity_score", -1)))
        numeric["interview_completion"].append(float(signals.get("interview_completion_rate", 0.0)))
        numeric["saved_by_recruiters_30d"].append(float(signals.get("saved_by_recruiters_30d", 0)))
        numeric["applications_submitted_30d"].append(float(signals.get("applications_submitted_30d", 0)))

        if country == "India":
            segments["india"] += 1
        if signals.get("open_to_work_flag"):
            segments["open_to_work"] += 1
        days_since_active = _days_since(signals.get("last_active_date"))
        if days_since_active is not None and days_since_active <= 30:
            segments["active_30d"] += 1
        if days_since_active is not None and days_since_active <= 90:
            segments["active_90d"] += 1
        if signals.get("github_activity_score", -1) >= 0:
            segments["github_linked"] += 1
        if signals.get("skill_assessment_scores"):
            segments["has_skill_assessment"] += 1
        if AI_TITLE_PATTERN.search(title):
            segments["ai_title"] += 1
        if ADJACENT_TITLE_PATTERN.search(title):
            segments["adjacent_title"] += 1
        if title.lower() in NON_FIT_TITLES:
            segments["non_fit_title"] += 1
        if industry in GOOD_INDUSTRIES:
            segments["product_industry"] += 1
        if industry in SERVICE_INDUSTRIES:
            segments["service_industry"] += 1
        if jobs and all(job.get("industry") in SERVICE_INDUSTRIES for job in jobs):
            segments["pure_services_career"] += 1
        if 5.0 <= profile.get("years_of_experience", 0.0) <= 9.0:
            segments["experience_5_to_9"] += 1

        risk, reasons = honeypot_risk(candidate)
        trap = detect_traps(candidate)
        risk = max(risk, trap.risk_score)
        reasons = sorted(set(reasons + trap.flags))
        if risk > 0:
            segments["risk_flagged"] += 1
            for reason in reasons:
                counters["risk_reasons"][reason] += 1
            if len(risk_examples) < top_n:
                risk_examples.append(_candidate_snapshot(candidate, risk, reasons))

        evidence_hits = sum(1 for term in JD_EVIDENCE_TERMS if term in text)
        if evidence_hits >= 4 and len(strong_pool_examples) < top_n:
            strong_pool_examples.append(
                _candidate_snapshot(candidate, risk, reasons, extra={"jd_evidence_hits": evidence_hits})
            )

    return {
        "total_candidates": total,
        "segments": dict(segments),
        "top_titles": counters["titles"].most_common(top_n),
        "top_industries": counters["industries"].most_common(top_n),
        "countries": counters["countries"].most_common(top_n),
        "top_locations": counters["locations"].most_common(top_n),
        "top_skills": counters["skills"].most_common(top_n),
        "experience_buckets": dict(counters["experience_buckets"]),
        "notice_buckets": dict(counters["notice_buckets"]),
        "jd_term_coverage": counters["jd_terms"].most_common(),
        "risk_reasons": counters["risk_reasons"].most_common(),
        "numeric_summary": {
            name: {
                "mean": _safe_average(values),
                "median": _safe_median(values),
                "p10": _percentile(values, 0.10),
                "p90": _percentile(values, 0.90),
                "min": round(min(values), 4) if values else 0.0,
                "max": round(max(values), 4) if values else 0.0,
            }
            for name, values in numeric.items()
        },
        "risk_examples": risk_examples,
        "strong_pool_examples": strong_pool_examples,
    }


def _candidate_snapshot(
    candidate: dict[str, Any],
    risk: float,
    reasons: list[str],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile = candidate["profile"]
    signals = candidate["redrob_signals"]
    row = {
        "candidate_id": candidate["candidate_id"],
        "title": profile.get("current_title", ""),
        "industry": profile.get("current_industry", ""),
        "location": profile.get("location", ""),
        "country": profile.get("country", ""),
        "years": profile.get("years_of_experience", 0.0),
        "open_to_work": signals.get("open_to_work_flag", False),
        "response_rate": signals.get("recruiter_response_rate", 0.0),
        "notice_days": signals.get("notice_period_days", 0),
        "risk": round(risk, 4),
        "risk_reasons": "; ".join(reasons),
    }
    if extra:
        row.update(extra)
    return row


def write_profile_outputs(profile: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "profile_summary.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    (out_dir / "profile_summary.md").write_text(render_markdown_report(profile), encoding="utf-8")
    _write_rows(out_dir / "risk_examples.csv", profile["risk_examples"])
    _write_rows(out_dir / "strong_pool_examples.csv", profile["strong_pool_examples"])


def audit_submission(candidates_path: Path, submission_path: Path, top_n: int = 30) -> dict[str, Any]:
    candidates = {candidate["candidate_id"]: candidate for candidate in iter_candidates(candidates_path)}
    rows: list[dict[str, Any]] = []
    with submission_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            candidate = candidates.get(row["candidate_id"])
            if not candidate:
                continue
            profile = candidate["profile"]
            signals = candidate["redrob_signals"]
            risk, reasons = honeypot_risk(candidate)
            text = _candidate_text(candidate)
            rows.append(
                {
                    "rank": int(row["rank"]),
                    "candidate_id": row["candidate_id"],
                    "score": float(row["score"]),
                    "title": profile.get("current_title", ""),
                    "industry": profile.get("current_industry", ""),
                    "location": profile.get("location", ""),
                    "country": profile.get("country", ""),
                    "years": profile.get("years_of_experience", 0.0),
                    "open_to_work": signals.get("open_to_work_flag", False),
                    "response_rate": signals.get("recruiter_response_rate", 0.0),
                    "notice_days": signals.get("notice_period_days", 0),
                    "risk": round(risk, 4),
                    "risk_reasons": "; ".join(reasons),
                    "jd_evidence_hits": sum(1 for term in JD_EVIDENCE_TERMS if term in text),
                }
            )
    rows.sort(key=lambda item: item["rank"])
    title_counts = Counter(row["title"] for row in rows)
    industry_counts = Counter(row["industry"] for row in rows)
    country_counts = Counter(row["country"] for row in rows)
    segment_counts = Counter()
    for row in rows:
        title = row["title"]
        if AI_TITLE_PATTERN.search(title):
            segment_counts["ai_title"] += 1
        if ADJACENT_TITLE_PATTERN.search(title):
            segment_counts["adjacent_title"] += 1
        if title.lower() in NON_FIT_TITLES:
            segment_counts["non_fit_title"] += 1
        if row["industry"] in GOOD_INDUSTRIES:
            segment_counts["product_industry"] += 1
        if row["industry"] in SERVICE_INDUSTRIES:
            segment_counts["service_industry"] += 1
        if row["country"] == "India":
            segment_counts["india"] += 1
        if row["open_to_work"]:
            segment_counts["open_to_work"] += 1
        if 5.0 <= float(row["years"]) <= 9.0:
            segment_counts["experience_5_to_9"] += 1
        if row["risk"] > 0:
            segment_counts["risk_flagged"] += 1
    return {
        "submission_rows": len(rows),
        "segments": dict(segment_counts),
        "top_titles": title_counts.most_common(top_n),
        "top_industries": industry_counts.most_common(top_n),
        "countries": country_counts.most_common(top_n),
        "top_rows": rows[:top_n],
        "risk_rows": [row for row in rows if row["risk"] > 0],
    }


def write_submission_audit(audit: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "submission_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    (out_dir / "submission_audit.md").write_text(render_submission_audit(audit), encoding="utf-8")
    _write_rows(out_dir / "submission_top_rows.csv", audit["top_rows"])
    _write_rows(out_dir / "submission_risk_rows.csv", audit["risk_rows"])


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def render_markdown_report(profile: dict[str, Any]) -> str:
    lines = [
        "# Phase 2 Dataset Intelligence Report",
        "",
        "This report is generated by streaming the released candidate JSONL once. It is for analysis and strategy; it does not change the official ranking command.",
        "",
        "## Headline Counts",
        "",
        f"- Total candidates: {profile['total_candidates']}",
    ]
    for key, value in sorted(profile["segments"].items()):
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Numeric Signal Summary", ""])
    for name, stats in profile["numeric_summary"].items():
        lines.append(
            f"- {name}: mean {stats['mean']}, median {stats['median']}, p10 {stats['p10']}, p90 {stats['p90']}, min {stats['min']}, max {stats['max']}"
        )

    _add_counter_section(lines, "Top Titles", profile["top_titles"])
    _add_counter_section(lines, "Top Industries", profile["top_industries"])
    _add_counter_section(lines, "Countries", profile["countries"])
    _add_counter_section(lines, "Top Locations", profile["top_locations"])
    _add_counter_section(lines, "Top Skills", profile["top_skills"])
    _add_counter_section(lines, "JD Term Coverage", profile["jd_term_coverage"])
    _add_counter_section(lines, "Risk Reasons", profile["risk_reasons"])

    lines.extend(
        [
            "",
            "## Phase 2 Takeaways",
            "",
            "- The target role is rare relative to the full dataset, so top-10 precision matters more than broad recall.",
            "- Non-fit titles and services-heavy profiles are common; they must not outrank real AI/search/recommendation engineers.",
            "- Redrob behavior signals should act as a hireability modifier, especially recency, response rate, open-to-work, and notice period.",
            "- Risk flags are not automatic rejections, but top-ranked candidates with risk flags deserve manual review before final submission.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_submission_audit(audit: dict[str, Any]) -> str:
    lines = [
        "# Submission Quality Audit",
        "",
        "This audit summarizes the currently generated top-100 CSV against the JD-oriented segments used in analysis.",
        "",
        "## Headline Counts",
        "",
        f"- Submission rows audited: {audit['submission_rows']}",
    ]
    for key, value in sorted(audit["segments"].items()):
        lines.append(f"- {key}: {value}")
    _add_counter_section(lines, "Top Titles In Submission", audit["top_titles"])
    _add_counter_section(lines, "Top Industries In Submission", audit["top_industries"])
    _add_counter_section(lines, "Countries In Submission", audit["countries"])
    lines.extend(["", "## Top Rows Preview", ""])
    for row in audit["top_rows"][:10]:
        lines.append(
            f"- #{row['rank']} {row['candidate_id']}: {row['title']}, {row['years']} yrs, {row['industry']}, {row['location']}, risk {row['risk']}"
        )
    lines.extend(
        [
            "",
            "## Audit Takeaways",
            "",
            "- The top rows should be dominated by AI/search/recommendation/NLP/data-science titles.",
            "- Any non-fit or risk-flagged top rows should be manually inspected before final submission.",
            "- Use this audit after every scoring change to catch quality regressions quickly.",
        ]
    )
    return "\n".join(lines) + "\n"


def _add_counter_section(lines: list[str], title: str, rows: list[list[Any] | tuple[Any, Any]]) -> None:
    lines.extend(["", f"## {title}", ""])
    if not rows:
        lines.append("- none")
        return
    for label, count in rows:
        lines.append(f"- {label}: {count}")
