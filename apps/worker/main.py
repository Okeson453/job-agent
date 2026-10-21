"""Worker process entrypoint — supervised asyncio loops with heartbeat."""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
import time
import traceback
from typing import Any, Callable, Coroutine

# Lightweight imports only: logging must be configured before any heavy
# module (worker loops, adapters, DB) is imported so failures are visible.
from src.observability.logging import configure_logging, get_logger
from src.observability.tracing import configure_tracing
from src.scheduler.queues import close_redis
from src.database.session import close_engine

logger = get_logger(__name__)

TASK_TICKS: dict[str, float] = {}
TASK_ALIVE: dict[str, bool] = {}


def mark_tick(name: str) -> None:
    TASK_TICKS[name] = time.time()
    TASK_ALIVE[name] = True


def _env(name: str, default: str) -> bool:
    return os.environ.get(name, default).lower() in ("1", "true", "yes", "on")


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
    """Fast first beat, then hourly. Guarantees logs are never empty."""
    first = True
    while not stop_event.is_set():
        alive = sum(1 for v in TASK_ALIVE.values() if v)
        paused = False
        try:
            from src.scheduler.queues import is_system_paused

            paused = await is_system_paused()
        except Exception:
            paused = False
        logger.info(
            "worker.heartbeat",
            tasks_alive=alive,
            system_paused=paused,
            ticks={k: int(v) for k, v in TASK_TICKS.items()},
        )
        timeout = 30 if first else 3600
        first = False
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=timeout)
            break
        except asyncio.TimeoutError:
            continue


async def _startup_diag() -> None:
    """Log environment and connectivity facts so silent stalls are diagnosable."""
    from urllib.parse import urlparse

    from src.scheduler.queues import dlq_depths, get_redis

    def _host(url: str) -> str:
        try:
            return urlparse(url).netloc or "n/a"
        except Exception:
            return "n/a"

    db_host = _host(os.environ.get("DATABASE_URL", ""))
    redis_host = _host(os.environ.get("REDIS_URL", ""))
    required = ("DATABASE_URL", "REDIS_URL", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "ENCRYPTION_KEY")
    missing = [k for k in required if not os.environ.get(k)]
    logger.info(
        "worker.diag",
        db_host=db_host or "unset",
        redis_host=redis_host or "unset",
        missing_secrets=missing,
        mode=os.environ.get("APPLICATION_MODE_DEFAULT", "APPROVAL"),
        match_threshold=os.environ.get("MATCH_THRESHOLD", "auto"),
    )

    # Redis reachability with timeout.
    try:
        client = await get_redis()
        await asyncio.wait_for(client.ping(), timeout=10)
        logger.info("worker.diag.redis_ok", host=redis_host)
    except Exception as exc:
        logger.error("worker.diag.redis_failed", host=redis_host, error=str(exc))

    try:
        depths = await asyncio.wait_for(dlq_depths(), timeout=10)
        if depths:
            logger.warning("worker.diag.dlq", depths=depths)
    except Exception:
        pass


async def _startup_recovery() -> dict[str, dict[str, int]]:
    """Resume the pipeline after a crash or dead-letter stall.

    Runs before consumer loops start:
    - reclaim in-flight messages stranded in processing lists by a crash
    - requeue dead-lettered messages (consumers are idempotent)
    """
    from src.scheduler.queues import (
        ALL_QUEUES,
        NOTIFICATION_QUEUE,
        dlq_depths,
        push,
        reclaim_processing,
        requeue_dlq,
        set_system_paused,
    )

    # A pause set without a TTL freezes everything forever; resume it so the
    # pipeline starts moving again. Re-pause explicitly if still wanted.
    if _env("RESUME_STUCK_PAUSE_ON_START", "1"):
        try:
            await set_system_paused(False)
        except Exception as exc:
            logger.warning("worker.recovery.unpause.error", error=str(exc))

    requeue_enabled = _env("DLQ_AUTO_REQUEUE", "1")

    depths = await dlq_depths()
    summary: dict[str, dict[str, int]] = {}
    for q in ALL_QUEUES:
        reclaimed = 0
        requeued = 0
        try:
            reclaimed = await reclaim_processing(q)
        except Exception as exc:
            logger.warning("worker.recovery.reclaim.error", queue=q, error=str(exc))
        if requeue_enabled and depths.get(q):
            try:
                requeued = await requeue_dlq(q)
            except Exception as exc:
                logger.warning("worker.recovery.requeue.error", queue=q, error=str(exc))
        if reclaimed or requeued:
            summary[q] = {"reclaimed_processing": reclaimed, "requeued_dlq": requeued}

    if summary:
        logger.warning("worker.recovery.requeued", queues=summary)
        try:
            await push(
                NOTIFICATION_QUEUE,
                {"type": "pipeline_recovered", "detail": json.dumps(summary)},
            )
        except Exception:
            pass
    return summary


