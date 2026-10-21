"""Abstract base class for all job source adapters."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from src.observability.logging import get_logger
from src.scheduler.queues import get_redis

logger = get_logger(__name__)


class JobSource(ABC):
    """One adapter per job board / ATS.

    discover() returns raw, source-native records. Parsing into field names
    expected by the normalizer happens in the adjacent parser module, never
    inline here.
    """

    source_name: str
    default_poll_interval_minutes: int = 30
    rate_limit_per_minute: int = 10

    async def _acquire_rate_limit(self) -> None:
        """Redis token-bucket shared by all adapters.

        Keyed per source_name and minute window. If Redis is unavailable,
        log and proceed — better to risk a mild over-fetch than halt discovery.
        """
        try:
            client = await get_redis()
            key = f"ratelimit:{self.source_name}:{int(time.time()) // 60}"
            count = await client.incr(key)
            if count == 1:
                await client.expire(key, 70)
            if count > self.rate_limit_per_minute:
                logger.warning(
                    "discovery.rate_limit_hit",
                    source=self.source_name,
                    count=count,
                    limit=self.rate_limit_per_minute,
                )
                raise RuntimeError(
                    f"{self.source_name} rate limit exceeded for this minute"
                )
        except RuntimeError:
            raise
        except Exception as exc:
            logger.warning(
                "discovery.rate_limit_unavailable",
                source=self.source_name,
                error=str(exc),
            )

    @abstractmethod
    async def discover(self) -> list[dict[str, Any]]:
        """Fetch new postings from this source.

        Returns a list of raw dicts in the source's native shape.
        Callers must invoke ``await self._acquire_rate_limit()`` before
        outbound HTTP.
        """
        ...
