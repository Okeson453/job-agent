"""Matching worker: deterministic score, enqueue for LLM if above threshold."""

from __future__ import annotations

import asyncio
import os
import uuid

from sqlalchemy import select

from src.candidate.profile.service import get_profile, load_min_match_score
from src.database.session import get_session
from src.jobs.job_state import set_job_state
from src.jobs.matcher.deterministic import score
from src.jobs.models import Job, JobMatch
from src.observability.logging import get_logger
from src.observability.tracing import span
from src.scheduler.queues import (
    ANALYSIS_QUEUE,
    LLM_QUEUE,
    ack,
    is_system_paused,
    nack,
    pop,
    push,
)

logger = get_logger(__name__)

_CONCURRENCY = int(os.environ.get("MATCHING_WORKER_CONCURRENCY", "5"))
_THRESHOLD = int(os.environ.get("MATCH_THRESHOLD", str(load_min_match_score())))


async def _process(job_id: str) -> None:
    with span("matching.deterministic", attributes={"job_id": job_id}):
        async with get_session() as db:
            result = await db.execute(
                select(Job).where(Job.id == uuid.UUID(job_id))
            )
            job = result.scalar_one_or_none()
            if job is None:
                logger.warning("matching.job_not_found", job_id=job_id)
                return

            set_job_state(job, "NORMALIZED", reason="matching_start")
            profile = await get_profile(db)
            deterministic = score(job, profile)

            match_row = JobMatch(
                job_id=job.id,
                deterministic_score=deterministic,
                match_score=deterministic,
                recommendation="REVIEW" if deterministic >= _THRESHOLD else "REJECT",
            )
            db.add(match_row)

            if deterministic < _THRESHOLD:
                set_job_state(job, "REJECTED_BY_FILTER", reason=f"score={deterministic}")
                await db.commit()
                logger.info("matching.rejected", job_id=job_id, score=deterministic)
                return

            set_job_state(job, "MATCHED", reason=f"score={deterministic}")
            await db.commit()
            await push(LLM_QUEUE, {"job_id": job_id})
            logger.info("matching.passed", job_id=job_id, score=deterministic)


async def run_matching_loop() -> None:
    sem = asyncio.Semaphore(_CONCURRENCY)
    logger.info("matching.loop.started", concurrency=_CONCURRENCY)
    active: set[asyncio.Task] = set()

    async def _guarded(message: dict) -> None:
        async with sem:
            try:
                await _process(message["job_id"])
                await ack(message)
            except Exception as exc:
                logger.error("matching.process.failed", error=str(exc))
                await nack(message, error=str(exc))

    while True:
        if await is_system_paused():
            await asyncio.sleep(2)
            continue
        # Bound in-flight tasks to concurrency
        while len(active) >= _CONCURRENCY:
            done, active = await asyncio.wait(active, return_when=asyncio.FIRST_COMPLETED)
            active = set(active)
        payload = await pop(ANALYSIS_QUEUE, timeout=5)
        if payload is None:
            continue
        task = asyncio.create_task(_guarded(payload))
        active.add(task)
        task.add_done_callback(active.discard)
