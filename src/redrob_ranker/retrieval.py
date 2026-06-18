"""Phase 4 multi-retriever candidate generation.

The final ranker still scores the full dataset for reproducibility, but these
retriever signals explain *why* a candidate entered the high-quality pool and
provide a small ranking lift when multiple independent JD-aligned paths agree.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .config import (
    ADJACENT_TITLE_PATTERNS,
    GOOD_CITIES,
    GOOD_INDUSTRIES,
    MUST_HAVE_TERMS,
    SERVICE_INDUSTRIES,
    STRONG_TITLE_PATTERNS,
    TARGET_CITIES,
)
from .features import candidate_text, clamp, honeypot_risk, skill_score
from .io import iter_candidates


CORE_RETRIEVAL_TERMS = {
    "retrieval",
    "embedding",
    "embeddings",
    "vector search",
    "semantic search",
    "hybrid search",
    "ranking",
    "recommendation",
    "recommender",
    "matching",
    "bm25",
    "faiss",
    "qdrant",
    "weaviate",
    "pinecone",
    "milvus",
    "opensearch",
    "elasticsearch",
}

EVALUATION_TERMS = {"ndcg", "mrr", "map", "a/b", "ab test", "offline evaluation", "online evaluation", "benchmark"}
PRODUCTION_TERMS = {"production", "deployed", "real users", "shipped", "ship", "scale", "latency", "index refresh"}


def retrieval_signals(candidate: dict[str, Any], text: str | None = None) -> dict[str, Any]:
    """Return retriever source hits and a compact agreement score."""

    profile = candidate["profile"]
    signals = candidate["redrob_signals"]
    jobs = candidate.get("career_history", [])
    text = text if text is not None else candidate_text(candidate)
    titles = [profile.get("current_title", "")] + [job.get("title", "") for job in jobs]
    skill_value, matched_skills = skill_score(candidate)
    risk, risk_reasons = honeypot_risk(candidate)

    sources: list[str] = []
    details: dict[str, Any] = {}

    if any(pattern.search(title) for pattern in STRONG_TITLE_PATTERNS for title in titles):
        sources.append("title_strong_ai_search")
    elif any(pattern.search(title) for pattern in ADJACENT_TITLE_PATTERNS for title in titles):
        sources.append("title_adjacent_engineering")

    core_hits = sorted(term for term in CORE_RETRIEVAL_TERMS if term in text)
    eval_hits = sorted(term for term in EVALUATION_TERMS if term in text)
    production_hits = sorted(term for term in PRODUCTION_TERMS if term in text)
    rubric_hits = sorted(term for term in MUST_HAVE_TERMS if term in text)
    details["core_hits"] = core_hits[:8]
    details["evaluation_hits"] = eval_hits[:6]
    details["production_hits"] = production_hits[:6]
    details["rubric_hit_count"] = len(rubric_hits)

    if len(core_hits) >= 2:
        sources.append("career_core_retrieval")
    if eval_hits:
        sources.append("ranking_evaluation")
    if production_hits and core_hits:
        sources.append("production_system_evidence")
    if skill_value >= 0.42 and len(matched_skills) >= 3:
        sources.append("trusted_skill_cluster")
    if profile.get("current_industry") in GOOD_INDUSTRIES or any(job.get("industry") in GOOD_INDUSTRIES for job in jobs):
        sources.append("product_company_context")

    city = profile.get("location", "").split(",")[0].strip()
    if profile.get("country") == "India" and (city in TARGET_CITIES or city in GOOD_CITIES or signals.get("willing_to_relocate")):
        sources.append("location_viable")
    if (
        signals.get("open_to_work_flag")
        and signals.get("recruiter_response_rate", 0.0) >= 0.45
        and signals.get("notice_period_days", 180) <= 60
    ):
        sources.append("hireability_viable")
    if risk > 0:
        sources.append("trap_risk_flag")
        details["risk_reasons"] = risk_reasons
    if jobs and all(job.get("industry") in SERVICE_INDUSTRIES for job in jobs):
        sources.append("pure_services_caution")

    positive_sources = [source for source in sources if source not in {"trap_risk_flag", "pure_services_caution"}]
    source_score = clamp(len(set(positive_sources)) / 7.0)
    caution_penalty = 0.12 * int("trap_risk_flag" in sources) + 0.05 * int("pure_services_caution" in sources)
    agreement_score = clamp(source_score - caution_penalty)

    return {
        "sources": sorted(set(sources)),
        "positive_sources": sorted(set(positive_sources)),
        "agreement_score": agreement_score,
        "matched_skills": matched_skills,
        "details": details,
    }


def build_retrieval_pool(candidates_path: Path, top_n: int = 500) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    source_counts: Counter[str] = Counter()
    for candidate in iter_candidates(candidates_path):
        signals = retrieval_signals(candidate)
        for source in signals["sources"]:
            source_counts[source] += 1
        if signals["agreement_score"] <= 0:
            continue
        profile = candidate["profile"]
        row = {
            "candidate_id": candidate["candidate_id"],
            "agreement_score": round(signals["agreement_score"], 4),
            "source_count": len(signals["positive_sources"]),
            "sources": "|".join(signals["sources"]),
            "title": profile.get("current_title", ""),
            "industry": profile.get("current_industry", ""),
            "location": profile.get("location", ""),
            "country": profile.get("country", ""),
            "years": profile.get("years_of_experience", 0.0),
            "core_hits": "|".join(signals["details"].get("core_hits", [])),
            "evaluation_hits": "|".join(signals["details"].get("evaluation_hits", [])),
            "production_hits": "|".join(signals["details"].get("production_hits", [])),
            "matched_skills": "|".join(signals["matched_skills"][:5]),
        }
        rows.append(row)
    rows.sort(key=lambda row: (-row["agreement_score"], -row["source_count"], row["candidate_id"]))
    return {
        "total_pool_candidates": len(rows),
        "source_counts": source_counts.most_common(),
        "top_pool": rows[:top_n],
    }


def write_retrieval_outputs(pool: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "retrieval_pool_summary.json").write_text(json.dumps(pool, indent=2), encoding="utf-8")
    (out_dir / "retrieval_pool_summary.md").write_text(render_retrieval_report(pool), encoding="utf-8")
    _write_rows(out_dir / "retrieval_pool_top.csv", pool["top_pool"])


def render_retrieval_report(pool: dict[str, Any]) -> str:
    lines = [
        "# Phase 4 Multi-Retriever Report",
        "",
        "This report shows independent retrieval paths used to identify high-quality candidate pools before final ranking.",
        "",
        f"- Pool candidates with positive agreement: {pool['total_pool_candidates']}",
        "",
        "## Retriever Source Counts",
        "",
    ]
    for source, count in pool["source_counts"]:
        lines.append(f"- {source}: {count}")
    lines.extend(["", "## Top Pool Preview", ""])
    for row in pool["top_pool"][:20]:
        lines.append(
            f"- {row['candidate_id']}: {row['title']}, {row['years']} yrs, {row['industry']}, agreement {row['agreement_score']}, sources {row['sources']}"
        )
    lines.extend(
        [
            "",
            "## How Phase 4 Helps",
            "",
            "- Multiple independent source hits reduce reliance on one brittle keyword path.",
            "- Plain career evidence, trusted skills, product context, logistics, and hireability can all support a candidate.",
            "- Trap and pure-services caution sources are visible for manual review instead of hidden inside a score.",
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
