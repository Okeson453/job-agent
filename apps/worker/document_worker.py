"""Document worker: eligibility, tailored CV generation, and dispatch.

Replaces the old application/browser workers. The system never submits
applications: after the LLM qualifies a job, this worker creates the tracking
record, runs the eligibility gate, renders a job-specific CV (PDF + DOCX),
marks the opportunity NOTIFIED, and enqueues the Telegram delivery.
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

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


_CV_MEDIA_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


async def _prepare_documents(
    db: AsyncSession, app: Application, job: Job
) -> dict[str, object]:
    """Generate the tailored CV, the email draft, and persist their records.

    Idempotent: files already recorded for this application are reused, so a
    retried notification never produces a second CV or a duplicate draft. The
    tailoring plan and the email draft are stored on the application record to
    keep the job → assessment → documents chain auditable.
    """
    from src.documents.email import draft_application_email, write_email_file
    from src.documents.generator import generate_cv
    from src.documents.kb import load_kb
    from src.documents.models import GeneratedDocument
    from src.documents.tailoring import build_plan

    rows = (
        await db.execute(
            select(GeneratedDocument).where(
                GeneratedDocument.application_id == app.id
            )
        )
    ).scalars().all()
    cv_rows = {row.format: row for row in rows if row.kind == "cv"}
    email_row = next((row for row in rows if row.kind == "email"), None)

    cached_draft = (app.metadata_ or {}).get("email_draft")
    cv_ready = {"pdf", "docx"} <= cv_rows.keys() and all(
        Path(row.path).exists() for row in cv_rows.values()
    )
    email_ready = (
        email_row is not None
        and Path(email_row.path).exists()
        and isinstance(cached_draft, dict)
        and bool(cached_draft.get("body"))
    )
    if cv_ready and (email_ready or not _email_enabled()):
        logger.info(
            "documents.reused",
            job_id=str(job.id),
            application_id=str(app.id),
        )
        return {
            "cv_pdf": cv_rows["pdf"].path,
            "cv_docx": cv_rows["docx"].path,
            "email_draft": cached_draft if email_ready else None,
        }

    kb = load_kb()
    plan = await build_plan(job, kb)
    metadata = {**(app.metadata_ or {}), "cv_plan": plan.model_dump()}

    artifact = await asyncio.to_thread(generate_cv, job, kb, plan)
    for fmt, path in (("pdf", artifact.pdf_path), ("docx", artifact.docx_path)):
        payload = await asyncio.to_thread(path.read_bytes)
        row = cv_rows.get(fmt)
        if row is None:
            row = GeneratedDocument(
                application_id=app.id, job_id=job.id, kind="cv", format=fmt
            )
            db.add(row)
        row.filename = path.name
        row.path = str(path)
        row.mime_type = _CV_MEDIA_TYPES[fmt]
        row.size_bytes = len(payload)
        row.sha256 = hashlib.sha256(payload).hexdigest()
        # Regenerated content has not been delivered yet.
        row.sent_at = None

    email_draft: dict[str, str] | None = None
    if _email_enabled():
        draft = await draft_application_email(job, kb, plan)
        if draft is not None:
            txt_path = artifact.pdf_path.parent / f"{artifact.filename_base}-email.txt"
            await asyncio.to_thread(write_email_file, draft, txt_path)
            payload = await asyncio.to_thread(txt_path.read_bytes)
            row = email_row
            if row is None:
                row = GeneratedDocument(
                    application_id=app.id, job_id=job.id, kind="email", format="txt"
                )
                db.add(row)
            row.filename = txt_path.name
            row.path = str(txt_path)
            row.mime_type = "text/plain"
            row.size_bytes = len(payload)
            row.sha256 = hashlib.sha256(payload).hexdigest()
            row.sent_at = None
            email_draft = {
                "to": draft.to,
                "subject": draft.subject,
                "body": draft.body,
            }
            metadata["email_draft"] = email_draft

    app.metadata_ = metadata
    await db.flush()
    logger.info(
        "documents.generated",
        job_id=str(job.id),
        application_id=str(app.id),
        filename=artifact.filename_base,
        has_email=email_draft is not None,
    )
    return {
        "cv_pdf": str(artifact.pdf_path),
        "cv_docx": str(artifact.docx_path),
        "email_draft": email_draft,
    }


def _email_enabled() -> bool:
    import os

    return os.environ.get("APPLICATION_EMAIL_ENABLED", "1").lower() not in {
        "0",
        "false",
        "no",
    }


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
            docs: dict[str, object] = {
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
