"""Turing — public remote role board (browser-rendered).

The listing shows 12 cards initially and grows via a "Load more roles"
button. Detail pages require an authenticated session, which this system
never creates, so only publicly visible card data is collected.
"""

from __future__ import annotations

import os
from typing import Any

from src.discovery.base import JobSource
from src.discovery.browser_fetch import render_with_clicks
from src.discovery.turing.parser import parse as parse_turing
from src.discovery.turing.parser import parse_listing_html
from src.jobs.normalizer.normalizer import register_parser
from src.observability.logging import get_logger

logger = get_logger(__name__)
register_parser("turing", parse_turing)

_LIST_URL = "https://work.turing.com/jobs"


def _int_env(name: str, default: int) -> int:
    try:
        return max(0, int(os.environ.get(name, default)))
    except ValueError:
        return default


class TuringAdapter(JobSource):
    source_name = "turing"
    default_poll_interval_minutes = 60
    rate_limit_per_minute = 6

    async def discover(self) -> list[dict[str, Any]]:
        try:
            await self._acquire_rate_limit()
        except RuntimeError:
            return []

        html = await render_with_clicks(
            _LIST_URL,
            card_selector="article[data-job-card-id]",
            click_text="Load more roles",
            max_clicks=_int_env("DISCOVERY_TURING_LOAD_MORE_CLICKS", 3),
            wait_selector="article[data-job-card-id]",
            settle_ms=2000,
        )
        if not html:
            logger.info("turing.discover.empty")
            return []

        results = parse_listing_html(html)
        logger.info("turing.discover.ok", count=len(results))
        return results
