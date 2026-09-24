"""Integration test: greenhouse/lever raw shapes → normalized JobCreate.

No network or database required.
"""

from __future__ import annotations

import pytest

from src.jobs.normalizer.normalizer import normalize


class TestDiscoveryNormalize:
    def test_greenhouse_end_to_end_shape(self) -> None:
        raw = {
            "id": 98765,
            "title": "Senior Backend Engineer",
            "company_name": "Stripe",
            "content": (
                "We are hiring a Senior Backend Engineer with TypeScript, Node.js, "
                "PostgreSQL, and Redis experience. Remote positions available. "
                "Fintech domain. Compensation $150k-$200k."
            ),
            "absolute_url": "https://boards.greenhouse.io/stripe/jobs/98765",
            "location": {"name": "Remote"},
            "updated_at": "2026-01-15T00:00:00Z",
        }
        job = normalize("greenhouse", raw)
        assert job.source == "greenhouse"
        assert job.external_id == "98765"
        assert job.title == "Senior Backend Engineer"
        assert job.company == "Stripe"
        assert job.remote is True
        assert job.application_url.startswith("https://")
        assert job.technologies is not None
        assert "TypeScript" in job.technologies
        assert job.seniority == "senior"

    def test_lever_end_to_end_shape(self) -> None:
        raw = {
            "id": "abc-123",
            "text": "Platform Engineer",
            "company": "Shopify",
            "descriptionPlain": (
                "Build infrastructure with Python and PostgreSQL. "
                "Mid-level role. Remote OK."
            ),
            "hostedUrl": "https://jobs.lever.co/shopify/abc-123",
            "categories": {"location": "Remote", "commitment": "Full-time"},
            "createdAt": 1700000000000,
        }
        job = normalize("lever", raw)
        assert job.source == "lever"
        assert job.external_id == "abc-123"
        assert job.title == "Platform Engineer"
        assert job.company == "Shopify"
        assert job.remote is True
        assert "Python" in (job.technologies or [])

    def test_duplicate_external_ids_differ_by_source(self) -> None:
        raw_gh = {
            "id": "same-id",
            "title": "Engineer",
            "company_name": "A",
            "content": "TypeScript",
            "absolute_url": "https://boards.greenhouse.io/a/jobs/same-id",
            "location": {"name": "Remote"},
        }
        raw_lv = {
            "id": "same-id",
            "text": "Engineer",
            "company": "B",
            "descriptionPlain": "TypeScript",
            "hostedUrl": "https://jobs.lever.co/b/same-id",
            "categories": {"location": "Remote"},
        }
        j1 = normalize("greenhouse", raw_gh)
        j2 = normalize("lever", raw_lv)
        assert j1.external_id == j2.external_id
        assert j1.source != j2.source
