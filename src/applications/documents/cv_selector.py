"""Deterministic CV variant selection (Section 11)."""

from __future__ import annotations

import re

from src.jobs.models import Job

# Mapping table: keyword → CV profile name.
# Multi-word phrases are checked as substrings; single tokens use word bounds
# so "api" does not match "rapid" or "therapy".
_RULES: list[tuple[list[str], str]] = [
    (["security", "appsec", "application security", "infosec"], "Security"),
    (["mql5", "trading", "metatrader", "forex", "quant"], "Trading"),
    (["backend", "node.js", "nodejs", "platform engineer"], "Backend"),
    (["full stack", "fullstack", "full-stack", "frontend", "react"], "FullStack"),
]

_DEFAULT = "General Software Engineer"

_TOKEN = re.compile(r"[a-z0-9]+(?:\.[a-z0-9]+)?")


def _matches(keyword: str, blob: str, tokens: set[str]) -> bool:
    kw = keyword.lower()
    if " " in kw or "-" in kw:
        return kw in blob
    if "." in kw:
        return kw in blob
    return kw in tokens


def select(job: Job) -> str:
    """Return the CV profile name that best matches the role."""
    techs = " ".join(job.technologies or []).lower()
    blob = f"{job.title} {job.description} {techs}".lower()
    tokens = set(_TOKEN.findall(blob))

    for keywords, profile_name in _RULES:
        for kw in keywords:
            if _matches(kw, blob, tokens):
                return profile_name

    return _DEFAULT
