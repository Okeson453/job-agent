"""Application listing and approve/skip endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session
from src.applications.models import Application
from src.applications.schemas import ApplicationRead
from src.applications.service import (
    ApplicationActionError,
    approve_application as approve_svc,
    record_outcome,
    skip_application as skip_svc,
)

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationRead])
async def list_applications(
    state: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> list[ApplicationRead]:
    stmt = select(Application).order_by(Application.created_at.desc())
    if state:
        stmt = stmt.where(Application.state == state)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return [ApplicationRead.model_validate(r) for r in result.scalars().all()]


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> ApplicationRead:
    result = await db.execute(
        select(Application).where(Application.id == application_id)
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return ApplicationRead.model_validate(app)


@router.post("/{application_id}/approve", response_model=ApplicationRead)
async def approve_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> ApplicationRead:
    try:
        app = await approve_svc(db, application_id)
    except ApplicationActionError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail.lower() else 409
        raise HTTPException(status_code=status, detail=detail) from exc
    return ApplicationRead.model_validate(app)


@router.post("/{application_id}/skip", response_model=ApplicationRead)
async def skip_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> ApplicationRead:
    try:
        app = await skip_svc(db, application_id)
    except ApplicationActionError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail.lower() else 409
        raise HTTPException(status_code=status, detail=detail) from exc
    return ApplicationRead.model_validate(app)


@router.post("/{application_id}/outcome/{outcome}", response_model=ApplicationRead)
async def set_outcome(
    application_id: uuid.UUID,
    outcome: str,
    db: AsyncSession = Depends(get_db_session),
) -> ApplicationRead:
    if outcome not in ("INTERVIEW", "OFFER", "EMPLOYER_REJECTED"):
        raise HTTPException(status_code=400, detail="Invalid outcome")
    try:
        app = await record_outcome(db, application_id, outcome)  # type: ignore[arg-type]
    except (ApplicationActionError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ApplicationRead.model_validate(app)
