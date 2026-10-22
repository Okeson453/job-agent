"""Primary discovery sources: ioassociates, Turing, ExpertWoka, micro1.

Parsers are exercised against HTML captured from the live public pages so
selector drift shows up as a test failure rather than an empty discovery run.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "t")
os.environ.setdefault("TELEGRAM_CHAT_ID", "0")
os.environ.setdefault("ENCRYPTION_KEY", "QUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUE=")

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "discovery"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class TestHTMLParserBackend:
    def test_lexbor_parser_import_works(self) -> None:
        from src.discovery.html import HTMLParser

        tree = HTMLParser("<html><body><a href='/x'>Hi</a></body></html>")
        assert tree.css_first("a").attributes["href"] == "/x"

    def test_extract_cards_uses_supported_backend(self) -> None:
        from src.discovery.browser_fetch import extract_cards

        cards = extract_cards("<div><article>a</article><article>b</article></div>", "article")
        assert len(cards) == 2


class TestSalaryParsing:
    def test_annual_range_with_k(self) -> None:
        from src.discovery.salary import parse_annual_salary

        assert parse_annual_salary("£26k - 40k per year") == (26000, 40000, "GBP")

    def test_hourly_rate_is_not_annualised(self) -> None:
        from src.discovery.salary import parse_annual_salary

        assert parse_annual_salary("$45-$55 per hour") == (None, None, None)

    def test_undisclosed(self) -> None:
        from src.discovery.salary import parse_annual_salary

        assert parse_annual_salary("Upon request") == (None, None, None)
        assert parse_annual_salary(None) == (None, None, None)


class TestIOAssociates:
    def test_listing_cards(self) -> None:
        from src.discovery.ioassociates.parser import parse_listing_html

        records = parse_listing_html(fixture("ioa_listing.html"))
        assert len(records) >= 10
        for record in records:
            assert record["external_id"].isdigit()
            assert record["application_url"].startswith("https://www.ioassociates.co.uk/jobs/")
            assert record["title"]

    def test_card_fields(self) -> None:
        from src.discovery.ioassociates.parser import parse_listing_html

        records = parse_listing_html(fixture("ioa_listing.html"))
        lead = next(r for r in records if r["title"] == "Lead Recruitment Consultant")
        assert lead["location"] == "Manchester"
        assert lead["salary_min"] == 26000
        assert lead["salary_max"] == 40000
        assert lead["salary_currency"] == "GBP"

    def test_detail_page(self) -> None:
        from src.discovery.ioassociates.parser import parse_detail_html

        details = parse_detail_html(fixture("ioa_detail.html"))
        assert details["title"] == "Senior FPGA Engineer"
        assert "space technology" in details["description"]
        assert details["employment_type"] == "full_time"
        assert details["location"] == "Luxembourg"

    def test_normalizes(self) -> None:
        from src.discovery.ioassociates.parser import parse_listing_html
        from src.jobs.normalizer.normalizer import normalize

        raw = parse_listing_html(fixture("ioa_listing.html"))[0]
        job = normalize("ioassociates", raw)
        assert job.source == "ioassociates"
        assert job.external_id
        assert job.application_url.startswith("https://www.ioassociates.co.uk/jobs/")


class TestTuring:
    def test_listing_cards(self) -> None:
        from src.discovery.turing.parser import parse_listing_html

        records = parse_listing_html(fixture("turing_listing.html"))
        assert len(records) == 12
        assert all(r["external_id"].isdigit() for r in records)
        assert all("jobId=" in r["application_url"] for r in records)

    def test_card_fields(self) -> None:
        from src.discovery.turing.parser import parse_listing_html

        records = {r["title"]: r for r in parse_listing_html(fixture("turing_listing.html"))}
        role = records["Strategic Project Lead – Software Engineering"]
        assert role["company"] == "Turing"
        assert "frontier AI model production" in role["description"]

    def test_normalizes(self) -> None:
        from src.discovery.turing.parser import parse_listing_html
        from src.jobs.normalizer.normalizer import normalize

        job = normalize("turing", parse_listing_html(fixture("turing_listing.html"))[0])
        assert job.company == "Turing"
        assert "jobId=" in job.application_url


class TestExpertWoka:
    def test_listing_cards(self) -> None:
        from src.discovery.expertwoka.parser import parse_listing_html

        records = parse_listing_html(fixture("woka_listing.html"))
        assert len(records) >= 10
        for record in records:
            assert record["application_url"].startswith("https://expertwoka.com/opportunities/")
            assert record["title"]

    def test_card_fields(self) -> None:
        from src.discovery.expertwoka.parser import parse_listing_html

        records = {r["title"]: r for r in parse_listing_html(fixture("woka_listing.html"))}
        role = records["Anonymization Writer"]
        assert role["company"] == "Mercor"
        assert role["location"] == "United States"
        assert role["remote"] is True
        assert role["salary_min"] is None  # hourly rate, not annualised

    def test_detail_page(self) -> None:
        from src.discovery.expertwoka.parser import parse_detail_html

        details = parse_detail_html(fixture("woka_detail.html"))
        assert details["title"] == "Anonymization Writer"
        assert "PII anonymization" in details["description"]
        assert details["remote"] is True
        assert details["location"] == "United States"
        assert "Data Labeling" in details["technologies"]
        assert details["employer_apply_url"].startswith("https://")

    def test_normalizes_with_employer_url(self) -> None:
        from src.discovery.expertwoka.parser import (
            parse_detail_html,
            parse_listing_html,
        )
        from src.jobs.normalizer.normalizer import normalize

        raw = {**parse_listing_html(fixture("woka_listing.html"))[0], **parse_detail_html(fixture("woka_detail.html"))}
        job = normalize("expertwoka", raw)
        assert job.company == "Mercor"
        assert job.employer_apply_url
        assert job.application_url.startswith("https://expertwoka.com/opportunities/")


class TestMicro1:
    def test_gated_page_yields_no_cards(self) -> None:
        from src.discovery.micro1.parser import parse_listing_html

        html = (
            "<html><body><nav>"
            "<a href='/experts/opportunities'>Opportunities</a>"
            "<a href='https://talent.micro1.ai/login'>Login</a>"
            "</nav></body></html>"
        )
        assert parse_listing_html(html) == []

    def test_real_card_shape_parses_if_present(self) -> None:
        from src.discovery.micro1.parser import parse_listing_html

        html = (
            "<main><a href='/experts/opportunities/ai-trainer-123'>AI Trainer</a></main>"
        )
        records = parse_listing_html(html)
        assert len(records) == 1
        assert records[0]["external_id"] == "ai-trainer-123"
        assert records[0]["application_url"] == "https://www.micro1.ai/experts/opportunities/ai-trainer-123"


class TestWiring:
    def test_primary_domains_allowed(self) -> None:
        from src.security.allowlist import is_allowed, reset_allowlist_cache

        reset_allowlist_cache()
        for url in (
            "https://www.ioassociates.co.uk/search-jobs/",
            "https://work.turing.com/jobs",
            "https://www.micro1.ai/experts/opportunities",
            "https://expertwoka.com/opportunities",
        ):
            assert is_allowed(url) is True, url

    def test_registry_defaults_to_primary_sources(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.discovery.registry import get_sources, reset_registry

        for key in list(os.environ):
            if key.startswith("DISCOVERY_") and key.endswith("_ENABLED"):
                monkeypatch.delenv(key, raising=False)
        reset_registry()
        try:
            names = set(get_sources())
            assert names == {"ioassociates", "expertwoka", "turing", "micro1"}
        finally:
            reset_registry()

    def test_legacy_source_is_opt_in(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.discovery.registry import get_sources, reset_registry

        for key in list(os.environ):
            if key.startswith("DISCOVERY_") and key.endswith("_ENABLED"):
                monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("DISCOVERY_GREENHOUSE_ENABLED", "1")
        reset_registry()
        try:
            assert "greenhouse" in get_sources()
        finally:
            reset_registry()
