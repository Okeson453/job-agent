"""Daily and per-source statistics, including derived rates (§21)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session
from src.applications.models import Application
from src.jobs.models import Job, JobMatch

router = APIRouter(prefix="/stats", tags=["stats"])


def _rate(num: int | None, den: int | None) -> float:
    n = int(num or 0)
    d = int(den or 0)
    if d <= 0:
        return 0.0
    return round(n / d, 4)


@router.get("/daily")
async def daily_stats(
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=1)

    jobs_discovered = await db.scalar(
        select(func.count()).select_from(Job).where(Job.discovered_at >= since)
    )
    apps_total = await db.scalar(
        select(func.count())
        .select_from(Application)
        .where(Application.created_at >= since)
    )
    apps_notified = await db.scalar(
        select(func.count())
        .select_from(Application)
        .where(
            Application.created_at >= since,
            Application.state.in_(("NOTIFIED", "APPLIED", "INTERVIEW", "OFFER")),
        )
    )
    apps_applied = await db.scalar(
        select(func.count())
        .select_from(Application)
        .where(
            Application.created_at >= since,
            Application.state.in_(("APPLIED", "INTERVIEW", "OFFER")),
        )
    )
    apps_interview = await db.scalar(
        select(func.count())
        .select_from(Application)
        .where(Application.created_at >= since, Application.state == "INTERVIEW")
    )
    apps_offer = await db.scalar(
        select(func.count())
        .select_from(Application)
        .where(Application.created_at >= since, Application.state == "OFFER")
    )
    apps_responded = await db.scalar(
        select(func.count())
        .select_from(Application)
        .where(
            Application.created_at >= since,
            Application.state.in_(("INTERVIEW", "OFFER", "EMPLOYER_REJECTED")),
        )
    )
    high_match = await db.scalar(
        select(func.count())
        .select_from(JobMatch)
        .where(JobMatch.match_score >= 70, JobMatch.created_at >= since)
    )

    jd = int(jobs_discovered or 0)
    at = int(apps_total or 0)
    notif = int(apps_notified or 0)
    appl = int(apps_applied or 0)
    resp = int(apps_responded or 0)
    iv = int(apps_interview or 0)

    return {
        "jobs_discovered": jd,
        "opportunities_tracked": at,
        "notified": notif,
        "applied": appl,
        "interviews": iv,
        "offers": int(apps_offer or 0),
        "high_match": int(high_match or 0),
        "notification_rate": _rate(notif, jd),
        "application_rate": _rate(appl, notif),
        "response_rate": _rate(resp, appl),
        "interview_rate": _rate(iv, appl),
    }


@router.get("/rates")
async def rates_stats(
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    daily = await daily_stats(db)
    return {
        "notification_rate": daily["notification_rate"],
        "application_rate": daily["application_rate"],
        "response_rate": daily["response_rate"],
        "interview_rate": daily["interview_rate"],
        "window": "24h",
    }


@router.get("/sources")
async def source_stats(
    db: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=30)
    result = await db.execute(
        select(Job.source, func.count())
        .where(Job.discovered_at >= since)
        .group_by(Job.source)
        .order_by(func.count().desc())
    )
    rows = result.all()
    out = []
    for source, count in rows:
        job_ids = select(Job.id).where(Job.source == source, Job.discovered_at >= since)
        applied = await db.scalar(
            select(func.count())
            .select_from(Application)
            .where(
                Application.job_id.in_(job_ids),
                Application.state.in_(("APPLIED", "INTERVIEW", "OFFER")),
            )
        )
        interviews = await db.scalar(
            select(func.count())
            .select_from(Application)
            .where(
                Application.job_id.in_(job_ids),
                Application.state == "INTERVIEW",
            )
        )
        out.append(
            {
                "source": source,
                "count": count,
                "applied": applied,
                "source_conversion": _rate(applied, count),
                "interview_conversion": _rate(interviews, applied),
            }
        )
    return out
