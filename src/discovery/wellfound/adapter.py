"""Wellfound — public remote job listings via browser (zero credentials)."""

from __future__ import annotations
from typing import Any
from urllib.parse import urljoin
from src.discovery.base import JobSource
from src.discovery.browser_fetch import extract_cards, fetch_listing_html
from src.discovery.wellfound.parser import parse
from src.jobs.normalizer.normalizer import register_parser
from src.observability.logging import get_logger

logger = get_logger(__name__)
register_parser("wellfound", parse)

_LIST_URL = "https://wellfound.com/role/l/software-engineer/remote"


class WellfoundAdapter(JobSource):
    source_name = "wellfound"
    default_poll_interval_minutes = 60
    rate_limit_per_minute = 5

    async def discover(self) -> list[dict[str, Any]]:
        try:
            await self._acquire_rate_limit()
        except RuntimeError:
            return []
        html = await fetch_listing_html(_LIST_URL, wait_selector="a[href*='/jobs/']")
        if not html:
            logger.info("wellfound.discover.empty")
            return []
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for a in extract_cards(html, "a[href*='/jobs/']"):
            href = a.attributes.get("href") or ""
            if not href or "/jobs/" not in href or href in seen:
                continue
            seen.add(href)
            url = urljoin("https://wellfound.com", href)
            title = (a.text() or "").strip() or "Wellfound Role"
            rid = href.rstrip("/").split("/")[-1]
            results.append({
                "external_id": rid or url,
                "title": title[:200],
                "company": "Wellfound Startup",
                "description": title,
                "location": "Remote",
                "remote": True,
                "application_url": url,
            })
        logger.info("wellfound.discover.ok", count=len(results))
        return results
