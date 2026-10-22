"""ExpertWoka — public AI/remote opportunity board (server-rendered).

Listings paginate by query string (``?sort=newest&page=N``) and details are
plain HTML, so no browser is needed. Detail pages sometimes link out to the
employer's own application form; that link is stored separately and never
followed automatically.
"""

from __future__ import annotations

import os
from typing import Any

from src.discovery.base import JobSource
from src.discovery.browser_fetch import fetch_static_html, polite_sleep
from src.discovery.expertwoka.parser import parse as parse_expertwoka
from src.discovery.expertwoka.parser import parse_detail_html, parse_listing_html
from src.jobs.normalizer.normalizer import register_parser
from src.observability.logging import get_logger

logger = get_logger(__name__)
register_parser("expertwoka", parse_expertwoka)

_BASE = "https://expertwoka.com/opportunities"


def _int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, default)))
    except ValueError:
        return default


class ExpertWokaAdapter(JobSource):
    source_name = "expertwoka"
    default_poll_interval_minutes = 60
    rate_limit_per_minute = 12

    async def discover(self) -> list[dict[str, Any]]:
        try:
            await self._acquire_rate_limit()
        except RuntimeError:
            return []

        max_pages = _int_env("DISCOVERY_EXPERTWOKA_MAX_PAGES", 3)
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for page in range(1, max_pages + 1):
            url = f"{_BASE}?sort=newest&page={page}"
            html = await fetch_static_html(url)
            if not html:
                logger.info("expertwoka.discover.page_unavailable", page=page)
                break
            records = parse_listing_html(html)
            if not records:
                logger.info("expertwoka.discover.no_cards", page=page)
                break
            for record in records:
                if record["external_id"] in seen:
                    continue
                seen.add(record["external_id"])
                results.append(record)
            await polite_sleep(0.5)

        logger.info("expertwoka.discover.ok", pages=max_pages, count=len(results))
        return results

    async def enrich(self, raws: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not raws:
            return raws
        enriched: list[dict[str, Any]] = []
        for raw in raws:
            url = str(raw.get("application_url") or "")
            html = await fetch_static_html(url)
            if html:
                details = parse_detail_html(html)
                enriched.append({**raw, **details})
            else:
                enriched.append(raw)
            await polite_sleep(0.4)
        logger.info("expertwoka.enrich.done", requested=len(raws))
        return enriched
