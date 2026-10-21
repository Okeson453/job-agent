"""Notification worker: format, send, and persist Telegram messages.

Primary message type is "opportunity": a structured card for every
qualified job delivered to the operator for manual review and action.
The system never submits applications; notifications are the delivery
endpoint of the pipeline.
"""

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


def _salary_text(job: Job) -> str:
    if not (job.salary_min or job.salary_max):
        return "n/a"
    lo = job.salary_min or "?"
    hi = job.salary_max or "?"
    cur = job.salary_currency or ""
    return f"{cur}{lo}–{hi}".strip()


def _match_text(match: JobMatch | None) -> tuple[int, list, list]:
    if match is None:
        return 0, [], []
    score = match.match_score or match.deterministic_score or 0
    return score, list(match.strong_matches or []), list(match.gaps or [])


def _format_opportunity(
    job: Job,
    match: JobMatch | None,
    application_id: str,
    cv_pdf: str | None = None,
    cv_docx: str | None = None,
    email_draft: str | None = None,
) -> str:
    """Full-detail Telegram card for a qualified opportunity."""
    score, strong, gaps = _match_text(match)
    techs = ", ".join(job.technologies or []) or "n/a"
    countries = ", ".join(job.countries or []) or "n/a"
    salary = _salary_text(job)

    arrangement = "Remote" if job.remote else "On-site"
    if "hybrid" in (job.location or "").lower():
        arrangement = "Hybrid"

    lines = [
        "<b>OPPORTUNITY</b>",
        "",
        f"<b>{job.title}</b>",
        f"Company: {job.company}",
        f"Seniority: {job.seniority or 'n/a'}",
        f"Employment: {job.employment_type or 'n/a'} | {arrangement}",
        f"Location: {job.location or 'n/a'}",
        f"Geographic eligibility: {countries}",
        f"Salary: {salary}",
        f"Match: {score}%",
        f"Stack: {techs}",
        "",
        f"URL: {job.application_url or 'n/a'}",
    ]

    if job.closing_date is not None:
        lines.append(f"Deadline: {job.closing_date:%Y-%m-%d}")

    if strong:
        lines.append("")
        lines.append("<b>Alignment</b>")
        lines.append(f"Strong: {', '.join(str(s)[:60] for s in strong[:6])}")

    if gaps:
        lines.append("")
        lines.append("<b>Skill gaps</b>")
        lines.append(f"{', '.join(str(g)[:60] for g in gaps[:6])}")

    lines.append("")
    lines.append(f"<b>Description</b>")
    lines.append(_clip(job.description, 800))

    if cv_pdf or cv_docx:
        lines.append("")
        lines.append("<b>Tailored CV</b>")
        if cv_pdf:
            lines.append(f"PDF: {cv_pdf}")
        if cv_docx:
            lines.append(f"DOCX: {cv_docx}")

    if email_draft:
        lines.append("")
        lines.append("<b>Application email draft</b>")
        lines.append(_clip(email_draft, 800))

    lines.append("")
    lines.append(f"Application ID: <code>{application_id}</code>")
    lines.append(f"/applied {application_id}  ·  /dismiss {application_id}")
    return "\n".join(lines)


def _format_recovered(detail: str | None) -> str:
    return (
        f"<b>PIPELINE RECOVERED</b>\n\n"
        f"Stuck pause cleared, stranded messages reclaimed and dead letters requeued.\n"
        f"Detail: <code>{detail or 'n/a'}</code>"
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

    if msg_type == "opportunity":
        job, match = (None, None)
        if job_id:
            job, match = await _load_job_match(job_id)
        if job is not None:
            text = _format_opportunity(
                job,
                match,
                application_id,
                cv_pdf=payload.get("cv_pdf"),
                cv_docx=payload.get("cv_docx"),
                email_draft=payload.get("email_draft"),
            )
            await _send_recorded(msg_type, text, meta)
        else:
            await _send_recorded(
                msg_type,
                f"<b>OPPORTUNITY</b>\nApplication: <code>{application_id}</code>\nJob id: {job_id}",
                meta,
            )

    elif msg_type == "daily_summary":
        from apps.telegram.formatters import format_daily_stats

        await _send_recorded(
            msg_type, format_daily_stats(payload.get("stats") or {}), meta
        )

    elif msg_type == "pipeline_recovered":
        await _send_recorded(
            msg_type, _format_recovered(payload.get("detail")), meta
        )

    elif msg_type == "dlq_dead_letter":
        q = payload.get("queue", "?")
        attempts = payload.get("attempts", "?")
        err = payload.get("error") or payload.get("last_error") or "unknown"
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
