"""Deterministic matching against realistic job + profile pairs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from src.candidate.schemas import CandidateProfile
from src.jobs.matcher.deterministic import score
from src.jobs.models import Job


def _job(**kwargs: object) -> Job:
    defaults: dict = {
        "id": uuid.uuid4(),
        "source": "greenhouse",
        "external_id": "x",
        "title": "Senior Backend Engineer",
        "company": "Acme",
        "description": (
            "TypeScript, Node.js, PostgreSQL, Redis. Fintech backend platform. "
            "Remote, Nigeria-friendly."
        ),
        "location": "Remote - Nigeria",
        "remote": True,
        "countries": ["Nigeria"],
        "technologies": ["TypeScript", "Node.js", "PostgreSQL", "Redis"],
        "seniority": "senior",
        "application_url": "https://example.com/job",
        "state": "DISCOVERED",
        "discovered_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    return Job(**defaults)  # type: ignore[arg-type]


def _profile() -> CandidateProfile:
    return CandidateProfile(
        full_name="Okeson",
        email="okeson@example.com",
        location="Nigeria",
        skills=["TypeScript", "Python", "PostgreSQL", "Node.js", "System Design"],
        technologies=["TypeScript", "Python", "PostgreSQL", "Node.js", "Redis"],
        preferred_roles=["Backend Engineer", "Software Engineer"],
        remote_ok=True,
        nigeria_eligible=True,
    )


class TestMatchingPipeline:
    def test_strong_fit_scores_high(self) -> None:
        s = score(_job(), _profile())
        assert s >= 60
        assert s <= 100

    def test_unrelated_role_scores_lower(self) -> None:
        strong = score(_job(), _profile())
        weak = score(
            _job(
                title="Dental Hygienist",
                description="Clinical dental care. No software.",
                technologies=["Dentistry"],
                remote=False,
                countries=["US"],
                location="New York",
                seniority="junior",
            ),
            _profile(),
        )
        assert weak < strong

    def test_ten_jobs_all_in_range(self) -> None:
        profile = _profile()
        titles = [
            "Backend Engineer",
            "Senior Software Engineer",
            "Platform Engineer",
            "Staff Engineer",
            "Junior Developer",
            "Trading Systems Engineer",
            "Security Engineer",
            "Data Engineer",
            "Frontend Engineer",
            "DevOps Engineer",
        ]
        for title in titles:
            s = score(_job(title=title), profile)
            assert 0 <= s <= 100, f"score out of range for {title}: {s}"
