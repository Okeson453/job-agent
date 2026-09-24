"""Generic career-page adapter driven by site_configs.

Static pages via httpx + selectolax. JS-heavy pages fall back to Playwright
listing fetch. No CAPTCHA bypass.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import httpx
from selectolax.parser import HTMLParser

from src.discovery.base import JobSource
from src.discovery.browser_fetch import fetch_listing_html
from src.discovery.company_career.site_configs import SITE_CONFIGS
from src.discovery.http import AllowlistBlocked, allowed_get
from src.jobs.normalizer.normalizer import register_parser
from src.observability.logging import get_logger

logger = get_logger(__name__)


def parse(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "external_id": str(raw.get("external_id") or ""),
        "title": str(raw.get("title") or "").strip(),
        "company": str(raw.get("company") or "").strip(),
        "description": str(raw.get("description") or ""),
        "location": raw.get("location"),
        "remote": bool(raw.get("remote", False)),
        "application_url": str(raw.get("application_url") or ""),
        "employment_type": raw.get("employment_type"),
        "technologies": list(raw.get("technologies") or []),
    }


register_parser("company_career", parse)


class CompanyCareerAdapter(JobSource):
    source_name = "company_career"
    default_poll_interval_minutes = 60
    rate_limit_per_minute = 5

    async def discover(self) -> list[dict[str, Any]]:
        try:
            await self._acquire_rate_limit()
        except RuntimeError:
            return []
        results: list[dict[str, Any]] = []
        timeout = httpx.Timeout(20.0, connect=10.0)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            for domain, cfg in SITE_CONFIGS.items():
                list_url = cfg.get("list_url")
                if not list_url:
                    continue
                selector = cfg.get("job_link_selector", "a")
                try:
                    try:
                        resp = await allowed_get(client, list_url)
                        html = resp.text if resp.status_code == 200 else None
                    except AllowlistBlocked:
                        html = None
                    if not html or len(html) < 500:
                        html = await fetch_listing_html(list_url, wait_selector=selector)
                    if not html:
                        continue
                    tree = HTMLParser(html)
                    links = tree.css(selector)
                    seen: set[str] = set()
                    for node in links[:80]:
                        href = node.attributes.get("href", "") or ""
                        title = (node.text() or "").strip()
                        if not href or not title or href in seen:
                            continue
                        seen.add(href)
                        full_url = urljoin(list_url, href)
                        results.append(
                            {
                                "external_id": full_url,
                                "title": title[:200],
                                "company": domain.split(".")[0].title(),
                                "description": title,
                                "location": None,
                                "remote": "remote" in title.lower() or "remote" in full_url.lower(),
                                "application_url": full_url,
                            }
                        )
                    logger.info("company_career.discover", domain=domain, count=len(seen))
                except Exception as exc:
                    logger.error("company_career.error", domain=domain, error=str(exc))
                    continue

        return results
