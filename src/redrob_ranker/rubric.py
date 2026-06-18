"""Structured interpretation of the Senior AI Engineer JD.

This module is the Phase 3 rubric engine. It keeps the JD interpretation
explicit, reviewable, and reusable by scoring, profiling, documentation, and
future tuning scripts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RubricCriterion:
    name: str
    weight: float
    description: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class RedrobJDRubric:
    role: str
    company: str
    location_preference: str
    summary: str
    must_have: tuple[RubricCriterion, ...]
    nice_to_have: tuple[RubricCriterion, ...]
    negative_signals: tuple[RubricCriterion, ...]
    logistics: tuple[RubricCriterion, ...]


SENIOR_AI_ENGINEER_RUBRIC = RedrobJDRubric(
    role="Senior AI Engineer - Founding Team",
    company="Redrob AI",
    location_preference="Pune/Noida preferred; major Indian cities and relocation acceptable",
    summary=(
        "Find a senior applied AI/search engineer who has shipped production "
        "retrieval, ranking, matching, or recommendation systems, can write "
        "strong Python, understands evaluation, and is hireable now."
    ),
    must_have=(
        RubricCriterion(
            "production_retrieval_ranking",
            0.25,
            "Production experience with embeddings, retrieval, vector or hybrid search, ranking, search, or recommendation systems.",
            (
                "embedding",
                "embeddings",
                "retrieval",
                "vector search",
                "semantic search",
                "hybrid search",
                "ranking",
                "search",
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
            ),
        ),
        RubricCriterion(
            "ranking_evaluation",
            0.14,
            "Hands-on ranking evaluation literacy: NDCG, MRR, MAP, offline benchmarks, A/B tests, and feedback loops.",
            (
                "ndcg",
                "mrr",
                "map",
                "a/b",
                "ab test",
                "offline evaluation",
                "online evaluation",
                "evaluation framework",
                "benchmark",
                "feedback loop",
            ),
        ),
        RubricCriterion(
            "production_python_engineering",
            0.13,
            "Strong Python and production engineering, not only demos or research prototypes.",
            (
                "python",
                "production",
                "deployed",
                "real users",
                "ship",
                "shipped",
                "mlops",
                "api",
                "pipeline",
                "system design",
            ),
        ),
        RubricCriterion(
            "senior_applied_ml_role",
            0.18,
            "Current or recent role should be AI/ML/search/recommendation/NLP/data-science oriented.",
            (
                "ai engineer",
                "ml engineer",
                "machine learning engineer",
                "applied ml engineer",
                "applied scientist",
                "data scientist",
                "nlp engineer",
                "search engineer",
                "recommendation systems engineer",
                "ranking engineer",
            ),
        ),
    ),
    nice_to_have=(
        RubricCriterion(
            "llm_finetuning",
            0.05,
            "LLM fine-tuning or parameter-efficient adaptation is useful but not enough by itself.",
            ("fine-tun", "lora", "qlora", "peft", "transformer", "llm"),
        ),
        RubricCriterion(
            "learning_to_rank",
            0.04,
            "Learning-to-rank model experience is valuable for search and recommendation quality.",
            ("learning to rank", "ltr", "xgboost", "ranker", "neural ranking"),
        ),
        RubricCriterion(
            "marketplace_or_hrtech",
            0.03,
            "HR-tech, recruiting, marketplace, or matching-product experience helps domain transfer.",
            ("hr-tech", "recruiting", "marketplace", "matching", "talent", "candidate"),
        ),
        RubricCriterion(
            "open_source_or_external_validation",
            0.03,
            "Open-source, papers, talks, or visible technical work reduce closed-system uncertainty.",
            ("open source", "github", "paper", "talk", "conference", "oss"),
        ),
    ),
    negative_signals=(
        RubricCriterion(
            "keyword_stuffing",
            0.25,
            "AI keywords appear in skills but not in actual role or career evidence.",
            ("ai tools", "chatgpt", "curious about ai", "side project", "tutorial"),
        ),
        RubricCriterion(
            "non_fit_current_title",
            0.20,
            "Current title is unrelated to applied AI/search engineering.",
            (
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
            ),
        ),
        RubricCriterion(
            "pure_services_path",
            0.12,
            "Entire career in IT services or consulting without product-company AI evidence.",
            ("it services", "consulting", "tcs", "infosys", "wipro", "accenture", "cognizant", "capgemini"),
        ),
        RubricCriterion(
            "availability_risk",
            0.12,
            "Stale activity, low response rate, not open to work, or long notice period.",
            ("inactive", "low response", "not open", "notice"),
        ),
        RubricCriterion(
            "honeypot_risk",
            0.20,
            "Impossible or low-trust profile signals such as inflated skill durations or unsupported expert claims.",
            ("expert zero duration", "duration exceeds experience", "invalid dates"),
        ),
    ),
    logistics=(
        RubricCriterion(
            "experience_band",
            0.10,
            "Preferred experience is 5-9 years, with 6-8 years ideal.",
            ("5-9 years", "6-8 years", "senior judgment"),
        ),
        RubricCriterion(
            "location",
            0.08,
            "Pune/Noida preferred; Hyderabad, Bangalore, Mumbai, Delhi NCR and relocation are acceptable.",
            ("pune", "noida", "hyderabad", "bangalore", "mumbai", "delhi", "gurgaon", "relocate"),
        ),
        RubricCriterion(
            "redrob_activity",
            0.12,
            "Redrob signals determine whether the candidate is reachable and hireable.",
            ("last active", "open to work", "response rate", "notice period", "interview completion"),
        ),
    ),
)


def evidence_terms() -> dict[str, float]:
    terms: dict[str, float] = {}
    for group in (SENIOR_AI_ENGINEER_RUBRIC.must_have, SENIOR_AI_ENGINEER_RUBRIC.nice_to_have):
        for criterion in group:
            for term in criterion.evidence:
                terms[term] = max(terms.get(term, 0.0), criterion.weight * 12)
    # Keep core retrieval/ranking terms dominant because the JD says this is
    # the real must-have, not a generic AI role.
    boosts = {
        "retrieval": 3.2,
        "embedding": 3.0,
        "embeddings": 3.0,
        "vector search": 3.0,
        "semantic search": 3.0,
        "ranking": 2.8,
        "bm25": 2.6,
        "faiss": 2.6,
        "qdrant": 2.6,
        "weaviate": 2.6,
        "pinecone": 2.6,
        "milvus": 2.6,
        "ndcg": 2.8,
        "mrr": 2.4,
    }
    for term, weight in boosts.items():
        terms[term] = max(terms.get(term, 0.0), weight)
    return terms


def ai_skill_terms() -> set[str]:
    terms: set[str] = set()
    for criterion in SENIOR_AI_ENGINEER_RUBRIC.must_have + SENIOR_AI_ENGINEER_RUBRIC.nice_to_have:
        for term in criterion.evidence:
            if len(term.split()) <= 4:
                terms.add(term)
    terms.update(
        {
            "machine learning",
            "deep learning",
            "nlp",
            "llm",
            "rag",
            "recommendation systems",
            "recommender systems",
            "learning to rank",
            "fine-tuning llms",
            "sentence-transformers",
            "bge",
            "e5",
            "llms",
            "pytorch",
            "tensorflow",
            "mlops",
            "model evaluation",
            "a/b testing",
            "ab testing",
        }
    )
    return terms


def strong_title_patterns() -> list[re.Pattern[str]]:
    return [
        re.compile(pattern, re.I)
        for pattern in [
            r"\b(ai|ml|machine learning)\b.*engineer",
            r"\bdata scientist\b",
            r"\bapplied scientist\b",
            r"\bnlp\b.*engineer",
            r"\bsearch\b.*engineer",
            r"\brecommendation\b.*engineer",
            r"\branking\b.*engineer",
        ]
    ]


def non_fit_titles() -> set[str]:
    for criterion in SENIOR_AI_ENGINEER_RUBRIC.negative_signals:
        if criterion.name == "non_fit_current_title":
            return set(criterion.evidence)
    return set()


def render_rubric_markdown() -> str:
    rubric = SENIOR_AI_ENGINEER_RUBRIC
    lines = [
        "# Phase 3 JD Rubric",
        "",
        f"- Role: {rubric.role}",
        f"- Company: {rubric.company}",
        f"- Location: {rubric.location_preference}",
        f"- Summary: {rubric.summary}",
        "",
    ]
    for title, criteria in [
        ("Must-Have Signals", rubric.must_have),
        ("Nice-To-Have Signals", rubric.nice_to_have),
        ("Negative Signals", rubric.negative_signals),
        ("Logistics And Hireability", rubric.logistics),
    ]:
        lines.extend([f"## {title}", ""])
        for criterion in criteria:
            lines.append(f"### {criterion.name}")
            lines.append(f"- Weight: {criterion.weight}")
            lines.append(f"- Meaning: {criterion.description}")
            lines.append(f"- Evidence terms: {', '.join(criterion.evidence)}")
            lines.append("")
    lines.extend(
        [
            "## How This Rubric Should Guide Ranking",
            "",
            "- Top 10 should be dominated by production AI/search/recommendation/ranking candidates.",
            "- Skills alone should not outrank role and career evidence.",
            "- Redrob activity is a hireability modifier, not a replacement for technical fit.",
            "- Negative signals should demote keyword-stuffed and suspicious profiles even when skill lists look strong.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_rubric_report(out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_rubric_markdown(), encoding="utf-8")
