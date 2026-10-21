"""YC Work at a Startup — public listings via browser (zero credentials)."""

from __future__ import annotations
from typing import Any
from urllib.parse import urljoin
from src.discovery.base import JobSource
from src.discovery.browser_fetch import extract_cards, fetch_listing_html
from src.discovery.yc.parser import parse
from src.jobs.normalizer.normalizer import register_parser
from src.observability.logging import get_logger

logger = get_logger(__name__)
register_parser("yc", parse)

_LIST_URL = "https://www.workatastartup.com/jobs"


class YCAdapter(JobSource):
    source_name = "yc"
    default_poll_interval_minutes = 60
    rate_limit_per_minute = 5

    async def discover(self) -> list[dict[str, Any]]:
        try:
            await self._acquire_rate_limit()
        except RuntimeError:
            return []
        html = await fetch_listing_html(_LIST_URL, wait_selector="a[href*='/jobs/']")
        if not html:
            return []
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for a in extract_cards(html, "a[href*='/jobs/']"):
            href = a.attributes.get("href") or ""
            if not href or href in seen:
                continue
            seen.add(href)
            url = urljoin(_LIST_URL, href)
            title = (a.text() or "").strip() or "YC Role"
            parent = a.parent
            company = "YC Startup"
            if parent is not None:
                txt = parent.text() or ""
                if " at " in txt:
                    company = txt.split(" at ")[-1].strip()[:80] or company
            rid = href.rstrip("/").split("/")[-1]
            results.append({
                "external_id": rid or url,
                "title": title[:200],
                "company": company,
                "description": title,
                "location": "Remote",
                "remote": True,
                "application_url": url,
            })
        logger.info("yc.discover.ok", count=len(results))
        return results
