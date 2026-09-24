"""Job listing endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session
from src.jobs.models import Job
from src.jobs.schemas import JobRead

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobRead])
async def list_jobs(
    state: str | None = None,
    source: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> list[JobRead]:
    stmt = select(Job).order_by(Job.discovered_at.desc())
    if state:
        stmt = stmt.where(Job.state == state)
    if source:
        stmt = stmt.where(Job.source == source)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return [JobRead.model_validate(r) for r in result.scalars().all()]


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> JobRead:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Job not found")
    return JobRead.model_validate(job)
