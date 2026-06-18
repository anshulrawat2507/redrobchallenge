"""JD-specific configuration for the Redrob Senior AI Engineer ranker."""

from __future__ import annotations

import re
from datetime import date

from .rubric import ai_skill_terms, evidence_terms, non_fit_titles, strong_title_patterns


TODAY = date(2026, 6, 17)
DEFAULT_LIMIT = 100
CSV_HEADER = ["candidate_id", "rank", "score", "reasoning"]

AI_SKILLS = ai_skill_terms()

MUST_HAVE_TERMS = evidence_terms()

STRONG_TITLE_PATTERNS = strong_title_patterns()

ADJACENT_TITLE_PATTERNS = [
    re.compile(pattern, re.I)
    for pattern in [
        r"\bdata engineer\b",
        r"\bsenior data engineer\b",
        r"\banalytics engineer\b",
        r"\bbackend engineer\b",
        r"\bsoftware engineer\b",
        r"\bcloud engineer\b",
        r"\bdevops engineer\b",
        r"\bfull stack\b",
    ]
]

NON_FIT_TITLES = non_fit_titles()

GOOD_INDUSTRIES = {
    "Software",
    "SaaS",
    "AI/ML",
    "Fintech",
    "E-commerce",
    "EdTech",
    "Food Delivery",
    "Gaming",
    "Transportation",
    "AdTech",
    "Internet",
    "Conversational AI",
}

SERVICE_INDUSTRIES = {"IT Services", "Consulting"}
TARGET_CITIES = {"Pune", "Noida"}
GOOD_CITIES = {"Hyderabad", "Bangalore", "Mumbai", "Delhi", "Gurgaon", "Pune", "Noida"}
