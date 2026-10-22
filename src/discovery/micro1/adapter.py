"""micro1 — public opportunity page (browser-rendered, login-gated).

The visible list is served to signed-in experts; the public page renders only
navigation from most networks, and the backing API rejects anonymous calls
with 403. This adapter attempts the public page, returns nothing when it is
gated, and never authenticates. ExpertWoka surfaces many of the same micro1
roles publicly, so coverage is not lost.
"""

from __future__ import annotations

from typing import Any

from src.discovery.base import JobSource
from src.discovery.browser_fetch import fetch_listing_html
from src.discovery.micro1.parser import parse as parse_micro1
from src.discovery.micro1.parser import parse_listing_html
from src.jobs.normalizer.normalizer import register_parser
from src.observability.logging import get_logger

logger = get_logger(__name__)
register_parser("micro1", parse_micro1)

_LIST_URL = "https://www.micro1.ai/experts/opportunities"


class Micro1Adapter(JobSource):
    source_name = "micro1"
    default_poll_interval_minutes = 120
    rate_limit_per_minute = 4

    async def discover(self) -> list[dict[str, Any]]:
        try:
            await self._acquire_rate_limit()
        except RuntimeError:
            return []

        html = await fetch_listing_html(
            _LIST_URL,
            wait_selector="a[href*='/experts/opportunities/']",
            timeout_ms=30000,
        )
        if not html:
            logger.info("micro1.discover.unavailable", reason="page_blocked_or_gated")
            return []

        results = parse_listing_html(html)
        if not results:
            logger.info("micro1.discover.gated", reason="no public opportunity cards")
        else:
            logger.info("micro1.discover.ok", count=len(results))
        return results
