"""Eligibility check tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from src.applications.eligibility import check_eligibility
from src.candidate.schemas import CandidateProfile
from src.jobs.models import Job


def _job(**kwargs: object) -> Job:
    defaults = dict(
        id=uuid.uuid4(),
        source="greenhouse",
        external_id="1",
        title="Backend Engineer",
        company="Acme",
        description="x",
        application_url="https://example.com",
        remote=True,
        location="Remote",
        countries=["Nigeria"],
        state="DISCOVERED",
        discovered_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return Job(**defaults)  # type: ignore[arg-type]


def _profile() -> CandidateProfile:
    return CandidateProfile(
        remote_ok=True,
        nigeria_eligible=True,
        full_name="Okeson",
    )


class TestEligibility:
    def test_remote_ok(self) -> None:
        ok, reason = check_eligibility(_job(), _profile())
        assert ok is True
        assert reason == ""

    def test_excluded_company(self) -> None:
        ok, reason = check_eligibility(
            _job(company="EvilCorp"), _profile(), excluded_companies=["EvilCorp"]
        )
        assert ok is False
        assert "excluded_company" in reason

    def test_onsite_outside_nigeria(self) -> None:
        ok, reason = check_eligibility(
            _job(remote=False, location="London", countries=["UK"]),
            _profile(),
        )
        assert ok is False
