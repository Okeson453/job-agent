"""Application worker: eligibility, CV, cover letter, questions, evidence validation."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select

from src.applications.documents.cover_letter import generate as generate_cover
from src.applications.documents.cv_selector import select as select_cv
from src.applications.eligibility import check_eligibility
from src.applications.models import Application, ApplicationAnswer
from src.applications.planner import state_machine as sm
from src.applications.questions.engine import answer as answer_question
from src.candidate.profile.service import get_profile, load_excluded_companies
from src.database.session import get_session
from src.jobs.models import Job
from src.llm.retrieval.retriever import retrieve
from src.observability.logging import get_logger
from src.observability.tracing import span
from src.scheduler.queues import (
    APPLICATION_QUEUE,
    BROWSER_QUEUE,
    NOTIFICATION_QUEUE,
    ack,
    is_system_paused,
    nack,
    pop,
    push,
)
from src.security.secrets import get_secret

logger = get_logger(__name__)

_PREP_QUESTIONS = [
    "Describe your relevant experience for this role.",
    "Why do you want this role?",
]


async def _process(job_id: str) -> None:
    with span("application.prepare", attributes={"job_id": job_id}):
        async with get_session() as db:
            result = await db.execute(
                select(Job).where(Job.id == uuid.UUID(job_id))
            )
            job = result.scalar_one_or_none()
            if job is None:
                return

            profile = await get_profile(db)
            mode = get_secret("APPLICATION_MODE_DEFAULT")
            app = await sm.create_application(db, job.id, mode=mode)

            await sm.advance(app.id, db, to_state=sm.NORMALIZED)
            await sm.advance(app.id, db, to_state=sm.ELIGIBILITY_CHECK)

            eligible, reason = check_eligibility(
                job, profile, excluded_companies=load_excluded_companies()
            )
            if not eligible:
                await sm.advance(
                    app.id,
                    db,
                    to_state=sm.REJECTED_BY_FILTER,
                    detail=reason,
                    extra={"failure_reason": reason},
                )
                await db.commit()
                return

            await sm.advance(app.id, db, to_state=sm.MATCHED)
            await sm.advance(app.id, db, to_state=sm.QUALIFIED)
            await sm.advance(app.id, db, to_state=sm.APPLICATION_PREP)
            await db.commit()
            app_id = app.id

        async with get_session() as db:
            result = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
            job = result.scalar_one_or_none()
            if job is None:
                return
            ar = await db.execute(select(Application).where(Application.id == app_id))
            app = ar.scalar_one_or_none()
            if app is None:
                return

            cv_name = select_cv(job)
            facts = await retrieve(db, job)
            letter, validated = await generate_cover(job, facts)

            missing_required = False
            for question in _PREP_QUESTIONS:
                answered = await answer_question(db, question, app)
                db.add(
                    ApplicationAnswer(
                        application_id=app.id,
                        question=answered.question,
                        answer=answered.answer,
                        category=answered.category,
                        validated=answered.validated,
                    )
                )
                if answered.source == "manual" and not answered.answer:
                    missing_required = True

            await sm.advance(app.id, db, to_state=sm.FACT_VALIDATION)

            if missing_required:
                await sm.advance(
                    app.id,
                    db,
                    to_state=sm.MISSING_INFORMATION,
                    detail="hard-excluded question unanswered",
                    extra={
                        "cv_profile_name": cv_name,
                        "cover_letter": letter or None,
                        "failure_reason": "missing_required_answer",
                    },
                )
                await db.commit()
                return

            if not letter or not str(letter).strip():
                await sm.advance(
                    app.id,
                    db,
                    to_state=sm.MANUAL_REVIEW,
                    detail="empty cover letter",
                    extra={
                        "cv_profile_name": cv_name,
                        "cover_letter": None,
                        "failure_reason": "empty_cover_letter",
                    },
                )
                await db.commit()
                await push(
                    NOTIFICATION_QUEUE,
                    {
                        "type": "review_needed",
                        "application_id": str(app.id),
                        "job_id": job_id,
                        "failure_reason": "empty_cover_letter",
                    },
                )
                return
            if not validated:
                logger.warning(
                    "application.evidence_soft_pass",
                    application_id=str(app.id),
                    job_id=job_id,
                )

            await sm.advance(
                app.id,
                db,
                to_state=sm.READY,
                extra={
                    "cv_profile_name": cv_name,
                    "cover_letter": letter,
                },
            )
            await db.commit()

            # Always notify Telegram with full job details before/with apply.
            await push(
                NOTIFICATION_QUEUE,
                {
                    "type": "applying",
                    "application_id": str(app.id),
                    "job_id": job_id,
                },
            )

            if mode == "AUTO":
                await sm.advance(app.id, db, to_state=sm.SUBMISSION)
                await db.commit()
                await push(
                    BROWSER_QUEUE,
                    {"application_id": str(app.id), "job_id": job_id},
                )
            elif mode == "BLOCK":
                await sm.advance(
                    app.id,
                    db,
                    to_state=sm.MANUAL_REVIEW,
                    detail="mode_block",
                    extra={"failure_reason": "blocked_by_mode"},
                )
                await db.commit()
                logger.info("application.blocked", application_id=str(app.id))
            else:
                await push(
                    NOTIFICATION_QUEUE,
                    {
                        "type": "approval_needed",
                        "application_id": str(app.id),
                        "job_id": job_id,
                    },
                )

            logger.info(
                "application.ready",
                application_id=str(app.id),
                job_id=job_id,
                mode=mode,
                validated=validated,
                cv=cv_name,
            )


async def run_application_loop() -> None:
    logger.info("application.loop.started")
    while True:
        if await is_system_paused():
            await asyncio.sleep(2)
            continue
        payload = await pop(APPLICATION_QUEUE, timeout=5)
        if payload is None:
            continue
        try:
            await _process(payload["job_id"])
            await ack(payload)
        except Exception as exc:
            logger.error("application.process.failed", error=str(exc))
            await nack(payload, error=str(exc))
