"""Discovery worker: polls sources on schedule, normalizes, dedups, enqueues."""

from __future__ import annotations

import asyncio
from typing import Any

_SOURCE_BACKOFF: dict[str, float] = {}

from src.database.session import get_session
from src.discovery.registry import get_sources
from src.jobs.dedup.deduplicator import is_duplicate, remember
from src.jobs.models import Job, JobRequirement
from src.scheduler.outbox import enqueue_outbox, publish_pending_outbox
from src.jobs.normalizer.normalizer import normalize
from src.observability.logging import get_logger
from src.observability.tracing import span
from src.scheduler.apscheduler_config import build_scheduler
from src.scheduler.queues import (
    ANALYSIS_QUEUE,
    DISCOVERY_QUEUE,
    ack,
    is_system_paused,
    nack,
    pop,
    push,
)

logger = get_logger(__name__)


def _requirements_from_job(job: Job) -> list[JobRequirement]:
    rows: list[JobRequirement] = []
    for tech in job.technologies or []:
        rows.append(
            JobRequirement(
                job_id=job.id,
                requirement_type="technology",
                value=str(tech),
                required=True,
            )
        )
    if job.seniority:
        rows.append(
            JobRequirement(
                job_id=job.id,
                requirement_type="seniority",
                value=job.seniority,
                required=False,
            )
        )
    if job.remote:
        rows.append(
            JobRequirement(
                job_id=job.id,
                requirement_type="remote",
                value="true",
                required=False,
            )
        )
    if job.location:
        rows.append(
            JobRequirement(
                job_id=job.id,
                requirement_type="location",
                value=job.location,
                required=False,
            )
        )
    if job.salary_min is not None:
        rows.append(
            JobRequirement(
                job_id=job.id,
                requirement_type="salary_min",
                value=str(job.salary_min),
                required=False,
            )
        )
    desc = (job.description or "").lower()
    if "sponsor" in desc or "visa" in desc:
        rows.append(
            JobRequirement(
                job_id=job.id,
                requirement_type="authorization",
                value="visa_mentioned",
                required=False,
            )
        )
    if "bachelor" in desc or "degree" in desc:
        rows.append(
            JobRequirement(
                job_id=job.id,
                requirement_type="education",
                value="degree_mentioned",
                required=False,
            )
        )
    return rows


async def _tick_source(source_name: str) -> None:
    """Run one discovery tick for a single source."""
    if await is_system_paused():
        logger.info("discovery.paused", source=source_name)
        return

    sources = get_sources()
    adapter = sources.get(source_name)
    if adapter is None:
        return

    # Per-source backoff after failures.
    import time
    now = time.time()
    until = _SOURCE_BACKOFF.get(source_name, 0)
    if now < until:
        logger.info("discovery.backoff", source=source_name, retry_in=int(until - now))
        return

    with span("discovery.tick", attributes={"source": source_name}):
        try:
            raw_jobs = await asyncio.wait_for(adapter.discover(), timeout=120)
            _SOURCE_BACKOFF.pop(source_name, None)
        except Exception as exc:
            # Exponential-ish backoff: 30s base, cap 15 min.
            remaining = max(0.0, until - now) if until else 0.0
            delay = min(900.0, max(30.0, remaining * 2 if remaining else 30.0))
            _SOURCE_BACKOFF[source_name] = now + delay
            logger.error(
                "discovery.tick.failed",
                source=source_name,
                error=str(exc),
                backoff_s=delay,
            )
            return

        if not raw_jobs:
            logger.info("discovery.tick.empty", source=source_name)
            return

        inserted_ids: list[str] = []
        async with get_session() as db:
            batch: list[Job] = []
            for raw in raw_jobs:
                try:
                    job_create = normalize(source_name, raw)
                except Exception as exc:
                    logger.warning(
                        "discovery.normalize.skip",
                        source=source_name,
                        error=str(exc),
                    )
                    continue

                if await is_duplicate(job_create, db):
                    continue

                row = Job(
                    source=job_create.source,
                    external_id=job_create.external_id,
                    title=job_create.title,
                    company=job_create.company,
                    description=job_create.description,
                    location=job_create.location,
                    remote=job_create.remote,
                    countries=job_create.countries,
                    employment_type=job_create.employment_type,
                    salary_min=job_create.salary_min,
                    salary_max=job_create.salary_max,
                    salary_currency=job_create.salary_currency,
                    technologies=job_create.technologies,
                    seniority=job_create.seniority,
                    application_url=job_create.application_url,
                    state="DISCOVERED",
                    closing_date=job_create.closing_date,
                )
                batch.append(row)
                await remember(job_create)

            if batch:
                db.add_all(batch)
                await db.flush()
                for row in batch:
                    for req in _requirements_from_job(row):
                        db.add(req)
                for row in batch:
                    await enqueue_outbox(
                        db, ANALYSIS_QUEUE, {"job_id": str(row.id)}
                    )
                await db.commit()
                inserted_ids = [str(row.id) for row in batch]
                async with get_session() as pub_db:
                    await publish_pending_outbox(pub_db)
                    await pub_db.commit()

        logger.info(
            "discovery.tick.complete",
            source=source_name,
            raw=len(raw_jobs),
            inserted=len(inserted_ids),
        )


async def run_discovery_loops() -> None:
    """Scheduler enqueues source ticks onto discovery_queue; this loop consumes them."""
    sources = get_sources()

    async def enqueue(n: str) -> None:
        await push(DISCOVERY_QUEUE, {"source": n})

    callbacks: dict[str, Any] = {}
    for name in sources:
        async def make_tick(n: str = name) -> None:
            await enqueue(n)

        callbacks[name] = make_tick

    scheduler = build_scheduler(callbacks)
    scheduler.start()
    logger.info("discovery.scheduler.started", sources=list(sources.keys()))

    # Immediate first discovery tick so cold start does not wait a full interval.
    for name in sources:
        await push(DISCOVERY_QUEUE, {"source": name})

    try:
        while True:
            if await is_system_paused():
                await asyncio.sleep(2)
                continue
            payload = await pop(DISCOVERY_QUEUE, timeout=5)
            if payload is None:
                continue
            source_name = payload.get("source")
            if not source_name:
                continue
            try:
                await _tick_source(source_name)
                await ack(payload)
            except Exception as exc:
                logger.error("discovery.consume.failed", source=source_name, error=str(exc))
                await nack(payload, error=str(exc))
    except asyncio.CancelledError:
        scheduler.shutdown(wait=False)
        raise
