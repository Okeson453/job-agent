"""Unit tests for deterministic match scoring."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from src.candidate.schemas import CandidateProfile
from src.jobs.matcher.deterministic import score
from src.jobs.models import Job


def _make_job(**kwargs: object) -> Job:
    defaults = {
        "id": uuid.uuid4(),
        "source": "greenhouse",
        "external_id": "1",
        "title": "Senior Backend Engineer",
        "company": "Acme",
        "description": "We need TypeScript, Node.js, PostgreSQL, Redis experience in a fintech environment.",
        "location": "Remote",
        "remote": True,
        "countries": ["Nigeria"],
        "technologies": ["TypeScript", "Node.js", "PostgreSQL", "Redis"],
        "seniority": "senior",
        "application_url": "https://example.com/job/1",
        "state": "DISCOVERED",
        "discovered_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    return Job(**defaults)  # type: ignore[arg-type]


class TestDeterministicScore:
    def test_high_match_remote_nigeria_stack(self, sample_candidate_profile: CandidateProfile) -> None:
        job = _make_job()
        s = score(job, sample_candidate_profile)
        assert 0 <= s <= 100
        # Remote + Nigeria + core stack + role + domain + seniority should be high.
        assert s >= 60

    def test_score_range(self, sample_candidate_profile: CandidateProfile) -> None:
        job = _make_job(remote=False, countries=[], technologies=[], description="Intern role")
        s = score(job, sample_candidate_profile)
        assert 0 <= s <= 100

    def test_no_stack_overlap_lowers_score(self, sample_candidate_profile: CandidateProfile) -> None:
        job = _make_job(
            technologies=["COBOL", "Fortran"],
            description="Legacy mainframe systems only. No modern stack.",
            title="Mainframe Operator",
        )
        s = score(job, sample_candidate_profile)
        high = score(_make_job(), sample_candidate_profile)
        assert s < high

    def test_pure_in_memory(self, sample_candidate_profile: CandidateProfile) -> None:
        """score() must not require any external I/O."""
        job = _make_job()
        # Calling twice with same inputs yields same result (deterministic).
        assert score(job, sample_candidate_profile) == score(job, sample_candidate_profile)
