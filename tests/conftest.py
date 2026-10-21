"""Shared pytest fixtures."""

from __future__ import annotations

import os

import pytest

# Ensure required secrets exist for unit tests that import security modules.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://jobagent:jobagent@localhost:5432/jobagent_test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "0")
os.environ.setdefault(
    "ENCRYPTION_KEY", "QUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUE="
)
os.environ.setdefault(
    "ALLOWED_DOMAINS",
    "boards.greenhouse.io,jobs.lever.co,www.linkedin.com,www.indeed.com",
)


@pytest.fixture
def sample_candidate_profile():
    from src.candidate.schemas import CandidateProfile

    return CandidateProfile(
        full_name="Okeson",
        email="okeson@example.com",
        location="Nigeria",
        skills=["TypeScript", "Python", "PostgreSQL", "Node.js"],
        technologies=["TypeScript", "Python", "PostgreSQL", "Node.js", "Redis"],
        preferred_roles=["Backend Engineer", "Software Engineer"],
        remote_ok=True,
        nigeria_eligible=True,
    )
