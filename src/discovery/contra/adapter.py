"""Contra — independent/contract opportunities via browser."""

from __future__ import annotations
from typing import Any
from urllib.parse import urljoin
from src.discovery.base import JobSource
from src.discovery.browser_fetch import extract_cards, fetch_listing_html
from src.discovery.contra.parser import parse
from src.jobs.normalizer.normalizer import register_parser
from src.observability.logging import get_logger

logger = get_logger(__name__)
register_parser("contra", parse)

_LIST_URL = "https://contra.com/opportunities"


class ContraAdapter(JobSource):
    source_name = "contra"
    default_poll_interval_minutes = 60
    rate_limit_per_minute = 5

    async def discover(self) -> list[dict[str, Any]]:
        try:
            await self._acquire_rate_limit()
        except RuntimeError:
            return []
        html = await fetch_listing_html(_LIST_URL, wait_selector="a[href*='/']")
        if not html:
            return []
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for a in extract_cards(html, "a[href*='/opportunities/'], a[href*='/o/']"):
            href = a.attributes.get("href") or ""
            if not href or href in seen:
                continue
            seen.add(href)
            url = urljoin("https://contra.com", href)
            title = (a.text() or "").strip() or "Contra Opportunity"
            rid = href.rstrip("/").split("/")[-1]
            results.append({
                "external_id": rid or url,
                "title": title[:200],
                "company": "Contra Client",
                "description": title,
                "location": "Remote",
                "remote": True,
                "application_url": url,
                "employment_type": "contract",
            })
        logger.info("contra.discover.ok", count=len(results))
        return results
