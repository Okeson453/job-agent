"""Extract factual claims about the candidate from generated text.

Rule-based sentence splitting first; a lightweight structure for tagging
each claim with the project or fact it references when identifiable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Claim:
    """A single factual assertion extracted from generated application text."""

    text: str
    claimed_level: str | None = None
    project_ref: str | None = None
    technologies: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


# Patterns that imply a stronger evidence level than design/research.
_IMPLEMENTED_MARKERS = re.compile(
    r"\b(built|deployed|shipped|operated|ran in production|production system|"
    r"launched|released|maintained in prod|on-call|scaled to)\b",
    re.IGNORECASE,
)
_DESIGNED_MARKERS = re.compile(
    r"\b(designed|architected|specified|drafted|proposed|modelled|modeled)\b",
    re.IGNORECASE,
)
_RESEARCH_MARKERS = re.compile(
    r"\b(researched|studied|investigated|explored|analysed|analyzed)\b",
    re.IGNORECASE,
)

def _project_name_pattern() -> re.Pattern[str]:
    names = ["TestingEngine", "CrashWave", "OrionSentinel", "AegisShare"]
    try:
        from pathlib import Path

        root = Path(__file__).resolve().parents[3] / "candidate" / "projects"
        if root.is_dir():
            loaded = sorted(
                d.name
                for d in root.iterdir()
                if d.is_dir() and not d.name.startswith(".") and d.name != "other"
            )
            if loaded:
                names = loaded
        # Also include nested product names under AegisOS etc.
        nested: list[str] = []
        for d in root.iterdir() if root.is_dir() else []:
            if not d.is_dir():
                continue
            for child in d.iterdir():
                if child.is_dir() and not child.name.startswith(".") and child.name not in (
                    "evidence",
                ):
                    nested.append(child.name)
        if nested:
            names = list(dict.fromkeys(names + nested))
    except Exception:
        pass
    joined = "|".join(re.escape(n) for n in names)
    return re.compile(rf"\b({joined})\b", re.IGNORECASE)


_PROJECT_NAMES = _project_name_pattern()

_TECH_TERMS = re.compile(
    r"\b(TypeScript|JavaScript|Python|PostgreSQL|Redis|Node\.?js|WebSockets?|"
    r"FastAPI|SQLAlchemy|Playwright|AWS|Docker|Kubernetes|GraphQL|gRPC)\b",
    re.IGNORECASE,
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _infer_claimed_level(sentence: str) -> str | None:
    if _IMPLEMENTED_MARKERS.search(sentence):
        return "implemented"
    if _DESIGNED_MARKERS.search(sentence):
        return "designed"
    if _RESEARCH_MARKERS.search(sentence):
        return "research"
    return None


def _extract_project(sentence: str) -> str | None:
    m = _PROJECT_NAMES.search(sentence)
    return m.group(1) if m else None


def _extract_technologies(sentence: str) -> list[str]:
    return list({m.group(0) for m in _TECH_TERMS.finditer(sentence)})


def extract_claims(generated_text: str) -> list[Claim]:
    """Pull factual claims out of LLM-generated application text.

    Only sentences that make a first-person or candidate-experience assertion
    are retained. Purely company-facing sentences are skipped.
    """
    if not generated_text or not generated_text.strip():
        return []

    sentences = _SENTENCE_SPLIT.split(generated_text.strip())
    claims: list[Claim] = []

    for raw in sentences:
        sentence = raw.strip()
        if len(sentence) < 8:
            continue
        # Skip sentences that are clearly about the company, not the candidate.
        lower = sentence.lower()
        if lower.startswith(("the company", "your team", "this role", "the position")):
            continue

        claimed = _infer_claimed_level(sentence)
        project = _extract_project(sentence)
        techs = _extract_technologies(sentence)

        # Keep sentences that look like experience claims even without a marker.
        is_experience = any(
            phrase in lower
            for phrase in (
                "i designed",
                "i built",
                "i implemented",
                "i developed",
                "i architected",
                "i worked",
                "my experience",
                "i have",
                "experience with",
                "experience designing",
                "experience building",
                "years of experience",
                "years experience",
                "responsible for",
                "led ",
                "owned ",
                "contributed",
                "deployed",
                "graduated",
                "certified",
                "degree in",
                "based in",
                "authorized to",
                "work authorization",
                "notice period",
                "currently studying",
                "accounting student",
            )
        )
        if claimed is None and not is_experience and not project:
            continue

        claims.append(
            Claim(
                text=sentence,
                claimed_level=claimed,
                project_ref=project,
                technologies=techs,
                keywords=_keywords(sentence),
            )
        )

    return claims


def _keywords(sentence: str) -> list[str]:
    words = re.findall(r"[a-zA-Z]{4,}", sentence.lower())
    stop = {
        "that",
        "this",
        "with",
        "from",
        "have",
        "been",
        "were",
        "which",
        "their",
        "about",
        "would",
        "could",
        "should",
        "into",
        "over",
        "under",
        "also",
        "than",
        "then",
        "when",
        "where",
        "what",
        "your",
        "role",
        "team",
        "work",
        "using",
        "based",
    }
    return [w for w in words if w not in stop][:12]
