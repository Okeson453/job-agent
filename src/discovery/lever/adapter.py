"""Lever public postings API adapter.

Endpoint: https://api.lever.co/v0/postings/{company}?mode=json
No authentication required for public postings.

``company`` must be the Lever *site name* (the subdomain on jobs.lever.co),
not the legal company name. Invalid site names return HTTP 404 from Lever.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from src.discovery.base import JobSource
from src.discovery.http import AllowlistBlocked, allowed_get
from src.observability.logging import get_logger

logger = get_logger(__name__)

# Public site names known to respond on api.lever.co (verified).
# Shopify/Netflix are NOT valid Lever site names for the public postings API.
_DEFAULT_COMPANIES = ["palantir", "spotify"]


class LeverAdapter(JobSource):
    source_name = "lever"
    default_poll_interval_minutes = 30
    rate_limit_per_minute = 20

    def __init__(self, companies: list[str] | None = None) -> None:
        if companies is not None:
            self._companies = companies
        else:
            env = os.environ.get("LEVER_COMPANIES", "")
            self._companies = (
                [c.strip() for c in env.split(",") if c.strip()]
                if env
                else list(_DEFAULT_COMPANIES)
            )

    async def discover(self) -> list[dict[str, Any]]:
        await self._acquire_rate_limit()
        results: list[dict[str, Any]] = []

        timeout = httpx.Timeout(20.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            for company in self._companies:
                url = f"https://api.lever.co/v0/postings/{company}"
                try:
                    resp = await allowed_get(client, url, params={"mode": "json"})
                    if resp.status_code == 404:
                        logger.warning(
                            "lever.discover.unknown_site",
                            company=company,
                            hint="LEVER_COMPANIES must use Lever site names (jobs.lever.co/<site>)",
                        )
                        continue
                    resp.raise_for_status()
                    jobs = resp.json()
                    if not isinstance(jobs, list):
                        jobs = jobs.get("data") or []
                    for raw in jobs:
                        if not raw.get("company"):
                            raw["company"] = company.replace("-", " ").title()
                        if raw.get("id") and (raw.get("text") or raw.get("title")):
                            results.append(raw)
                    logger.info(
                        "lever.discover.company",
                        company=company,
                        count=len(jobs),
                    )
                except AllowlistBlocked as exc:
                    logger.error("lever.discover.error", company=company, error=str(exc))
                except httpx.HTTPStatusError as exc:
                    code = exc.response.status_code if exc.response is not None else None
                    if code == 404:
                        logger.warning(
                            "lever.discover.unknown_site",
                            company=company,
                            status=code,
                        )
                    else:
                        logger.error(
                            "lever.discover.error",
                            company=company,
                            status=code,
                            error=str(exc),
                        )
                except (httpx.HTTPError, ValueError) as exc:
                    logger.error(
                        "lever.discover.error",
                        company=company,
                        error=str(exc),
                    )

        return results
