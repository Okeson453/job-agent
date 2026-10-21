"""Browser / ATS submission worker. Concurrency hard-capped for Playwright."""

from __future__ import annotations

import asyncio
import os
import uuid

from sqlalchemy import select

from src.applications.browser.session import open_context
from src.applications.documents.cv_paths import resolve_cv_path
from src.applications.questions.engine import answer as answer_question
from src.applications.models import Application, ApplicationAnswer
from src.applications.schemas import SubmissionResult
from src.applications.submission.ats_client import submit_via_api
from src.applications.submission.tracker import record_result
from src.candidate.profile.service import get_profile
from src.database.session import get_session
from src.jobs.models import Job
from src.observability.logging import get_logger
from src.observability.tracing import span
from src.scheduler.queues import (
    BROWSER_QUEUE,
    NOTIFICATION_QUEUE,
    ack,
    is_system_paused,
    nack,
    pop,
    push,
)

logger = get_logger(__name__)

_CONCURRENCY = int(os.environ.get("BROWSER_WORKER_CONCURRENCY", "2"))


async def _answers_map(db, app: Application) -> dict[str, str]:
    result = await db.execute(
        select(ApplicationAnswer).where(ApplicationAnswer.application_id == app.id)
    )
    out: dict[str, str] = {}
    for row in result.scalars().all():
        if row.answer:
            out[row.question.lower()] = row.answer
    return out


async def _process(application_id: str, job_id: str) -> None:
    with span(
        "browser.submit",
        attributes={"application_id": application_id, "job_id": job_id},
    ):
        context = None
        try:
            async with get_session() as db:
                app_result = await db.execute(
                    select(Application).where(
                        Application.id == uuid.UUID(application_id)
                    )
                )
                app = app_result.scalar_one_or_none()
                job_result = await db.execute(
                    select(Job).where(Job.id == uuid.UUID(job_id))
                )
                job = job_result.scalar_one_or_none()
                if app is None or job is None:
                    return

                profile = await get_profile(db)
                cv_path = await resolve_cv_path(db, app.cv_profile_name)
                if cv_path is None:
                    logger.warning(
                        "browser.missing_cv",
                        application_id=application_id,
                        profile=app.cv_profile_name,
                    )

                extra = await _answers_map(db, app)

                result = await submit_via_api(
                    job,
                    app,
                    candidate_email=profile.email,
                    candidate_name=profile.full_name,
                    resume_url=cv_path,
                    cover_letter=app.cover_letter,
                )
                used_browser = False
                if not result.success:
                    from src.applications.browser.form_filler import submit as form_submit

                    context = await open_context()
                    page = await context.new_page()
                    used_browser = True
                    async def _resolve(label: str) -> str | None:
                        """Route unknown form fields through the question engine."""
                        answered = await answer_question(db, label, app)
                        if answered.answer:
                            db.add(
                                ApplicationAnswer(
                                    application_id=app.id,
                                    question=answered.question,
                                    answer=answered.answer,
                                    category=answered.category,
                                    validated=answered.validated,
                                )
                            )
                            await db.flush()
                            return answered.answer
                        return None

                    result = await form_submit(
                        page,
                        job.application_url,
                        profile,
                        cv_path=cv_path,
                        cover_letter=app.cover_letter,
                        extra_answers=extra,
                        require_cv=True,
                        resolve_answer=_resolve,
                    )

                if cv_path is None and result.success:
                    result = SubmissionResult(
                        success=result.success,
                        confirmation_id=result.confirmation_id,
                        error=(result.error or "") + "; submitted_without_cv",
                        screenshot_path=result.screenshot_path,
                        dom_path=result.dom_path,
                    )

                if result.error and "captcha" in (result.error or "").lower():
                    from src.applications.planner import state_machine as sm
                    await sm.advance(
                        app.id,
                        db,
                        to_state=sm.HUMAN_INTERVENTION_REQUIRED,
                        detail="captcha_detected",
                        extra={"failure_reason": result.error},
                    )
                else:
                    await record_result(app.id, result, db)
                await db.commit()

                await push(
                    NOTIFICATION_QUEUE,
                    {
                        "type": "submission_failed"
                        if not result.success
                        else "submission_result",
                        "application_id": application_id,
                        "success": result.success,
                        "error": result.error,
                        "missing_cv": cv_path is None,
                        "via": "browser" if used_browser else "ats_api",
                    },
                )
        except Exception as exc:
            logger.error(
                "browser.process.failed",
                application_id=application_id,
                error=str(exc),
            )
            async with get_session() as db:
                await record_result(
                    uuid.UUID(application_id),
                    SubmissionResult(success=False, error=str(exc)),
                    db,
                )
                await push(
                    NOTIFICATION_QUEUE,
                    {
                        "type": "submission_failed",
                        "application_id": application_id,
                        "success": False,
                        "error": str(exc),
                    },
                )
        finally:
            if context is not None:
                await context.close()


async def run_browser_loop() -> None:
    sem = asyncio.Semaphore(_CONCURRENCY)
    logger.info("browser.loop.started", concurrency=_CONCURRENCY)

    active: set[asyncio.Task] = set()

    async def _guarded(payload: dict) -> None:
        async with sem:
            try:
                await _process(payload["application_id"], payload["job_id"])
                await ack(payload)
            except Exception as exc:
                logger.error("browser.guard.failed", error=str(exc))
                await nack(payload, error=str(exc))

    while True:
        if await is_system_paused():
            await asyncio.sleep(2)
            continue
        while len(active) >= _CONCURRENCY:
            done, active = await asyncio.wait(active, return_when=asyncio.FIRST_COMPLETED)
            active = set(active)
        payload = await pop(BROWSER_QUEUE, timeout=5)
        if payload is None:
            continue
        task = asyncio.create_task(_guarded(payload))
        active.add(task)
        task.add_done_callback(active.discard)
