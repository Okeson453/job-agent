"""Configuration surface, taxonomy, and seniority-as-signal behaviour."""

from __future__ import annotations

import os
import uuid
from dataclasses import replace

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "t")
os.environ.setdefault("TELEGRAM_CHAT_ID", "0")
os.environ.setdefault("ENCRYPTION_KEY", "QUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUE=")

from src.candidate.schemas import CandidateProfile
from src.config import (
    get_settings,
    normalize_seniority,
    reset_settings_cache,
    seniority_distance,
)
from src.jobs.matcher.deterministic import hard_filter_reason, score
from src.jobs.models import Job
from src.jobs.taxonomy import (
    category_allowed,
    classify,
    detect_seniority,
)


def make_job(**overrides) -> Job:
    defaults = {
        "id": uuid.uuid4(),
        "source": "expertwoka",
        "external_id": str(uuid.uuid4()),
        "title": "Backend Engineer",
        "company": "Acme",
        "description": "TypeScript, Node.js, PostgreSQL, Redis, fintech platform.",
        "location": "Remote",
        "remote": True,
        "countries": ["Nigeria"],
        "technologies": ["TypeScript", "Node.js", "PostgreSQL", "Redis"],
        "seniority": None,
        "application_url": "https://example.org/1",
    }
    defaults.update(overrides)
    return Job(**defaults)


@pytest.fixture()
def profile() -> CandidateProfile:
    return CandidateProfile(
        full_name="Test Candidate",
        skills=["TypeScript", "Node.js", "PostgreSQL", "Redis"],
        technologies=["TypeScript", "Node.js", "PostgreSQL", "Redis"],
        preferred_roles=["backend", "software engineer"],
        remote_ok=True,
        nigeria_eligible=True,
    )


# --------------------------------------------------------------------------- #
# Seniority parsing
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Senior", "senior"),
        ("Sr. Engineer", "senior"),
        ("entry-level", "junior"),
        ("Mid-Senior level", "senior"),
        ("Staff Engineer", "staff"),
        ("Principal", "principal"),
        ("Lead", "staff"),
        ("Internship", "intern"),
    ],
)
def test_normalize_seniority(raw, expected):
    assert normalize_seniority(raw) == expected


def test_normalize_seniority_unknown():
    assert normalize_seniority("whatever") is None
    assert normalize_seniority(None) is None


def test_seniority_distance():
    assert seniority_distance("senior", ("mid", "senior")) == 0
    assert seniority_distance("junior", ("mid", "senior")) == 1
    assert seniority_distance("intern", ("mid", "senior")) == 2
    assert seniority_distance(None, ("mid",)) is None


def test_detect_seniority_prefers_field_then_title():
    assert detect_seniority(make_job(seniority="Senior")) == "senior"
    assert detect_seniority(make_job(title="Principal Software Engineer")) == "principal"
    assert detect_seniority(make_job(title="Backend Engineer")) is None


# --------------------------------------------------------------------------- #
# Categories
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Senior Backend Engineer", "backend"),
        ("Machine Learning Engineer", "ml_ai"),
        ("SOC Analyst", "security"),
        ("QA Automation Engineer", "qa"),
        ("DevOps Engineer", "devops"),
        ("Data Engineer", "data"),
        ("Solutions Architect", "architecture"),
        ("Sales Manager", "non_tech"),
        ("Spacecraft Welder", "other_tech"),
    ],
)
def test_classify_titles(title, expected):
    assert classify(make_job(title=title)) == expected


def test_category_filter_never_drops_unclear_titles():
    configured = ("security", "data")
    assert category_allowed("backend", configured) is False
    assert category_allowed("security", configured) is True
    assert category_allowed("other_tech", configured) is True
    assert category_allowed("backend", ("all",)) is True


# --------------------------------------------------------------------------- #
# Seniority is a score signal, never an exclusion
# --------------------------------------------------------------------------- #


