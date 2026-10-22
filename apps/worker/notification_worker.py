"""Notification worker: format, send, and persist Telegram messages.

Primary message type is "opportunity": a structured card for every
qualified job, followed by the tailored CV files and, when the posting
publishes a recruitment address, a ready-to-send application email draft.

Delivery is tracked per part so a retried queue message never re-sends a
message or file that already reached the chat.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from html import escape as html_escape
from typing import Any
from pathlib import Path

from sqlalchemy import select

from src.database.session import get_session
from src.jobs.models import Job, JobMatch
from src.observability.logging import get_logger
from src.scheduler.queues import NOTIFICATION_QUEUE, ack, nack, pop
from src.telegram.delivery import (
    PART_CARD,
    PART_CV_DOCX,
    PART_CV_PDF,
    PART_EMAIL,
    delivered_parts,
    mark_failed,
    mark_sent,
)
from src.telegram.notifier import send_document, send_message
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


def _match_text(match: JobMatch | None) -> tuple[int, list[Any], list[Any]]:
    if match is None:
        return 0, [], []
    score = match.match_score or match.deterministic_score or 0
    return score, list(match.strong_matches or []), list(match.gaps or [])


def _format_opportunity(
    job: Job,
    match: JobMatch | None,
    application_id: str,
    *,
    cv_pdf: str | None = None,
    cv_docx: str | None = None,
    email_draft: dict[str, Any] | None = None,
) -> str:
    """Full-detail Telegram card for a qualified opportunity."""
    score, strong, gaps = _match_text(match)
    techs = ", ".join(str(t) for t in (job.technologies or [])) or "n/a"
    countries = ", ".join(str(c) for c in (job.countries or [])) or "n/a"
    salary = _salary_text(job)

    arrangement = "Remote" if job.remote else "On-site"
    if "hybrid" in (job.location or "").lower():
        arrangement = "Hybrid"

    lines = [
        "<b>OPPORTUNITY</b>",
        "",
        f"<b>{html_escape(job.title)}</b>",
        f"Company: {html_escape(job.company)}",
        f"Seniority: {html_escape(job.seniority or 'n/a')}",
        f"Employment: {html_escape(job.employment_type or 'n/a')} | {arrangement}",
        f"Location: {html_escape(job.location or 'n/a')}",
        f"Geographic eligibility: {html_escape(countries)}",
        f"Salary: {html_escape(salary)}",
        f"Match: {score}%",
        f"Stack: {html_escape(techs)}",
        "",
        f"URL: {html_escape(job.application_url or 'n/a')}",
    ]

    if job.closing_date is not None:
        lines.append(f"Deadline: {job.closing_date:%Y-%m-%d}")

    if strong:
        lines.append("")
        lines.append("<b>Alignment</b>")
        lines.append(
            "Strong: " + html_escape(", ".join(str(s)[:60] for s in strong[:6]))
        )

    if gaps:
        lines.append("")
        lines.append("<b>Skill gaps</b>")
        lines.append(html_escape(", ".join(str(g)[:60] for g in gaps[:6])))

    lines.append("")
    lines.append("<b>Description</b>")
    lines.append(html_escape(_clip(job.description, 700)))

    attached = [
        Path(path).name
        for path in (cv_pdf, cv_docx)
        if path
    ]
    if attached:
        lines.append("")
        lines.append("<b>Tailored CV</b>")
        lines.append(html_escape("Attached: " + ", ".join(attached)))
    else:
        lines.append("")
        lines.append("<b>Tailored CV</b>")
        lines.append("Generation failed — open the URL to apply.")

    if email_draft and email_draft.get("to"):
        lines.append("")
        lines.append("<b>Application email</b>")
        lines.append(f"To: {html_escape(str(email_draft['to']))}")
        lines.append(
            f"Subject: {html_escape(str(email_draft.get('subject') or ''))}"
        )
        lines.append("Draft follows in the next message.")

    lines.append("")
    lines.append(f"Application ID: <code>{application_id}</code>")
    lines.append(f"/applied {application_id}  ·  /dismiss {application_id}")
    return "\n".join(lines)


def _format_email(job: Job, draft: dict[str, Any]) -> str:
    return "\n".join(
        [
            "<b>APPLICATION EMAIL — DRAFT</b>",
            f"<b>{html_escape(job.title)}</b> — {html_escape(job.company)}",
            "",
            f"<b>To:</b> {html_escape(str(draft.get('to') or ''))}",
            f"<b>Subject:</b> {html_escape(str(draft.get('subject') or ''))}",
            "",
            html_escape(str(draft.get("body") or "")),
            "",
            f"Job: {html_escape(job.application_url or '')}",
        ]
    )


def _format_recovered(detail: str | None) -> str:
    return (
        f"<b>PIPELINE RECOVERED</b>\n\n"
        f"Stuck pause cleared, stranded messages reclaimed and dead letters requeued.\n"
        f"Detail: <code>{detail or 'n/a'}</code>"
    )


async def _record(
    application_id: str,
    part: str,
    *,
    ok: bool,
    body: str = "",
    error: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    """Persist the delivery outcome for one part of the notification."""
    try:
        async with get_session() as db:
            if ok:
                await mark_sent(db, application_id, part, body_len=len(body))
                await record_notification(
                    db,
                    msg_type=f"opportunity.{part}",
                    body=body,
                    status="sent",
                    meta=meta,
                )
            else:
                await mark_failed(db, application_id, part, error or "unknown")
                await record_notification(
                    db,
                    msg_type=f"opportunity.{part}",
                    body=body,
                    status="failed",
                    error=error,
                    meta=meta,
                )
            await db.commit()
    except Exception as exc:
        logger.warning(
            "notification.persist.failed", part=part, error=str(exc)
        )


async def _mark_document_sent(application_id: str, path: str) -> None:
    try:
        from src.documents.models import GeneratedDocument

        async with get_session() as db:
            row = (
                await db.execute(
                    select(GeneratedDocument).where(
                        GeneratedDocument.application_id
                        == uuid.UUID(application_id),
                        GeneratedDocument.path == path,
                    )
                )
            ).scalar_one_or_none()
            if row is not None:
                row.sent_at = datetime.now(timezone.utc)
                await db.commit()
    except Exception as exc:
        logger.warning("notification.document_stamp.failed", error=str(exc))


async def _load_job_match(job_id: str) -> tuple[Job | None, JobMatch | None]:
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


async def _send_opportunity(payload: dict[str, Any]) -> None:
    application_id = payload.get("application_id", "")
    job_id = payload.get("job_id", "")
    if not application_id or not job_id:
        logger.warning("notification.opportunity.incomplete", payload=payload)
        return

    meta = {
        "application_id": application_id,
        "job_id": job_id,
        "type": "opportunity",
    }
    job, match = await _load_job_match(job_id)
    if job is None:
        await _record(
            application_id,
            PART_CARD,
            ok=False,
            error="job not found",
            meta=meta,
        )
        raise RuntimeError(f"job {job_id} not found")

    async with get_session() as db:
        done = await delivered_parts(db, application_id)

    cv_pdf = payload.get("cv_pdf")
    cv_docx = payload.get("cv_docx")
    email_draft = payload.get("email_draft")
    if not isinstance(email_draft, dict):
        email_draft = None

    if PART_CARD not in done:
        text = _format_opportunity(
            job,
            match,
            application_id,
            cv_pdf=cv_pdf,
            cv_docx=cv_docx,
            email_draft=email_draft,
        )
        try:
            await send_message(text)
        except Exception as exc:
            await _record(application_id, PART_CARD, ok=False, body=text, error=str(exc), meta=meta)
            raise
        await _record(application_id, PART_CARD, ok=True, body=text, meta=meta)

    for part, path, label in (
        (PART_CV_PDF, cv_pdf, "Tailored CV (PDF)"),
        (PART_CV_DOCX, cv_docx, "Tailored CV (DOCX)"),
    ):
        if not path or part in done:
            continue
        caption = f"<b>{html_escape(job.title)}</b> — {html_escape(job.company)}\n{label}"
        try:
            await send_document(path, caption=caption, filename=Path(path).name)
        except Exception as exc:
            await _record(application_id, part, ok=False, error=str(exc), meta=meta)
            raise
        await _record(application_id, part, ok=True, body=label, meta=meta)
        await _mark_document_sent(application_id, str(path))

    if email_draft and PART_EMAIL not in done:
        text = _format_email(job, email_draft)
        try:
            await send_message(text)
        except Exception as exc:
            await _record(application_id, PART_EMAIL, ok=False, body=text, error=str(exc), meta=meta)
            raise
        await _record(application_id, PART_EMAIL, ok=True, body=text, meta=meta)


async def _dispatch(payload: dict[str, Any]) -> None:
    msg_type = payload.get("type", "")

    if msg_type == "opportunity":
        await _send_opportunity(payload)
        return

    meta = {
        "application_id": payload.get("application_id") or None,
        "job_id": payload.get("job_id") or None,
        "type": msg_type,
    }

    if msg_type == "daily_summary":
        from apps.telegram.formatters import format_daily_stats

        await send_message(format_daily_stats(payload.get("stats") or {}))

    elif msg_type == "pipeline_recovered":
        text = _format_recovered(payload.get("detail"))
        await send_message(text)

    elif msg_type == "dlq_dead_letter":
        q = payload.get("queue", "?")
        attempts = payload.get("attempts", "?")
        err = payload.get("error") or payload.get("last_error") or "unknown"
        text = (
            f"<b>DEAD LETTER</b>\n\n"
            f"Queue: <code>{html_escape(str(q))}</code>\n"
            f"Attempts: {attempts}\n"
            f"Error: {html_escape(str(err))}"
        )
        await send_message(text)
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
