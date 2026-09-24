"""Notification worker: format, send, and persist Telegram messages."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select

from src.database.session import get_session
from src.jobs.models import Job, JobMatch
from src.observability.logging import get_logger
from src.scheduler.queues import NOTIFICATION_QUEUE, ack, nack, pop
from src.telegram.notifier import send
from src.telegram.notifications_store import record_notification

logger = get_logger(__name__)


def _clip(text: str | None, n: int = 600) -> str:
    if not text:
        return "n/a"
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _format_apply_details(job: Job, match: JobMatch | None, application_id: str) -> str:
    """Full-detail Telegram card for every job being applied to."""
    techs = ", ".join(job.technologies or []) or "n/a"
    score = 0
    if match is not None:
        score = match.match_score or match.deterministic_score or 0
    salary = "n/a"
    if job.salary_min or job.salary_max:
        lo = job.salary_min or "?"
        hi = job.salary_max or "?"
        salary = f"{lo}–{hi}"
    countries = ", ".join(job.countries or []) or "n/a"
    return (
        f"<b>APPLYING</b>\n\n"
        f"<b>{job.title}</b>\n"
        f"Company: {job.company}\n"
        f"Employment: {job.employment_type or 'n/a'}\n"
        f"Remote: {'Yes' if job.remote else 'No'} | Location: {job.location or 'n/a'}\n"
        f"Countries: {countries}\n"
        f"Seniority: {job.seniority or 'n/a'}\n"
        f"Salary: {salary}\n"
        f"Match: {score}%\n"
        f"Stack: {techs}\n\n"
        f"URL: {job.application_url or 'n/a'}\n\n"
        f"<b>Description</b>\n{_clip(job.description, 800)}\n\n"
        f"Application ID: <code>{application_id}</code>\n"
        f"/apply {application_id}  ·  /skip {application_id}"
    )


def _format_review(application_id: str, job_title: str, reason: str | None = None) -> str:
    return (
        f"<b>MANUAL REVIEW NEEDED</b>\n\n"
        f"Job: {job_title}\n"
        f"Application: <code>{application_id}</code>\n"
        f"Reason: {reason or 'evidence validation could not fully ground the generated content.'}"
    )


def _format_failure(application_id: str, error: str | None) -> str:
    return (
        f"<b>SUBMISSION FAILED</b>\n\n"
        f"Application: <code>{application_id}</code>\n"
        f"Reason: {error or 'unknown'}"
    )


async def _send_recorded(msg_type: str, text: str, meta: dict | None = None) -> None:
    status, err = "sent", None
    try:
        await send(text)
    except Exception as exc:
        status, err = "failed", str(exc)
        raise
    finally:
        try:
            async with get_session() as db:
                await record_notification(
                    db,
                    msg_type=msg_type,
                    body=text,
                    status=status,
                    error=err,
                    meta=meta,
                )
                await db.commit()
        except Exception as exc:
            logger.warning("notification.persist.failed", error=str(exc))


async def _load_job_match(job_id: str):
    async with get_session() as db:
        job = (
            await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
        ).scalar_one_or_none()
        match = None
        if job is not None:
            match = (
                await db.execute(select(JobMatch).where(JobMatch.job_id == job.id))
            ).scalar_one_or_none()
        return job, match


async def _dispatch(payload: dict) -> None:
    msg_type = payload.get("type", "")
    application_id = payload.get("application_id", "")
    job_id = payload.get("job_id", "")
    meta = {
        "application_id": application_id or None,
        "job_id": job_id or None,
        "type": msg_type,
    }

    if msg_type in ("approval_needed", "applying", "application_ready"):
        job, match = (None, None)
        if job_id:
            job, match = await _load_job_match(job_id)
        if job is not None:
            text = _format_apply_details(job, match, application_id)
            await _send_recorded(msg_type, text, meta)
        else:
            await _send_recorded(
                msg_type,
                f"<b>APPLYING</b>\nApplication: <code>{application_id}</code>\nJob id: {job_id}",
                meta,
            )

    elif msg_type == "review_needed":
        title = "unknown"
        if job_id:
            job, _ = await _load_job_match(job_id)
            if job is not None:
                title = job.title
        await _send_recorded(
            msg_type,
            _format_review(application_id, title, payload.get("failure_reason")),
            meta,
        )

    elif msg_type in ("submission_failed", "failure"):
        await _send_recorded(
            msg_type, _format_failure(application_id, payload.get("error")), meta
        )

    elif msg_type == "daily_summary":
        from apps.telegram.formatters import format_daily_stats

        await _send_recorded(
            msg_type, format_daily_stats(payload.get("stats") or {}), meta
        )

    elif msg_type == "dlq_dead_letter":
        q = payload.get("queue", "?")
        attempts = payload.get("attempts", "?")
        err = payload.get("last_error") or "unknown"
        text = (
            f"<b>DEAD LETTER</b>\n\n"
            f"Queue: <code>{q}</code>\n"
            f"Attempts: {attempts}\n"
            f"Error: {err}"
        )
        await _send_recorded(msg_type, text, meta)

    else:
        logger.warning("notification.unknown_type", type=msg_type)


async def run_notification_loop() -> None:
    logger.info("notification.loop.started")
    while True:
        payload = await pop(NOTIFICATION_QUEUE, timeout=5)
        if payload is None:
            continue
        try:
            await _dispatch(payload)
            await ack(payload)
        except Exception as exc:
            logger.error("notification.dispatch.failed", error=str(exc))
            await nack(payload, error=str(exc))
