"""Grounding checks for generated CV prose.

The CV body is assembled from knowledge-base bullets, so nothing there can be
invented. The only free text is the headline and summary; this module rejects
those when they mention technologies or numbers that do not appear in the KB.
"""

from __future__ import annotations

import re

from src.documents.kb import CandidateKB

# Technologies commonly named in job ads. If a summary mentions one that the
# knowledge base does not contain, the summary is not trustworthy.
_KNOWN_TECH = {
    "aws",
    "azure",
    "gcp",
    "google cloud",
    "kubernetes",
    "docker",
    "terraform",
    "ansible",
    "jenkins",
    "github actions",
    "gitlab",
    "react",
    "next.js",
    "nextjs",
    "vue",
    "angular",
    "svelte",
    "node.js",
    "nodejs",
    "express",
    "nestjs",
    "django",
    "flask",
    "fastapi",
    "rails",
    "spring",
    "laravel",
    "php",
    "java",
    "kotlin",
    "swift",
    "go",
    "golang",
    "rust",
    "c++",
    "c#",
    ".net",
    "python",
    "typescript",
    "javascript",
    "postgresql",
    "postgres",
    "mysql",
    "mongodb",
    "redis",
    "kafka",
    "rabbitmq",
    "elasticsearch",
    "graphql",
    "grpc",
    "rest",
    "websockets",
    "linux",
    "git",
    "pytorch",
    "tensorflow",
    "scikit-learn",
    "pandas",
    "numpy",
    "spark",
    "airflow",
    "snowflake",
    "dbt",
    "tableau",
    "power bi",
    "selenium",
    "cypress",
    "playwright",
    "pytest",
    "jest",
    "vitest",
    "solidity",
    "web3",
    "ethereum",
    "solana",
    "owasp",
    "siem",
    "soc",
    "iam",
    "oauth2",
    "jwt",
    "rbac",
    "mfa",
    "ci/cd",
}

_SENIORITY = ("senior", "staff", "principal", "lead engineer", "team lead", "head of", "director", "expert")

_NUMBER = re.compile(r"\b\d+(?:[.,]\d+)?\b")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()


def unsupported_terms(text: str, kb: CandidateKB) -> list[str]:
    """Return KB-absent technologies/numbers named in ``text``."""
    source = _normalise(kb.all_source_text())
    candidate = _normalise(text)

    problems: list[str] = []

    for term in sorted(_KNOWN_TECH):
        # Word-boundary match that tolerates punctuation such as "c++" or ".net".
        pattern = rf"(?<![\w.]){re.escape(term)}(?![\w])"
        if re.search(pattern, candidate) and not re.search(pattern, source):
            problems.append(term)

    for number in _NUMBER.findall(candidate):
        if not re.search(rf"(?<!\d){re.escape(number)}(?!\d)", source):
            problems.append(number)

    for level in _SENIORITY:
        if level in candidate and level not in source:
            problems.append(f"seniority:{level}")

    return problems


def is_grounded(text: str, kb: CandidateKB) -> bool:
    if not text.strip():
        return False
    return not unsupported_terms(text, kb)


def clip_sentences(text: str, limit: int = 3) -> str:
    sentences = [s for s in _SENTENCE_SPLIT.split(text.strip()) if s.strip()]
    return " ".join(sentences[:limit]).strip()
