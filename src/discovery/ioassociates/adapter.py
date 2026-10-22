"""iO Associates — public job search listing (browser-rendered).

The site sits behind Cloudflare and renders cards client-side, so a real
browser session is required. Pagination is plain path-based:
``/search-jobs/page/{n}/``.
"""

from __future__ import annotations

import os
from typing import Any

from src.discovery.base import JobSource
from src.discovery.browser_fetch import render_pages
from src.discovery.ioassociates.parser import (
    parse as parse_ioassociates,
)
from src.discovery.ioassociates.parser import parse_detail_html, parse_listing_html
from src.jobs.normalizer.normalizer import register_parser
from src.observability.logging import get_logger

logger = get_logger(__name__)
register_parser("ioassociates", parse_ioassociates)

_BASE = "https://www.ioassociates.co.uk"


def _int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, default)))
    except ValueError:
        return default


class IOAssociatesAdapter(JobSource):
    source_name = "ioassociates"
    default_poll_interval_minutes = 60
    rate_limit_per_minute = 10

    async def discover(self) -> list[dict[str, Any]]:
        try:
            await self._acquire_rate_limit()
        except RuntimeError:
            return []

        max_pages = _int_env("DISCOVERY_IOASSOCIATES_MAX_PAGES", 4)
        urls = [
            f"{_BASE}/search-jobs/" if page == 1 else f"{_BASE}/search-jobs/page/{page}/"
            for page in range(1, max_pages + 1)
        ]
        pages = await render_pages(urls, wait_selector="main article")

        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for html in pages:
            if not html:
                continue
            for record in parse_listing_html(html):
                if record["external_id"] in seen:
                    continue
                seen.add(record["external_id"])
                results.append(record)

        logger.info("ioassociates.discover.ok", pages=len(pages), count=len(results))
        return results

    async def enrich(self, raws: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Fetch full job pages for newly discovered roles."""
        if not raws:
            return raws
        urls = [str(raw.get("application_url") or "") for raw in raws]
        pages = await render_pages(urls, wait_selector=".jd-content", settle_ms=800)

        enriched: list[dict[str, Any]] = []
        for raw, html in zip(raws, pages, strict=False):
            if html:
                details = parse_detail_html(html)
                merged = {**raw, **details}
                if details.get("location"):
                    merged["remote"] = bool(details.get("remote", raw.get("remote", False)))
                enriched.append(merged)
            else:
                enriched.append(raw)
        logger.info("ioassociates.enrich.done", requested=len(raws))
        return enriched
