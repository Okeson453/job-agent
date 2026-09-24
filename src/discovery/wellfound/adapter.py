"""Wellfound adapter — permitted public endpoints only."""

from __future__ import annotations

from typing import Any

from src.discovery.base import JobSource
from src.discovery.wellfound.parser import parse
from src.jobs.normalizer.normalizer import register_parser
from src.observability.logging import get_logger

logger = get_logger(__name__)

register_parser("wellfound", parse)


class WellfoundAdapter(JobSource):
    source_name = "wellfound"
    default_poll_interval_minutes = 60
    rate_limit_per_minute = 5

    async def discover(self) -> list[dict[str, Any]]:
        try:
            await self._acquire_rate_limit()
        except RuntimeError:
            return []
        logger.info(
            "wellfound.discover.skipped",
            reason="no stable public unauthenticated API configured for V1",
        )
        return []
