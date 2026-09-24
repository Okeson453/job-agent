"""LinkedIn adapter — permitted endpoints only.

LinkedIn does not offer a public unauthenticated job search API suitable
for automated polling. This adapter is a structural placeholder that
returns empty results and logs clearly when no permitted access path exists.
No credential abuse, no CAPTCHA bypass.
"""

from __future__ import annotations

from typing import Any

from src.discovery.base import JobSource
from src.discovery.linkedin.parser import parse
from src.jobs.normalizer.normalizer import register_parser
from src.observability.logging import get_logger

logger = get_logger(__name__)

register_parser("linkedin", parse)


class LinkedInAdapter(JobSource):
    source_name = "linkedin"
    default_poll_interval_minutes = 120
    rate_limit_per_minute = 2

    async def discover(self) -> list[dict[str, Any]]:
        try:
            await self._acquire_rate_limit()
        except RuntimeError:
            return []
        logger.info(
            "linkedin.discover.skipped",
            reason="no permitted unauthenticated public API; enable only with official access",
        )
        return []
