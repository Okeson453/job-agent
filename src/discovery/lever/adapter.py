"""Lever public postings API adapter.

Endpoint: https://api.lever.co/v0/postings/{company}?mode=json
No authentication required for public postings.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from src.discovery.http import AllowlistBlocked, allowed_get

from src.discovery.base import JobSource
from src.observability.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_COMPANIES = ["lever", "netflix", "shopify"]


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
                    resp.raise_for_status()
                    jobs = resp.json()
                    if not isinstance(jobs, list):
                        jobs = jobs.get("data") or []
                    for raw in jobs:
                        if not raw.get("company"):
                            raw["company"] = company.replace("-", " ").title()
                        # Return source-native records; normalizer calls parser.
                        if raw.get("id") and (raw.get("text") or raw.get("title")):
                            results.append(raw)
                    logger.info(
                        "lever.discover.company",
                        company=company,
                        count=len(jobs),
                    )
                except (httpx.HTTPError, ValueError, AllowlistBlocked) as exc:
                    logger.error(
                        "lever.discover.error",
                        company=company,
                        error=str(exc),
                    )
                    continue

        return results
