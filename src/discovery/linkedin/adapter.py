"""LinkedIn Jobs — public guest search via browser (zero credentials).

If LinkedIn serves a login wall or challenge, the adapter stops and returns
empty. No CAPTCHA bypass, no session hijacking.
"""

from __future__ import annotations
import os
from typing import Any
from urllib.parse import quote_plus, urljoin
from src.discovery.base import JobSource
from src.discovery.browser_fetch import extract_cards, fetch_listing_html
from src.discovery.linkedin.parser import parse
from src.jobs.normalizer.normalizer import register_parser
from src.observability.logging import get_logger

logger = get_logger(__name__)
register_parser("linkedin", parse)


class LinkedInAdapter(JobSource):
    source_name = "linkedin"
    default_poll_interval_minutes = 120
    rate_limit_per_minute = 2

    def __init__(self) -> None:
        self._query = os.environ.get("LINKEDIN_QUERY", "software engineer remote")

    async def discover(self) -> list[dict[str, Any]]:
        try:
            await self._acquire_rate_limit()
        except RuntimeError:
            return []
        q = quote_plus(self._query)
        url = f"https://www.linkedin.com/jobs/search/?keywords={q}&location=Remote&f_WT=2"
        html = await fetch_listing_html(url, wait_selector="a.base-card__full-link, a[href*='/jobs/view/']")
        if not html:
            return []
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for sel in ("a.base-card__full-link", "a[href*='/jobs/view/']"):
            for a in extract_cards(html, sel):
                href = a.attributes.get("href") or ""
                if not href or href in seen:
                    continue
                seen.add(href)
                full = urljoin("https://www.linkedin.com", href.split("?")[0])
                title = (a.text() or "").strip() or "LinkedIn Role"
                rid = full.rstrip("/").split("/")[-1] or full
                results.append({
                    "external_id": rid,
                    "title": title[:200],
                    "company": "LinkedIn Employer",
                    "description": title,
                    "location": "Remote",
                    "remote": True,
                    "application_url": full,
                })
        logger.info("linkedin.discover.ok", count=len(results))
        return results
