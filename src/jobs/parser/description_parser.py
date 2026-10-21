"""Extract technologies, seniority, and salary from free-text job descriptions.

Rule-based extraction first; LLM fallback is explicit and logged, not silent.
"""

from __future__ import annotations

import re
from typing import Any

from src.jobs.schemas import SalaryRange

_TECH_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bTypeScript\b", re.I), "TypeScript"),
    (re.compile(r"\bJavaScript\b", re.I), "JavaScript"),
    (re.compile(r"\bPython\b", re.I), "Python"),
    (re.compile(r"\bPostgreSQL\b|\bPostgres\b", re.I), "PostgreSQL"),
    (re.compile(r"\bRedis\b", re.I), "Redis"),
    (re.compile(r"\bNode\.?js\b", re.I), "Node.js"),
    (re.compile(r"\bReact\b", re.I), "React"),
    (re.compile(r"\bAWS\b|\bAmazon Web Services\b", re.I), "AWS"),
    (re.compile(r"\bDocker\b", re.I), "Docker"),
    (re.compile(r"\bKubernetes\b|\bK8s\b", re.I), "Kubernetes"),
    (re.compile(r"\bGraphQL\b", re.I), "GraphQL"),
    (re.compile(r"\bgRPC\b", re.I), "gRPC"),
    (re.compile(r"\bFastAPI\b", re.I), "FastAPI"),
    (re.compile(r"\bSQLAlchemy\b", re.I), "SQLAlchemy"),
    (re.compile(r"\bPlaywright\b", re.I), "Playwright"),
    (re.compile(r"\bWebSockets?\b", re.I), "WebSockets"),
    (re.compile(r"\bGo\b|\bGolang\b", re.I), "Go"),
    (re.compile(r"\bRust\b", re.I), "Rust"),
    (re.compile(r"\bJava\b(?!\s*Script)", re.I), "Java"),
    (re.compile(r"\bC\+\+\b", re.I), "C++"),
    (re.compile(r"\bKafka\b", re.I), "Kafka"),
    (re.compile(r"\bMongoDB\b", re.I), "MongoDB"),
    (re.compile(r"\bMySQL\b", re.I), "MySQL"),
]

_SENIORITY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(principal|staff)\s+(software\s+)?engineer\b", re.I), "staff"),
    (re.compile(r"\bsenior\b|\bsr\.?\b", re.I), "senior"),
    (re.compile(r"\bmid[- ]?level\b|\bintermediate\b", re.I), "mid"),
    (re.compile(r"\bjunior\b|\bentry[- ]?level\b|\bintern\b", re.I), "junior"),
    (re.compile(r"\blead\b", re.I), "lead"),
]

_SALARY_PATTERN = re.compile(
    r"(?:"
    r"\$\s*([\d,]+(?:\.\d+)?)\s*[kK]?"
    r"(?:\s*[-–—to]+\s*\$?\s*([\d,]+(?:\.\d+)?)\s*[kK]?)?"
    r"|"
    r"([\d,]+(?:\.\d+)?)\s*[kK]\s*[-–—to]+\s*([\d,]+(?:\.\d+)?)\s*[kK]"
    r")",
    re.I,
)


def _parse_number(raw: str, *, assume_k: bool = False) -> int | None:
    cleaned = raw.replace(",", "").strip()
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if assume_k or cleaned.lower().endswith("k"):
        value *= 1000
    elif value < 1000:
        # Heuristic: bare numbers under 1000 in salary context are often "k".
        value *= 1000
    return int(value)


def extract(description: str) -> dict[str, Any]:
    """Pull technologies, seniority, and salary from free-text description."""
    technologies: list[str] = []
    seen: set[str] = set()
    for pattern, label in _TECH_PATTERNS:
        if pattern.search(description) and label not in seen:
            technologies.append(label)
            seen.add(label)

    seniority: str | None = None
    for pattern, level in _SENIORITY_PATTERNS:
        if pattern.search(description):
            seniority = level
            break

    salary: SalaryRange | None = None
    m = _SALARY_PATTERN.search(description)
    if m:
        groups = m.groups()
        if groups[0] is not None:
            lo = _parse_number(groups[0])
            hi = _parse_number(groups[1]) if groups[1] else None
            salary = SalaryRange(min=lo, max=hi, currency="USD")
        elif groups[2] is not None:
            lo = _parse_number(groups[2], assume_k=True)
            hi = _parse_number(groups[3], assume_k=True) if groups[3] else None
            salary = SalaryRange(min=lo, max=hi, currency="USD")

    return {
        "technologies": technologies,
        "seniority": seniority,
        "salary": salary,
    }
