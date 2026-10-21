"""Greenhouse public job-board API adapter.

Uses the documented public endpoint:
  https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs
No authentication required for public boards. Rate limiting enforced via
a Redis token-bucket keyed by source name.
"""

from __future__ import annotations

from typing import Any

import httpx

from src.discovery.base import JobSource
from src.discovery.http import AllowlistBlocked, allowed_get
from src.observability.logging import get_logger
logger = get_logger(__name__)

# Default public boards to poll when no explicit list is configured.
_DEFAULT_BOARDS = [
    "airbnb",
    "stripe",
    "discord",
]


class GreenhouseAdapter(JobSource):
    source_name = "greenhouse"
    default_poll_interval_minutes = 30
    rate_limit_per_minute = 20

    def __init__(self, board_tokens: list[str] | None = None) -> None:
        if board_tokens is not None:
            self._boards = board_tokens
        else:
            import os

            env_boards = os.environ.get("GREENHOUSE_BOARD_TOKENS", "")
            self._boards = (
                [b.strip() for b in env_boards.split(",") if b.strip()]
                if env_boards
                else list(_DEFAULT_BOARDS)
            )


    async def discover(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        timeout = httpx.Timeout(20.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            for board in self._boards:
                try:
                    await self._acquire_rate_limit()
                except RuntimeError as exc:
                    logger.warning(
                        "greenhouse.board_skipped_rate_limit",
                        board=board,
                        error=str(exc),
                    )
                    continue
                url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
                try:
                    resp = await allowed_get(client, url, params={"content": "true"})
                    resp.raise_for_status()
                    payload = resp.json()
                    jobs = payload.get("jobs") or []
                    for raw in jobs:
                        # Inject company name from board token when missing.
                        if not raw.get("company_name") and not raw.get("company"):
                            raw["company_name"] = board.replace("-", " ").title()
                        # Return source-native records; normalizer calls parser.
                        if raw.get("id") and raw.get("title"):
                            results.append(raw)
                    logger.info(
                        "greenhouse.discover.board",
                        board=board,
                        count=len(jobs),
                    )
                except (httpx.HTTPError, ValueError, AllowlistBlocked) as exc:
                    logger.error(
                        "greenhouse.discover.error",
                        board=board,
                        error=str(exc),
                    )
                    continue

        return results
