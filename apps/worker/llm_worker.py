"""LLM worker: retrieval + semantic match with independent qualification gate."""

from __future__ import annotations

import asyncio
import os
import uuid

from sqlalchemy import select

from src.database.session import get_session
from src.jobs.job_state import set_job_state
from src.jobs.matcher.semantic import analyze
from src.jobs.models import Job, JobMatch
from src.llm.retrieval.retriever import retrieve
from src.observability.logging import get_logger
from src.observability.tracing import span
from src.scheduler.queues import (
    APPLICATION_QUEUE,
    LLM_QUEUE,
    NOTIFICATION_QUEUE,
    ack,
    is_system_paused,
    nack,
    pop,
    push,
)

logger = get_logger(__name__)

_CONCURRENCY = int(os.environ.get("LLM_WORKER_CONCURRENCY", "3"))
_MIN_SEMANTIC = int(os.environ.get("SEMANTIC_MATCH_MIN", "50"))
_MIN_BLENDED = int(os.environ.get("BLENDED_MATCH_MIN", "45"))


def _qualify(match_result, blended: int, deterministic: int | None) -> bool:
    """Deterministic gate — LLM recommendation alone is not enough."""
    if match_result.recommendation != "QUALIFIED":
        return False
    if match_result.match < _MIN_SEMANTIC:
        return False
    if blended < _MIN_BLENDED:
        return False
    if deterministic is not None and deterministic < 30:
        return False
    return True


async def _process(job_id: str) -> None:
    with span("matching.semantic", attributes={"job_id": job_id}):
        async with get_session() as db:
            result = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
            job = result.scalar_one_or_none()
            if job is None:
                return

            facts = await retrieve(db, job)
            match_result = await analyze(job, facts)

            mr = await db.execute(select(JobMatch).where(JobMatch.job_id == job.id))
            row = mr.scalar_one_or_none()
            deterministic = row.deterministic_score if row else None
            blended = match_result.match
            if row:
                row.semantic_score = float(match_result.match)
                if row.deterministic_score:
                    blended = int(round((row.deterministic_score + match_result.match) / 2))
                row.match_score = blended
                row.strong_matches = match_result.strong_matches
                row.gaps = match_result.gaps
                row.recommendation = match_result.recommendation
                row.analysis_raw = match_result.analysis

            if _qualify(match_result, blended, deterministic):
                set_job_state(job, "QUALIFIED", reason=f"blended={blended}")
                if row:
                    row.recommendation = "QUALIFIED"
                await db.commit()
                await push(APPLICATION_QUEUE, {"job_id": job_id})
                logger.info("llm.qualified", job_id=job_id, blended=blended)
            elif match_result.recommendation == "REVIEW":
                # Borderline: surface to operator instead of stranding as MATCHED.
                set_job_state(job, "MATCHED", reason="semantic_review")
                if row:
                    row.recommendation = "REVIEW"
                await db.commit()
                await push(
                    NOTIFICATION_QUEUE,
                    {
                        "type": "review_needed",
                        "job_id": job_id,
                        "failure_reason": f"semantic_review blended={blended}",
                    },
                )
                logger.info("llm.review", job_id=job_id, blended=blended)
            else:
                next_state = "LOW_MATCH"
                if row:
                    row.recommendation = "REJECT"
                set_job_state(job, next_state, reason=f"gate failed blended={blended}")
                await db.commit()
                logger.info(
                    "llm.not_qualified",
                    job_id=job_id,
                    recommendation=match_result.recommendation,
                    blended=blended,
                )


async def run_llm_loop() -> None:
    sem = asyncio.Semaphore(_CONCURRENCY)
    logger.info("llm.loop.started", concurrency=_CONCURRENCY)
    active: set[asyncio.Task] = set()

    async def _guarded(message: dict) -> None:
        async with sem:
            try:
                await _process(message["job_id"])
                await ack(message)
            except Exception as exc:
                logger.error("llm.process.failed", error=str(exc))
                await nack(message, error=str(exc))

    while True:
        if await is_system_paused():
            await asyncio.sleep(2)
            continue
        while len(active) >= _CONCURRENCY:
            done, active = await asyncio.wait(active, return_when=asyncio.FIRST_COMPLETED)
            active = set(active)
        payload = await pop(LLM_QUEUE, timeout=5)
        if payload is None:
            continue
        task = asyncio.create_task(_guarded(payload))
        active.add(task)
        task.add_done_callback(active.discard)
