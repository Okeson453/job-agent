"""Generic career-page adapter driven by site_configs.

Uses httpx + selectolax for static pages. No Playwright here — browser
automation is reserved for the application submission path.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import httpx
from selectolax.parser import HTMLParser

from src.discovery.base import JobSource
from src.discovery.company_career.site_configs import SITE_CONFIGS
from src.observability.logging import get_logger

logger = get_logger(__name__)


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
                try:
                    resp = await client.get(list_url)
                    if resp.status_code in (403, 429):
                        logger.warning(
                            "company_career.blocked",
                            domain=domain,
                            status=resp.status_code,
                        )
                        continue
                    resp.raise_for_status()
                    tree = HTMLParser(resp.text)
                    links = tree.css(cfg.get("job_link_selector", "a"))
                    for node in links[:50]:
                        href = node.attributes.get("href", "")
                        title = node.text(strip=True) or ""
                        if not href or not title:
                            continue
                        full_url = urljoin(list_url, href)
                        results.append(
                            {
                                "external_id": full_url,
                                "title": title,
                                "company": domain.split(".")[0].title(),
                                "description": "",
                                "location": None,
                                "remote": "remote" in title.lower(),
                                "application_url": full_url,
                            }
                        )
                    logger.info(
                        "company_career.discover",
                        domain=domain,
                        count=len(links),
                    )
                except Exception as exc:
                    logger.error(
                        "company_career.error",
                        domain=domain,
                        error=str(exc),
                    )
                    continue

        return results
