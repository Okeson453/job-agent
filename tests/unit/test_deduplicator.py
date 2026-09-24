"""Unit tests for job deduplication keys and fingerprinting."""

from __future__ import annotations

from src.jobs.dedup.deduplicator import _dedup_key, _fingerprint, _normalize_text
from src.jobs.schemas import JobCreate


def test_normalize_collapses_whitespace_and_case() -> None:
    assert _normalize_text("  Foo   BAR ") == "foo bar"


def test_dedup_key_is_source_scoped() -> None:
    a = _dedup_key("greenhouse", "123")
    b = _dedup_key("lever", "123")
    assert a != b
    assert "greenhouse" in a
    assert "123" in a


def test_fingerprint_cross_source() -> None:
    job = JobCreate(
        source="greenhouse",
        external_id="1",
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        description="x",
        application_url="https://example.com/jobs/1",
        technologies=[],
    )
    fp = _fingerprint(job)
    assert "acme" in fp
    assert "backend engineer" in fp
