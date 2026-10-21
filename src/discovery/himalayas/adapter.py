"""Himalayas — public jobs API. Zero credentials."""

from __future__ import annotations
from typing import Any
import httpx
from src.discovery.base import JobSource
from src.discovery.http import AllowlistBlocked, allowed_get
from src.discovery.himalayas.parser import parse
from src.jobs.normalizer.normalizer import register_parser
from src.observability.logging import get_logger

logger = get_logger(__name__)
register_parser("himalayas", parse)

class HimalayasAdapter(JobSource):
    source_name = "himalayas"
    default_poll_interval_minutes = 30
    rate_limit_per_minute = 10

    async def discover(self) -> list[dict[str, Any]]:
        try:
            await self._acquire_rate_limit()
        except RuntimeError:
            return []
        url = "https://himalayas.app/jobs/api"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0), headers={"User-Agent": "job-agent/0.1"}, follow_redirects=True) as client:
                resp = await allowed_get(client, url)
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, dict):
                    jobs = data.get("jobs") or data.get("data") or data.get("results") or []
                elif isinstance(data, list):
                    jobs = data
                else:
                    jobs = []
                results = [j for j in jobs if isinstance(j, dict)]
                logger.info("himalayas.discover.ok", count=len(results))
                return results
        except (httpx.HTTPError, AllowlistBlocked, ValueError) as exc:
            logger.error("himalayas.discover.error", error=str(exc))
            return []
