"""LLM worker: retrieval + semantic match with independent qualification gate.

If the LLM is unavailable or returns a weak recommendation, jobs that already
cleared the deterministic match threshold are still promoted to application
so the pipeline does not stall on paid-API outages.
"""

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
_PROMOTE_DET = int(os.environ.get("MATCH_THRESHOLD", "40"))


def _qualify(match_result, blended: int, deterministic: int | None) -> bool:
    if match_result.recommendation != "QUALIFIED":
        return False
    if match_result.match < _MIN_SEMANTIC:
        return False
    if blended < _MIN_BLENDED:
        return False
    if deterministic is not None and deterministic < 30:
        return False
    return True


async def _promote(db, job, row, job_id: str, reason: str, score: int) -> None:
    set_job_state(job, "QUALIFIED", reason=reason)
    if row:
        row.recommendation = "QUALIFIED"
        row.match_score = score
    await db.commit()
    await push(APPLICATION_QUEUE, {"job_id": job_id})
    logger.info("llm.qualified", job_id=job_id, reason=reason, score=score)


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
                if row.deterministic_score is not None:
                    blended = int(round((row.deterministic_score + match_result.match) / 2))
                row.match_score = blended
                row.strong_matches = match_result.strong_matches
                row.gaps = match_result.gaps
                row.recommendation = match_result.recommendation
                row.analysis_raw = match_result.analysis

            det = int(deterministic) if deterministic is not None else 0

            if _qualify(match_result, blended, deterministic):
                await _promote(db, job, row, job_id, f"blended={blended}", blended)
                return

            if match_result.recommendation == "REVIEW":
                score = det if det else blended
                await _promote(db, job, row, job_id, f"auto_review_apply score={score}", score)
                return

            # LLM down or weak semantic: still apply if deterministic cleared threshold
            if det >= _PROMOTE_DET:
                await _promote(
                    db, job, row, job_id, f"deterministic_promote score={det}", det
                )
                return

            if row:
                row.recommendation = "REJECT"
            set_job_state(job, "LOW_MATCH", reason=f"gate failed blended={blended} det={det}")
            await db.commit()
            logger.info(
                "llm.not_qualified",
                job_id=job_id,
                recommendation=match_result.recommendation,
                blended=blended,
                deterministic=det,
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
