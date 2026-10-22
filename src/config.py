"""Runtime settings for discovery, matching, and notification.

Everything the operator can tune without touching code lives here, read from
the environment at call time so tests and long-lived workers can change it.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache

# Seniority ladder, junior to most senior. Used for distance scoring.
SENIORITY_LADDER = ("intern", "junior", "mid", "senior", "staff", "principal")

# Aliases seen in job postings.
_SENIORITY_ALIASES = {
    "entry": "junior",
    "entry level": "junior",
    "entry-level": "junior",
    "graduate": "junior",
    "jr": "junior",
    "mid-level": "mid",
    "middle": "mid",
    "intermediate": "mid",
    "sr": "senior",
    "senior level": "senior",
    "lead": "staff",
    "tech lead": "staff",
    "team lead": "staff",
    "principal engineer": "principal",
    "staff engineer": "staff",
}

REMOTE_MODES = ("remote_only", "prefer", "any")


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip().lower() for part in value.split(",") if part.strip())


def _bool(name: str, default: bool) -> bool:
    raw = _env(name)
    if not raw:
        return default
    return raw.lower() not in {"0", "false", "no", "off"}


def _int(name: str, default: int) -> int:
    raw = _env(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def normalize_seniority(value: str | None) -> str | None:
    """Map a posting's seniority label onto the ladder."""
    if not value:
        return None
    text = value.lower().strip()
    if text in _SENIORITY_ALIASES:
        return _SENIORITY_ALIASES[text]
    for part in text.replace("/", ",").split(","):
        token = part.strip()
        if token in SENIORITY_LADDER:
            return token
        if token in _SENIORITY_ALIASES:
            return _SENIORITY_ALIASES[token]
    for level in reversed(SENIORITY_LADDER):
        if level in text:
            return level
    # Token-level aliases catch abbreviations with punctuation: "Sr. Engineer".
    for token in re.split(r"[^a-z]+", text):
        if token in _SENIORITY_ALIASES:
            return _SENIORITY_ALIASES[token]
    return None


def seniority_distance(level: str | None, targets: tuple[str, ...]) -> int | None:
    """Steps between a job's level and the nearest target level."""
    if level is None or not targets:
        return None
    try:
        job_index = SENIORITY_LADDER.index(level)
    except ValueError:
        return None
    distances = [
        abs(job_index - SENIORITY_LADDER.index(target))
        for target in targets
        if target in SENIORITY_LADDER
    ]
    return min(distances) if distances else None


@dataclass(frozen=True)
class Settings:
    """Operator-tunable policy. Defaults preserve the earlier behaviour."""

    # Matching
    target_seniority: tuple[str, ...]
    job_categories: tuple[str, ...]
    preferred_countries: tuple[str, ...]
    allow_worldwide_remote: bool
    remote_mode: str
    min_salary: int | None
    salary_currency: str

    # Notification
    notify_min_score: int
    notify_daily_cap: int
    notify_attachments: bool
    notify_email_drafts: bool


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    targets = _csv(_env("TARGET_SENIORITY", "mid,senior"))
    categories = _csv(_env("JOB_CATEGORIES", "all")) or ("all",)
    countries = _csv(_env("PREFERRED_COUNTRIES", "nigeria")) or ("nigeria",)
    remote_mode = _env("REMOTE_MODE", "remote_only").lower()
    if remote_mode not in REMOTE_MODES:
        remote_mode = "remote_only"

    salary_raw = _env("MIN_SALARY")
    min_salary = int(salary_raw) if salary_raw.isdigit() else None

    return Settings(
        target_seniority=tuple(t for t in targets if t in SENIORITY_LADDER) or ("mid", "senior"),
        job_categories=categories,
        preferred_countries=countries,
        allow_worldwide_remote=_bool("ALLOW_WORLDWIDE_REMOTE", True),
        remote_mode=remote_mode,
        min_salary=min_salary,
        salary_currency=_env("SALARY_CURRENCY", "USD").upper() or "USD",
        notify_min_score=_int("NOTIFY_MIN_SCORE", 0),
        notify_daily_cap=_int("NOTIFY_MAX_PER_DAY", 0),
        notify_attachments=_bool("NOTIFY_ATTACHMENTS", True),
        notify_email_drafts=_bool("NOTIFY_EMAIL_DRAFTS", True),
    )


def reset_settings_cache() -> None:
    """Clear cached settings (tests and runtime reloads)."""
    get_settings.cache_clear()
