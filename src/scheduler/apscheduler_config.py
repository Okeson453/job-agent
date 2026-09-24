"""Per-source APScheduler job configuration."""

from __future__ import annotations

import os
from typing import Any, Callable, Coroutine

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.discovery.registry import get_sources
from src.observability.logging import get_logger

logger = get_logger(__name__)


def _interval_for(source_name: str) -> int:
    env_key = f"DISCOVERY_{source_name.upper()}_POLL_INTERVAL_MINUTES"
    sources = get_sources()
    adapter = sources.get(source_name)
    default = (
        adapter.default_poll_interval_minutes
        if adapter is not None
        else 30
    )
    raw = os.environ.get(env_key)
    interval_minutes = int(raw) if raw else default
    return max(interval_minutes, 1)


def build_scheduler(
    source_tick_callbacks: dict[str, Callable[[], Coroutine[Any, Any, None]]],
) -> AsyncIOScheduler:
    """Create and configure an AsyncIOScheduler with one job per source."""
    scheduler = AsyncIOScheduler(timezone="UTC")

    for source_name, callback in source_tick_callbacks.items():
        interval_minutes = _interval_for(source_name)
        scheduler.add_job(
            callback,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=f"discover_{source_name}",
            name=f"Discover {source_name}",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=120,
        )
        logger.info(
            "scheduler.job_registered",
            source=source_name,
            interval_minutes=interval_minutes,
        )

    return scheduler
