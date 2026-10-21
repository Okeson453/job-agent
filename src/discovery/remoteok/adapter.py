"""Remote OK — public JSON feed (https://remoteok.com/api). Zero credentials."""

from __future__ import annotations
from typing import Any
import httpx
from src.discovery.base import JobSource
from src.discovery.http import AllowlistBlocked, allowed_get
from src.discovery.remoteok.parser import parse
from src.jobs.normalizer.normalizer import register_parser
from src.observability.logging import get_logger

logger = get_logger(__name__)
register_parser("remoteok", parse)

class RemoteOKAdapter(JobSource):
    source_name = "remoteok"
    default_poll_interval_minutes = 30
    rate_limit_per_minute = 10

    async def discover(self) -> list[dict[str, Any]]:
        try:
            await self._acquire_rate_limit()
        except RuntimeError:
            return []
        url = "https://remoteok.com/api"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(25.0), headers={"User-Agent": "job-agent/0.1"}) as client:
                resp = await allowed_get(client, url)
                resp.raise_for_status()
                data = resp.json()
                if not isinstance(data, list):
                    return []
                results = []
                for raw in data:
                    if not isinstance(raw, dict) or not raw.get("id"):
                        continue
                    results.append(raw)
                logger.info("remoteok.discover.ok", count=len(results))
                return results
        except (httpx.HTTPError, AllowlistBlocked, ValueError) as exc:
            logger.error("remoteok.discover.error", error=str(exc))
            return []
