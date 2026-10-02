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

# Pipeline states the first session walks through before committing.
_PREP_TARGETS = [
    sm.NORMALIZED,
    sm.ELIGIBILITY_CHECK,
    sm.MATCHED,
    sm.QUALIFIED,
    sm.APPLICATION_PREP,
]

# States from which a retried job needs no further processing here.
_DONE_STATES = frozenset(
    {
        sm.REJECTED_BY_FILTER,
        sm.LOW_MATCH,
        sm.MISSING_INFORMATION,
        sm.DUPLICATE,
        sm.EMPLOYER_REJECTED,
        sm.OFFER,
        sm.SUBMITTED,
        sm.MANUAL_REVIEW,
        sm.SUBMISSION_FAILED,
        sm.HUMAN_INTERVENTION_REQUIRED,
    }
)


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
            # Idempotent: on a retry this returns the existing application,
            # which may already be part-way through the pipeline.
            app = await sm.create_application(db, job.id, mode=mode)
            app_id = app.id

            if app.state in _DONE_STATES:
                # A previous attempt already finished this application.
                # Replaying the pipeline would raise an illegal transition.
                await db.commit()
                return

            # Walk the pipeline forward, resuming from the current state
            # instead of replaying transitions that already happened.
            for target in _PREP_TARGETS:
                if app.state == target:
                    continue
                if not sm.can_transition(app.state, target):
                    # Retry from a later state: this step already happened.
                    continue
                app = await sm.advance(app.id, db, to_state=target)
                if target == sm.ELIGIBILITY_CHECK:
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

            await db.commit()

        async with get_session() as db:
            result = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
            job = result.scalar_one_or_none()
            if job is None:
                return
            ar = await db.execute(select(Application).where(Application.id == app_id))
            app = ar.scalar_one_or_none()
            if app is None:
                return

            cv_name: str | None = None
            validated: bool | None = None

            # Prep-phase work is only redone while the application is still
            # in prep; on a retry from a later state we must not duplicate
            # answers or re-run generation.
            if app.state in (sm.APPLICATION_PREP, sm.FACT_VALIDATION):
                cv_name = select_cv(job)
                facts = await retrieve(db, job)
                letter, validated = await generate_cover(job, facts)

                # Skip questions already answered by a previous attempt.
                existing = await db.execute(
                    select(ApplicationAnswer).where(
                        ApplicationAnswer.application_id == app.id
                    )
                )
                answered_questions = {a.question for a in existing.scalars()}

                missing_required = False
                for question in _PREP_QUESTIONS:
                    if question in answered_questions:
                        continue
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

                if sm.can_transition(app.state, sm.FACT_VALIDATION):
                    app = await sm.advance(app.id, db, to_state=sm.FACT_VALIDATION)

                if missing_required:
                    if sm.can_transition(app.state, sm.MISSING_INFORMATION):
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
                    if sm.can_transition(app.state, sm.MANUAL_REVIEW):
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

                if sm.can_transition(app.state, sm.READY):
                    app = await sm.advance(
                        app.id,
                        db,
                        to_state=sm.READY,
                        extra={
                            "cv_profile_name": cv_name,
                            "cover_letter": letter,
                        },
                    )
                await db.commit()

            # Dispatch only from READY; a retry from a later state has
            # already been dispatched (or is awaiting a human).
            if app.state == sm.READY:
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
