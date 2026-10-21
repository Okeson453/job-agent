"""Telegram command handlers.

Every handler calls the same service functions the API routes call —
never duplicates business logic.
"""

from __future__ import annotations

import uuid
from typing import Any, Callable, Coroutine

from sqlalchemy import select

from apps.telegram.formatters import format_daily_stats, format_job_card
from src.applications.models import Application
from src.applications.service import ApplicationActionError, approve_application, skip_application
from src.candidate.profile.service import get_profile
from src.database.session import get_session
from src.jobs.models import Job, JobMatch
from src.observability.logging import get_logger
from src.scheduler.queues import set_system_paused

logger = get_logger(__name__)

Handler = Callable[[str], Coroutine[Any, Any, str]]


async def cmd_jobs(_args: str) -> str:
    async with get_session() as db:
        result = await db.execute(
            select(Job).order_by(Job.discovered_at.desc()).limit(10)
        )
        jobs = result.scalars().all()
        if not jobs:
            return "No jobs found."
        lines = []
        for j in jobs:
            mr = await db.execute(select(JobMatch).where(JobMatch.job_id == j.id))
            match = mr.scalar_one_or_none()
            lines.append(format_job_card(j, match))
        return "\n\n".join(lines)


async def cmd_pending(_args: str) -> str:
    async with get_session() as db:
        result = await db.execute(
            select(Application)
            .where(Application.state.in_(["READY", "MANUAL_REVIEW"]))
            .order_by(Application.created_at.desc())
            .limit(10)
        )
        apps = result.scalars().all()
        if not apps:
            return "No pending applications."
        lines = [
            f"<code>{a.id}</code> state={a.state} job={a.job_id}" for a in apps
        ]
        return "\n".join(lines)


async def cmd_applied(_args: str) -> str:
    async with get_session() as db:
        result = await db.execute(
            select(Application)
            .where(Application.state == "SUBMITTED")
            .order_by(Application.created_at.desc())
            .limit(10)
        )
        apps = result.scalars().all()
        if not apps:
            return "No submitted applications."
        return "\n".join(f"<code>{a.id}</code> job={a.job_id}" for a in apps)


async def cmd_stats(_args: str) -> str:
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import func

    since = datetime.now(timezone.utc) - timedelta(days=1)
    async with get_session() as db:
        jobs_discovered = await db.scalar(
            select(func.count()).select_from(Job).where(Job.discovered_at >= since)
        )
        apps_total = await db.scalar(
            select(func.count())
            .select_from(Application)
            .where(Application.created_at >= since)
        )
        apps_submitted = await db.scalar(
            select(func.count())
            .select_from(Application)
            .where(
                Application.created_at >= since,
                Application.state == "SUBMITTED",
            )
        )
        failed = await db.scalar(
            select(func.count())
            .select_from(Application)
            .where(
                Application.created_at >= since,
                Application.state == "SUBMISSION_FAILED",
            )
        )
        high_match = await db.scalar(
            select(func.count())
            .select_from(JobMatch)
            .where(JobMatch.match_score >= 70, JobMatch.created_at >= since)
        )
    return format_daily_stats(
        {
            "jobs_discovered": jobs_discovered or 0,
            "applications": apps_total or 0,
            "submitted": apps_submitted or 0,
            "failed": failed or 0,
            "high_match": high_match or 0,
        }
    )


async def cmd_apply(args: str) -> str:
    """Identical code path to POST /applications/{id}/approve."""
    raw = args.strip().split()[0] if args.strip() else ""
    try:
        application_id = uuid.UUID(raw)
    except ValueError:
        return "Usage: /apply <application_id>"

    async with get_session() as db:
        try:
            app = await approve_application(db, application_id)
        except ApplicationActionError as exc:
            return str(exc)
        return f"Approved. Queued for submission: <code>{app.id}</code>"


async def cmd_skip(args: str) -> str:
    raw = args.strip().split()[0] if args.strip() else ""
    try:
        application_id = uuid.UUID(raw)
    except ValueError:
        return "Usage: /skip <application_id>"

    async with get_session() as db:
        try:
            app = await skip_application(db, application_id)
        except ApplicationActionError as exc:
            return str(exc)
        return f"Skipped: <code>{app.id}</code>"


async def cmd_pause(_args: str) -> str:
    await set_system_paused(True)
    return "System paused."


async def cmd_resume(_args: str) -> str:
    await set_system_paused(False)
    return "System resumed."


async def cmd_profile(_args: str) -> str:
    async with get_session() as db:
        profile = await get_profile(db)
        return (
            f"<b>{profile.full_name}</b>\n"
            f"Email: {profile.email}\n"
            f"Location: {profile.location}\n"
            f"Remote: {profile.remote_ok}\n"
            f"Skills: {', '.join(profile.skills[:8])}"
        )


async def cmd_interviews(_args: str) -> str:
    async with get_session() as db:
        result = await db.execute(
            select(Application)
            .where(Application.state == "INTERVIEW")
            .order_by(Application.created_at.desc())
            .limit(10)
        )
        apps = result.scalars().all()
        if not apps:
            return "No applications in interview state."
        return "\n".join(f"<code>{a.id}</code> job={a.job_id}" for a in apps)


async def cmd_rejected(_args: str) -> str:
    async with get_session() as db:
        result = await db.execute(
            select(Application)
            .where(
                Application.state.in_(
                    ["REJECTED_BY_FILTER", "LOW_MATCH", "SUBMISSION_FAILED"]
                )
            )
            .order_by(Application.created_at.desc())
            .limit(15)
        )
        apps = result.scalars().all()
        if not apps:
            return "No rejected applications."
        return "\n".join(
            f"<code>{a.id}</code> {a.state} {a.failure_reason or ''}" for a in apps
        )


async def cmd_answers(_args: str) -> str:
    from src.candidate.models import CandidateAnswer

    async with get_session() as db:
        result = await db.execute(
            select(CandidateAnswer).order_by(CandidateAnswer.created_at.desc()).limit(20)
        )
        rows = result.scalars().all()
        if not rows:
            return "Answer bank is empty."
        return "\n".join(
            f"[{r.category}] {r.question_text[:60]} → {r.answer_text[:80]}"
            for r in rows
        )


async def cmd_preferences(_args: str) -> str:
    async with get_session() as db:
        profile = await get_profile(db)
        return (
            f"Remote: {profile.remote_ok}\n"
            f"Nigeria eligible: {profile.nigeria_eligible}\n"
            f"Preferred roles: {', '.join(profile.preferred_roles)}\n"
            f"Min salary: {profile.min_salary or 'not set'} {profile.currency}\n"
            f"Availability: {profile.availability or 'not set'}\n"
            f"Work authorization: {profile.work_authorization or 'not set'}"
        )


HANDLERS: dict[str, Handler] = {
    "/jobs": cmd_jobs,
    "/today": cmd_jobs,
    "/pending": cmd_pending,
    "/applied": cmd_applied,
    "/interviews": cmd_interviews,
    "/rejected": cmd_rejected,
    "/stats": cmd_stats,
    "/apply": cmd_apply,
    "/skip": cmd_skip,
    "/pause": cmd_pause,
    "/resume": cmd_resume,
    "/profile": cmd_profile,
    "/answers": cmd_answers,
    "/preferences": cmd_preferences,
}
