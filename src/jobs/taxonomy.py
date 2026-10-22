"""Job taxonomy: role category and seniority detection.

Categories let the operator restrict coverage (`JOB_CATEGORIES`). Detection is
deliberately conservative: when a title does not clearly belong to a category it
is treated as ``other_tech`` and is never dropped by the category filter.
"""

from __future__ import annotations

import re

from src.config import normalize_seniority
from src.jobs.models import Job

# Ordered: first matching category wins, so put the specific ones first.
CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ml_ai", (
        "machine learning", "ml engineer", "ai engineer", "mlops", "deep learning",
        "nlp", "computer vision", "llm", "prompt engineer", "data scientist",
        "research scientist", "applied scientist",
    )),
    ("data", (
        "data engineer", "analytics engineer", "data analyst", "business intelligence",
        "bi developer", "etl", "data platform", "data warehouse", "databricks",
    )),
    ("security", (
        "security", "appsec", "application security", "infosec", "soc analyst",
        "penetration", "pentester", "red team", "blue team", "grc", "compliance engineer",
        "threat", "cyber",
    )),
    ("devops", (
        "devops", "platform engineer", "site reliability", "sre", "infrastructure engineer",
        "build engineer", "release engineer", "cloud engineer", "kubernetes",
    )),
    ("cloud", ("cloud architect", "aws engineer", "azure engineer", "gcp engineer", "cloud consultant")),
    ("qa", (
        "qa ", "quality assurance", "test engineer", "test automation", "sdet",
        "automation engineer", "manual tester", "qa lead",
    )),
    ("mobile", ("mobile", "android", "ios ", "ios engineer", "flutter", "react native", "swift engineer")),
    ("blockchain", ("blockchain", "web3", "solidity", "smart contract", "crypto engineer", "defi")),
    ("database", ("database administrator", "dba", "database engineer", "postgresql administrator", "sql developer")),
    ("network", ("network engineer", "network administrator", "network architect", "ccna", "ccnp", "network security")),
    ("support", (
        "technical support", "it support", "helpdesk", "help desk", "support engineer",
        "customer engineer", "solutions engineer", "implementation engineer",
    )),
    ("it_admin", ("system administrator", "sysadmin", "it administrator", "it manager", "it operations")),
    ("architecture", ("solution architect", "solutions architect", "software architect", "enterprise architect", "technical architect")),
    ("frontend", (
        "frontend", "front-end", "front end", "react developer", "angular developer",
        "vue developer", "ui engineer", "web developer",
    )),
    ("backend", (
        "backend", "back-end", "back end", "api engineer", "server engineer",
        "java developer", "python developer", "node developer", "golang engineer",
        "golang developer", "rust engineer", "php developer", "ruby developer",
        ".net developer", "c# developer",
    )),
    ("fullstack", ("full stack", "fullstack", "full-stack")),
    ("software", (
        "software engineer", "software developer", "software development",
        "programmer", "developer", "engineer", "technical lead", "tech lead",
        "engineering manager", "cto", "head of engineering",
    )),
)

ALL_CATEGORIES = frozenset(name for name, _ in CATEGORY_KEYWORDS) | {
    "other_tech",
    "non_tech",
}

_NON_TECH = (
    "sales", "marketing", "account manager", "recruiter", "talent acquisition",
    "customer success", "nurse", "driver", "accountant", "finance manager",
    "copywriter", "graphic designer", "product manager", "project manager",
    "operations manager", "hr ", "human resources", "legal counsel",
)

_LEVEL_PATTERNS = (
    ("principal", re.compile(r"\bprincipal\b", re.I)),
    ("staff", re.compile(r"\b(staff|lead|head of engineering)\b", re.I)),
    ("senior", re.compile(r"\b(senior|sr\.?|iii)\b", re.I)),
    ("junior", re.compile(r"\b(junior|jr\.?|entry[- ]level|graduate|trainee)\b", re.I)),
    ("intern", re.compile(r"\b(intern|internship)\b", re.I)),
)


def classify(job: Job) -> str:
    """Return the job's category slug."""
    title = f" {(job.title or '').lower()} "
    for category, keywords in CATEGORY_KEYWORDS:
        if any(keyword in title for keyword in keywords):
            return category

    if any(keyword in title for keyword in _NON_TECH):
        return "non_tech"
    return "other_tech"


def detect_seniority(job: Job) -> str | None:
    """Detect seniority from the normalized field, then from the title."""
    level = normalize_seniority(job.seniority)
    if level:
        return level
    title = job.title or ""
    for level, pattern in _LEVEL_PATTERNS:
        if pattern.search(title):
            return level
    return None


def category_allowed(category: str, configured: tuple[str, ...]) -> bool:
    """Only reject confidently classified categories the operator excluded."""
    if not configured or "all" in configured:
        return True
    if category in {"other_tech", "non_tech"}:
        return True
    return category in configured
