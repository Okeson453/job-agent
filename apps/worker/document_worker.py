"""Document worker: eligibility, document prep, and notification dispatch.

Replaces the old application/browser workers. The system never submits
applications: after the LLM qualifies a job, this worker creates the
tracking record, runs the eligibility gate, prepares documents (tailored
CV / application email — generation wired in the documents phase), marks
the opportunity NOTIFIED, and enqueues the Telegram delivery.

Phase note: document generation (CV/email) is not yet implemented here;
this worker currently walks the pipeline and dispatches the opportunity
notification. Generation slots into _prepare_documents().
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.applications.eligibility import check_eligibility
from src.applications.models import Application
from src.applications.planner import state_machine as sm
from src.candidate.profile.service import get_profile, load_excluded_companies
from src.database.session import get_session
from src.jobs.models import Job
from src.observability.logging import get_logger
from src.observability.tracing import span
from src.scheduler.queues import (
    DOCUMENT_QUEUE,
    NOTIFICATION_QUEUE,
    ack,
    is_system_paused,
    nack,
    pop,
    push,
)

logger = get_logger(__name__)

# Pipeline states the tracking record walks through before notification.
_PREP_TARGETS = [
    sm.NORMALIZED,
    sm.ELIGIBILITY_CHECK,
    sm.MATCHED,
    sm.QUALIFIED,
    sm.DOCUMENT_PREP,
]

# States from which a retried job needs no further processing here.
_DONE_STATES = frozenset(
    {
        sm.NOTIFIED,
        sm.APPLIED,
        sm.INTERVIEW,
        sm.OFFER,
        sm.EMPLOYER_REJECTED,
        sm.DISMISSED,
        sm.REJECTED_BY_FILTER,
        sm.LOW_MATCH,
        sm.MISSING_INFORMATION,
        sm.DUPLICATE,
    }
)


def _tick() -> None:
    try:
        from apps.worker.main import mark_tick

        mark_tick("documents")
    except Exception:
        pass


async def _prepare_documents(
    db: AsyncSession, app: Application, job: Job
) -> dict[str, str | None]:
    """Prepare the tailored CV and application email draft for a job.

    Placeholder in this phase: returns document descriptors without
    generating files. CV/email generation is wired here in the documents
    phase; the notification layer treats missing documents gracefully.
    """
    # Intentional no-op placeholder (documents phase implements generation).
    return {"cv_pdf": None, "cv_docx": None, "email_draft": None}


async def _process(job_id: str) -> None:
    _tick()
    with span("documents.prepare", attributes={"job_id": job_id}):
        async with get_session() as db:
            result = await db.execute(
                select(Job).where(Job.id == uuid.UUID(job_id))
            )
            job = result.scalar_one_or_none()
            if job is None:
                logger.warning("documents.job_missing", job_id=job_id)
                return

            profile = await get_profile(db)

            # Idempotent: on a retry this returns the existing tracking
            # record, which may already be part-way through the pipeline.
            app = await sm.create_application(db, job.id)
            app_id = app.id

            if app.state in _DONE_STATES:
                # A previous attempt already finished (or the operator
                # already acted). Replaying would raise illegal transitions.
                await db.commit()
                return

            for target in _PREP_TARGETS:
                if app.state == target:
                    continue
                if not sm.can_transition(app.state, target):
                    # Retry from a later state: this step already happened.
                    continue
                if target == sm.ELIGIBILITY_CHECK:
                    excluded = load_excluded_companies()
                    eligible, reason = check_eligibility(
                        job, profile, excluded_companies=excluded
                    )
                    if not eligible:
                        await sm.advance(
                            app.id,
                            db,
                            to_state=sm.REJECTED_BY_FILTER,
                            detail=f"ineligible:{reason}",
                            extra={"failure_reason": reason},
                        )
                        await db.commit()
                        logger.info("documents.ineligible", job_id=job_id, reason=reason)
                        return
                app = await sm.advance(app.id, db, to_state=target)

            # Document preparation (CV / email draft). Failure is not fatal:
            # the opportunity is still delivered, flagged as doc-less.
            docs: dict[str, str | None] = {
                "cv_pdf": None,
                "cv_docx": None,
                "email_draft": None,
            }
            try:
                docs = await _prepare_documents(db, app, job)
            except Exception as exc:
                logger.error(
                    "documents.preparation_failed",
                    job_id=job_id,
                    error=str(exc),
                )
                if sm.can_transition(app.state, sm.DOCUMENT_FAILED):
                    app = await sm.advance(
                        app.id,
                        db,
                        to_state=sm.DOCUMENT_FAILED,
                        detail=f"document_error:{exc}",
                        extra={"failure_reason": f"document_error:{exc}"},
                    )
            # DOCUMENT_FAILED → NOTIFIED is a legal recovery path: the
            # opportunity is delivered even without generated documents.
            if sm.can_transition(app.state, sm.NOTIFIED):
                app = await sm.advance(
                    app.id,
                    db,
                    to_state=sm.NOTIFIED,
                    detail=(
                        "notified_without_documents"
                        if app.state == sm.DOCUMENT_FAILED
                        else None
                    ),
                )
            app.notified_at = datetime.now(timezone.utc)
            await db.commit()

            await push(
                NOTIFICATION_QUEUE,
                {
                    "type": "opportunity",
                    "application_id": str(app_id),
                    "job_id": job_id,
                    "cv_pdf": docs.get("cv_pdf"),
                    "cv_docx": docs.get("cv_docx"),
                    "email_draft": docs.get("email_draft"),
                },
            )
            logger.info("documents.notified", job_id=job_id, application_id=str(app_id))


async def run_document_loop() -> None:
    logger.info("documents.loop.started")
    while True:
        if await is_system_paused():
            await asyncio.sleep(2)
            continue
        payload = await pop(DOCUMENT_QUEUE, timeout=5)
        if payload is None:
            continue
        job_id = payload.get("job_id")
        if not job_id:
            await ack(payload)
            continue
        try:
            await _process(job_id)
            await ack(payload)
        except Exception as exc:
            logger.error("documents.process.failed", job_id=job_id, error=str(exc))
            await nack(payload, error=str(exc))
