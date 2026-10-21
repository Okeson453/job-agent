"""Classify application questions into categories (Section 10)."""

from __future__ import annotations

import re
from enum import Enum


class QuestionCategory(str, Enum):
    PERSONAL = "PERSONAL"
    EXPERIENCE = "EXPERIENCE"
    TECHNICAL = "TECHNICAL"
    PROJECT = "PROJECT"
    EDUCATION = "EDUCATION"
    LOCATION = "LOCATION"
    WORK_AUTHORIZATION = "WORK_AUTHORIZATION"
    COMPENSATION = "COMPENSATION"
    AVAILABILITY = "AVAILABILITY"
    LEGAL = "LEGAL"
    CUSTOM = "CUSTOM"


# Categories that must never be answered by the LLM.
HARD_EXCLUDED = frozenset(
    {
        QuestionCategory.WORK_AUTHORIZATION,
        QuestionCategory.COMPENSATION,
        QuestionCategory.LEGAL,
    }
)

_PATTERNS: list[tuple[re.Pattern[str], QuestionCategory]] = [
    (
        re.compile(
            r"authori[sz]ed to work|work permit|visa|citizenship|right to work",
            re.I,
        ),
        QuestionCategory.WORK_AUTHORIZATION,
    ),
    (
        re.compile(r"salary|compensation|pay expectation|expected (pay|salary)", re.I),
        QuestionCategory.COMPENSATION,
    ),
    (
        re.compile(r"criminal|conviction|background check|legal|non-compete", re.I),
        QuestionCategory.LEGAL,
    ),
    (
        re.compile(r"notice period|start date|available to start|availability", re.I),
        QuestionCategory.AVAILABILITY,
    ),
    (
        re.compile(r"where (are|do) you (live|based)|relocat|location preference", re.I),
        QuestionCategory.LOCATION,
    ),
    (
        re.compile(r"degree|university|college|education|graduat", re.I),
        QuestionCategory.EDUCATION,
    ),
    (
        re.compile(
            r"describe (a |your )?(project|system)|challenging project|tell us about a project",
            re.I,
        ),
        QuestionCategory.PROJECT,
    ),
    (
        re.compile(
            r"technical|how would you|design a|implement|architecture|algorithm",
            re.I,
        ),
        QuestionCategory.TECHNICAL,
    ),
    (
        re.compile(
            r"experience with|years of experience|relevant experience|background in",
            re.I,
        ),
        QuestionCategory.EXPERIENCE,
    ),
    (
        re.compile(r"about yourself|who are you|personal summary|bio", re.I),
        QuestionCategory.PERSONAL,
    ),
]


def classify(question: str) -> QuestionCategory:
    """Rule-based classification. Returns CUSTOM when no pattern matches."""
    for pattern, category in _PATTERNS:
        if pattern.search(question):
            return category
    return QuestionCategory.CUSTOM