def test_junior_and_principal_roles_still_score(profile):
    cfg = get_settings()
    junior = score(make_job(title="Junior Backend Engineer", seniority="junior"), profile, cfg)
    senior = score(make_job(title="Senior Backend Engineer", seniority="senior"), profile, cfg)
    principal = score(make_job(title="Principal Engineer", seniority="principal"), profile, cfg)

    assert junior > 0
    assert senior > junior
    assert principal > 0
    # Aspirational roles are ranked lower but never filtered out by title.
    assert principal >= junior - 10


def test_seniority_never_causes_hard_rejection(profile):
    for title, level in (
        ("Intern Software Engineer", "intern"),
        ("Junior Developer", "junior"),
        ("Principal Engineer", "principal"),
    ):
        assert hard_filter_reason(make_job(title=title, seniority=level)) is None


def test_seniority_weight_is_configurable(profile):
    cfg = get_settings()
    narrow = replace(cfg, target_seniority=("senior",))
    wide = replace(cfg, target_seniority=("intern", "junior", "mid", "senior", "staff", "principal"))
    job = make_job(title="Junior Backend Engineer", seniority="junior")
    assert score(job, profile, narrow) < score(job, profile, wide)


# --------------------------------------------------------------------------- #
# Remote and geography policy
# --------------------------------------------------------------------------- #


def test_remote_mode_controls_hard_filter(profile):
    onsite = make_job(title="Backend Engineer", location="Berlin, Germany", remote=False)
    cfg = get_settings()

    assert hard_filter_reason(onsite, replace(cfg, remote_mode="any")) is None
    assert hard_filter_reason(onsite, replace(cfg, remote_mode="prefer")) is None
    assert hard_filter_reason(onsite, replace(cfg, remote_mode="remote_only")) is not None


def test_category_filter_rejects_excluded_category(profile):
    cfg = replace(get_settings(), job_categories=("security",))
    reason = hard_filter_reason(make_job(title="Senior Backend Engineer"), cfg)
    assert reason == "category_not_selected:backend"


def test_geo_preference_changes_score(profile):
    cfg = get_settings()
    job = make_job(countries=["Germany"], location="Remote (Europe)")

    worldwide = replace(cfg, preferred_countries=("nigeria",), allow_worldwide_remote=True)
    restricted = replace(cfg, preferred_countries=("nigeria",), allow_worldwide_remote=False)
    assert score(job, profile, worldwide) > score(job, profile, restricted)


# --------------------------------------------------------------------------- #
# Settings parsing
# --------------------------------------------------------------------------- #


def test_settings_parse_env(monkeypatch):
    reset_settings_cache()
    monkeypatch.setenv("TARGET_SENIORITY", "junior, senior")
    monkeypatch.setenv("JOB_CATEGORIES", "backend, data")
    monkeypatch.setenv("PREFERRED_COUNTRIES", "nigeria, ghana")
    monkeypatch.setenv("REMOTE_MODE", "prefer")
    monkeypatch.setenv("NOTIFY_MAX_PER_DAY", "12")
    monkeypatch.setenv("NOTIFY_ATTACHMENTS", "0")
    monkeypatch.setenv("MIN_SALARY", "45000")
    reset_settings_cache()

    cfg = get_settings()
    assert cfg.target_seniority == ("junior", "senior")
    assert cfg.job_categories == ("backend", "data")
    assert cfg.preferred_countries == ("nigeria", "ghana")
    assert cfg.remote_mode == "prefer"
    assert cfg.notify_daily_cap == 12
    assert cfg.notify_attachments is False
    assert cfg.min_salary == 45000

    reset_settings_cache()


def test_invalid_remote_mode_falls_back(monkeypatch):
    monkeypatch.setenv("REMOTE_MODE", "teleport")
    reset_settings_cache()
    assert get_settings().remote_mode == "remote_only"
    reset_settings_cache()


def test_invalid_seniority_values_are_dropped(monkeypatch):
    monkeypatch.setenv("TARGET_SENIORITY", "wizard,senior")
    reset_settings_cache()
    assert get_settings().target_seniority == ("senior",)
    reset_settings_cache()
