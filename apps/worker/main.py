"""Worker process entrypoint — supervised asyncio loops with heartbeat."""

from __future__ import annotations

import asyncio
import signal
import sys
import time
from typing import Any, Callable, Coroutine

from src.observability.logging import configure_logging, get_logger
from src.observability.tracing import configure_tracing
from src.scheduler.queues import close_redis
from src.database.session import close_engine

from apps.worker.discovery_worker import run_discovery_loops
from apps.worker.matching_worker import run_matching_loop
from apps.worker.llm_worker import run_llm_loop
from apps.worker.application_worker import run_application_loop
from apps.worker.browser_worker import run_browser_loop
from apps.worker.notification_worker import run_notification_loop

logger = get_logger(__name__)

TASK_TICKS: dict[str, float] = {}
TASK_ALIVE: dict[str, bool] = {}


def mark_tick(name: str) -> None:
    TASK_TICKS[name] = time.time()
    TASK_ALIVE[name] = True


async def _supervise(
    name: str,
    factory: Callable[[], Coroutine[Any, Any, None]],
    stop_event: asyncio.Event,
) -> None:
    """Restart a worker loop after uncaught exceptions (bounded backoff)."""
    backoff = 1.0
    while not stop_event.is_set():
        TASK_ALIVE[name] = True
        try:
            await factory()
            break
        except asyncio.CancelledError:
            TASK_ALIVE[name] = False
            raise
        except Exception as exc:
            TASK_ALIVE[name] = False
            logger.error(
                "worker.task_died",
                task=name,
                error=str(exc),
                retry_in=backoff,
            )
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=backoff)
                break
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, 60.0)
        else:
            backoff = 1.0
    TASK_ALIVE[name] = False


async def _heartbeat_loop(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        alive = sum(1 for v in TASK_ALIVE.values() if v)
        logger.info(
            "worker.heartbeat",
            tasks_alive=alive,
            ticks={k: int(v) for k, v in TASK_TICKS.items()},
        )
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=3600)
            break
        except asyncio.TimeoutError:
            continue


async def _manual_review_promoter(stop_event: asyncio.Event) -> None:
    """Promote stale MANUAL_REVIEW apps caused by transient infra failures."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from src.applications.models import Application
    from src.applications.planner import state_machine as sm
    from src.database.session import get_session
    from src.scheduler.queues import BROWSER_QUEUE, push

    interval = int(__import__("os").environ.get("MANUAL_REVIEW_PROMOTE_MINUTES", "30"))
    max_age_hours = int(__import__("os").environ.get("MANUAL_REVIEW_PROMOTE_AFTER_HOURS", "2"))
    allowed_reasons = {
        "empty_cover_letter",
        "evidence_validation_failed",
        "evidence_soft_pass",
    }

    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval * 60)
            break
        except asyncio.TimeoutError:
            pass
        if stop_event.is_set():
            break
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            async with get_session() as db:
                result = await db.execute(
                    select(Application).where(Application.state == sm.MANUAL_REVIEW)
                )
                apps = list(result.scalars().all())
                for app in apps:
                    reason = (app.failure_reason or "").strip()
                    created = app.created_at
                    if created is not None and created.tzinfo is None:
                        created = created.replace(tzinfo=timezone.utc)
                    if created is not None and created > cutoff:
                        continue
                    if reason and reason not in allowed_reasons:
                        continue
                    await sm.advance(
                        app.id,
                        db,
                        to_state=sm.SUBMISSION,
                        detail="auto_promote_stale_manual_review",
                    )
                    await db.commit()
                    await push(
                        BROWSER_QUEUE,
                        {
                            "application_id": str(app.id),
                            "job_id": str(app.job_id),
                        },
                    )
                    logger.info(
                        "worker.manual_review_promoted",
                        application_id=str(app.id),
                        reason=reason or "stale",
                    )
        except Exception as exc:
            logger.warning("worker.manual_review_promoter.error", error=str(exc))


async def _dlq_watchdog(stop_event: asyncio.Event) -> None:
    """Scan DLQ keys periodically and emit structured counts."""
    from src.scheduler.queues import get_redis

    queues = (
        "discovery_queue",
        "analysis_queue",
        "llm_queue",
        "application_queue",
        "browser_queue",
        "notification_queue",
    )
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=900)
            break
        except asyncio.TimeoutError:
            pass
        if stop_event.is_set():
            break
        try:
            client = await get_redis()
            counts = {}
            for q in queues:
                n = await client.llen(f"{q}:dlq")
                if n:
                    counts[q] = n
            if counts:
                logger.warning("worker.dlq_depth", counts=counts)
            else:
                logger.info("worker.dlq_depth", counts={})
        except Exception as exc:
            logger.warning("worker.dlq_watchdog.error", error=str(exc))


async def main() -> None:
    configure_logging(json_output=True)
    configure_tracing(service_name="job-agent-worker")
    logger.info("worker.starting")

    from src.candidate.profile.service import seed_from_json
    from src.database.session import get_session

    try:
        from src.database.bootstrap import ensure_schema

        await ensure_schema()
        async with get_session() as db:
            await seed_from_json(db)
        logger.info("worker.seed_ok")
    except Exception as exc:
        logger.warning("worker.seed_failed", error=str(exc))

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("worker.shutdown_signal")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    loops: list[tuple[str, Callable[[], Coroutine[Any, Any, None]]]] = [
        ("discovery", run_discovery_loops),
        ("matching", run_matching_loop),
        ("llm", run_llm_loop),
        ("application", run_application_loop),
        ("browser", run_browser_loop),
        ("notification", run_notification_loop),
    ]

    tasks = [
        asyncio.create_task(_supervise(name, factory, stop_event), name=f"supervise:{name}")
        for name, factory in loops
    ]
    tasks.append(asyncio.create_task(_heartbeat_loop(stop_event), name="heartbeat"))
    tasks.append(asyncio.create_task(_manual_review_promoter(stop_event), name="manual_review_promoter"))
    tasks.append(asyncio.create_task(_dlq_watchdog(stop_event), name="dlq_watchdog"))

    await stop_event.wait()

    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    await close_redis()
    await close_engine()
    logger.info("worker.stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
