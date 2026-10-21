"""Unit tests for CV variant selection."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from src.applications.documents.cv_selector import select
from src.jobs.models import Job


def _job(title: str, description: str = "", technologies: list[str] | None = None) -> Job:
    return Job(
        id=uuid.uuid4(),
        source="greenhouse",
        external_id="1",
        title=title,
        company="TestCo",
        description=description,
        application_url="https://example.com/job",
        remote=True,
        technologies=technologies,
        state="DISCOVERED",
        discovered_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestCVSelector:
    def test_backend_role(self) -> None:
        assert select(_job("Senior Backend Engineer", "Node.js APIs")) == "Backend"

    def test_security_role(self) -> None:
        assert select(_job("Application Security Engineer")) == "Security"

    def test_trading_role(self) -> None:
        assert select(_job("MQL5 Developer", "trading systems")) == "Trading"

    def test_fullstack_role(self) -> None:
        assert select(_job("Full Stack Engineer", "React and Node")) == "FullStack"

    def test_default(self) -> None:
        assert select(_job("Office Manager")) == "General Software Engineer"

    def test_api_substring_does_not_false_positive(self) -> None:
        assert select(_job("Rapid Application Development Lead")) == "General Software Engineer"