async def _infra_keepalive_loop(stop_event: asyncio.Event) -> None:
    """Ping Redis and Postgres periodically.

    Free-tier managed instances sleep when idle; repeated connection
    attempts are what wake them up, and periodic traffic keeps them awake.
    Both backends are pinged unconditionally: Postgres must stay warm
    even while Redis is asleep, and vice versa. Connectivity state
    changes are logged so an asleep backend is visible, not silent.
    """
    from src.scheduler.queues import redis_health

    interval = int(os.environ.get("INFRA_KEEPALIVE_INTERVAL_SECONDS", "45"))
    last_redis_ok: bool | None = None
    last_pg_ok: bool | None = None
    while not stop_event.is_set():
        redis_ok = False
        try:
            redis_ok = await asyncio.wait_for(redis_health(), timeout=15)
        except Exception:
            redis_ok = False
        if redis_ok != last_redis_ok:
            if redis_ok:
                logger.info("infra.redis_awake")
            else:
                logger.error(
                    "infra.redis_unreachable",
                    hint="Redis asleep/unreachable; queues stall until it wakes",
                )
            last_redis_ok = redis_ok

        pg_ok = False
        try:
            from sqlalchemy import text

            from src.database.session import get_session

            async with get_session() as db:
                await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=10)
            pg_ok = True
        except Exception:
            pg_ok = False
        if pg_ok != last_pg_ok:
            if pg_ok:
                logger.info("infra.postgres_awake")
            else:
                logger.error("infra.postgres_unreachable")
            last_pg_ok = pg_ok

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
            break
        except asyncio.TimeoutError:
            continue


async def _dlq_requeue_loop(stop_event: asyncio.Event) -> None:
    """Periodically drain DLQs back into their queues.

    Consumers are idempotent (applications resume from their current state,
    discovery deduplicates, matching/LLM re-score harmlessly), so retries
    are safe. This keeps the pipeline moving after transient failures.
    """
    from src.scheduler.queues import dlq_depths, requeue_dlq

    interval = int(os.environ.get("DLQ_REQUEUE_INTERVAL_SECONDS", "900"))
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
            break
        except asyncio.TimeoutError:
            pass
        if stop_event.is_set() or not _env("DLQ_AUTO_REQUEUE", "1"):
            break
        try:
            depths = await dlq_depths()
            for q, depth in depths.items():
                moved = await requeue_dlq(q)
                if moved:
                    logger.warning(
                        "worker.dlq_requeued", queue=q, moved=moved, remaining=depth - moved
                    )
        except Exception as exc:
            logger.warning("worker.dlq_requeue.error", error=str(exc))


async def _manual_review_promoter(stop_event: asyncio.Event) -> None:
    """Promote stale MANUAL_REVIEW apps caused by transient infra failures."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from src.applications.models import Application
    from src.applications.planner import state_machine as sm
    from src.database.session import get_session
    from src.scheduler.queues import BROWSER_QUEUE, push

    interval = int(os.environ.get("MANUAL_REVIEW_PROMOTE_MINUTES", "30"))
    max_age_hours = int(os.environ.get("MANUAL_REVIEW_PROMOTE_AFTER_HOURS", "2"))
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
                    if not sm.can_transition(app.state, sm.SUBMISSION):
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
    from src.scheduler.queues import dlq_depths

    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=900)
            break
        except asyncio.TimeoutError:
            pass
        if stop_event.is_set():
            break
        try:
            counts = await dlq_depths()
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

    # Heavy imports happen AFTER logging is configured so that any
    # import-time failure or hang is visible in the logs.
    from apps.worker.discovery_worker import run_discovery_loops
    from apps.worker.matching_worker import run_matching_loop
    from apps.worker.llm_worker import run_llm_loop
    from apps.worker.application_worker import run_application_loop
    from apps.worker.browser_worker import run_browser_loop
    from apps.worker.notification_worker import run_notification_loop

    try:
        await asyncio.wait_for(_startup_diag(), timeout=30)
    except Exception as exc:
        logger.error("worker.diag.failed", error=str(exc))

    try:
        from src.candidate.profile.service import seed_from_json
        from src.database.session import get_session

        try:
            from src.database.bootstrap import ensure_schema

            await asyncio.wait_for(ensure_schema(), timeout=90)
            async with get_session() as db:
                await seed_from_json(db)
            logger.info("worker.seed_ok")
        except Exception as exc:
            logger.warning("worker.seed_failed", error=str(exc))
    except Exception as exc:
        logger.warning("worker.seed_import_failed", error=str(exc))

    # Resume the pipeline before consumers start: clear a stuck pause,
    # reclaim crashed in-flight messages, requeue dead letters.
    try:
        await asyncio.wait_for(_startup_recovery(), timeout=60)
    except Exception as exc:
        logger.warning("worker.startup_recovery.error", error=str(exc))

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
    tasks.append(asyncio.create_task(_dlq_requeue_loop(stop_event), name="dlq_requeue"))
    tasks.append(asyncio.create_task(_infra_keepalive_loop(stop_event), name="infra_keepalive"))

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
    except BaseException:
        # Last-resort: never die silently. Print the full traceback to
        # stdout so the deploy log shows exactly what killed the process.
        traceback.print_exc()
        sys.stdout.flush()
        raise
