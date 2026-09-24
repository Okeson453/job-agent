"""Unit tests for job normalization and description parsing."""

from __future__ import annotations

import pytest

from src.jobs.normalizer.normalizer import normalize
from src.jobs.parser.description_parser import extract


class TestDescriptionParser:
    def test_extracts_technologies(self) -> None:
        text = (
            "We need a strong TypeScript and Node.js engineer with PostgreSQL "
            "and Redis experience. AWS knowledge is a plus."
        )
        result = extract(text)
        techs = result["technologies"]
        assert "TypeScript" in techs
        assert "Node.js" in techs
        assert "PostgreSQL" in techs
        assert "Redis" in techs
        assert "AWS" in techs

    def test_extracts_seniority(self) -> None:
        result = extract("Looking for a Senior Backend Engineer")
        assert result["seniority"] == "senior"

    def test_extracts_salary(self) -> None:
        result = extract("Compensation: $120k - $160k USD")
        salary = result["salary"]
        assert salary is not None
        assert salary.min is not None
        assert salary.max is not None
        assert salary.min >= 100000

    def test_empty_description(self) -> None:
        result = extract("")
        assert result["technologies"] == []
        assert result["seniority"] is None


class TestNormalizer:
    def test_greenhouse_shape(self) -> None:
        raw = {
            "id": 12345,
            "title": "Backend Engineer",
            "company_name": "Acme",
            "content": "TypeScript and PostgreSQL required. Remote OK.",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/12345",
            "location": {"name": "Remote"},
        }
        job = normalize("greenhouse", raw)
        assert job.source == "greenhouse"
        assert job.external_id == "12345"
        assert job.title == "Backend Engineer"
        assert job.company == "Acme"
        assert job.application_url.startswith("https://")
        assert job.remote is True
        assert "TypeScript" in (job.technologies or [])

    def test_missing_url_raises(self) -> None:
        raw = {
            "id": "1",
            "title": "Engineer",
            "company": "X",
            "description": "test",
        }
        with pytest.raises(ValueError, match="application_url"):
            normalize("greenhouse", raw)

    def test_lever_shape(self) -> None:
        raw = {
            "id": "abc-123",
            "text": "Platform Engineer",
            "company": "Widgets Inc",
            "descriptionPlain": "Python, FastAPI, PostgreSQL. Senior level.",
            "hostedUrl": "https://jobs.lever.co/widgets/abc-123",
            "categories": {"location": "Remote", "commitment": "Full-time"},
        }
        job = normalize("lever", raw)
        assert job.source == "lever"
        assert job.external_id == "abc-123"
        assert job.title == "Platform Engineer"
        assert "Python" in (job.technologies or [])
