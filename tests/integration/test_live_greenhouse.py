"""Live Greenhouse discovery → normalize → deterministic score.

Requires network access. Skips cleanly if the API is unreachable.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import httpx
import pytest

from src.candidate.schemas import CandidateProfile
from src.jobs.matcher.deterministic import score
from src.jobs.models import Job
from src.jobs.normalizer.normalizer import normalize

_PROFILE = CandidateProfile(
    full_name="Okeson",
    email="okeson@example.com",
    location="Nigeria",
    skills=["TypeScript", "Python", "PostgreSQL", "Node.js", "System Design"],
    technologies=["TypeScript", "Python", "PostgreSQL", "Node.js", "Redis"],
    preferred_roles=["Backend Engineer", "Software Engineer", "Platform Engineer"],
    remote_ok=True,
    nigeria_eligible=True,
)


def _to_job(job_create: object) -> Job:
    return Job(
        id=uuid.uuid4(),
        source=job_create.source,  # type: ignore[attr-defined]
        external_id=job_create.external_id,  # type: ignore[attr-defined]
        title=job_create.title,  # type: ignore[attr-defined]
        company=job_create.company,  # type: ignore[attr-defined]
        description=job_create.description,  # type: ignore[attr-defined]
        location=job_create.location,  # type: ignore[attr-defined]
        remote=job_create.remote,  # type: ignore[attr-defined]
        countries=job_create.countries,  # type: ignore[attr-defined]
        technologies=job_create.technologies,  # type: ignore[attr-defined]
        seniority=job_create.seniority,  # type: ignore[attr-defined]
        application_url=job_create.application_url,  # type: ignore[attr-defined]
        state="DISCOVERED",
        discovered_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture(scope="module")
def live_jobs() -> list[Job]:
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(
                "https://boards-api.greenhouse.io/v1/boards/discord/jobs",
                params={"content": "true"},
            )
            if resp.status_code != 200:
                pytest.skip(f"Greenhouse API returned {resp.status_code}")
            raw_jobs = resp.json().get("jobs") or []
    except httpx.HTTPError as exc:
        pytest.skip(f"Greenhouse unreachable: {exc}")

    result: list[Job] = []
    for raw in raw_jobs[:25]:
        if not raw.get("company_name"):
            raw["company_name"] = "Discord"
        try:
            created = normalize("greenhouse", raw)
            result.append(_to_job(created))
        except Exception:
            continue
    if len(result) < 5:
        pytest.skip("Fewer than 5 jobs normalized from live feed")
    return result


class TestLiveGreenhouse:
    def test_normalize_produces_required_fields(self, live_jobs: list[Job]) -> None:
        for job in live_jobs:
            assert job.external_id
            assert job.title
            assert job.company
            assert job.application_url.startswith("http")

    def test_scores_in_documented_range(self, live_jobs: list[Job]) -> None:
        scores = [score(j, _PROFILE) for j in live_jobs]
        assert all(0 <= s <= 100 for s in scores)
        # At least one job should score above the default threshold on a
        # software-heavy board like Discord.
        assert max(scores) >= 40

    def test_at_least_ten_scored(self, live_jobs: list[Job]) -> None:
        assert len(live_jobs) >= 10
