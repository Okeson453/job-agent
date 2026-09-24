"""Shared application actions used by the API and Telegram.

Approve/skip/outcome updates go through the state machine here so handlers
do not copy-paste transition logic.
"""

from __future__ import annotations

import uuid
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.applications.models import Application
from src.applications.planner import state_machine as sm
from src.scheduler.queues import BROWSER_QUEUE, push

Outcome = Literal["INTERVIEW", "OFFER", "EMPLOYER_REJECTED"]


class ApplicationActionError(ValueError):
    """Raised when an approve/skip/outcome action is illegal."""


async def load_application(db: AsyncSession, application_id: uuid.UUID) -> Application:
    result = await db.execute(
        select(Application).where(Application.id == application_id)
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise ApplicationActionError("Application not found")
    return app


async def approve_application(
    db: AsyncSession, application_id: uuid.UUID
) -> Application:
    """READY or MANUAL_REVIEW → SUBMISSION, then enqueue browser work.

    Idempotent: already in SUBMISSION/SUBMITTED is a no-op.
    """
    app = await load_application(db, application_id)
    if app.state in (sm.SUBMITTED, sm.SUBMISSION):
        return app
    if app.state not in (sm.READY, sm.MANUAL_REVIEW):
        raise ApplicationActionError(
            f"Cannot approve application in state {app.state}"
        )
    app = await sm.advance(
        application_id,
        db,
        to_state=sm.SUBMISSION,
        detail="operator_approve",
    )
    await db.commit()
    await push(
        BROWSER_QUEUE,
        {"application_id": str(app.id), "job_id": str(app.job_id)},
    )
    return app


async def skip_application(
    db: AsyncSession, application_id: uuid.UUID
) -> Application:
    """Route an application to REJECTED_BY_FILTER via the state machine."""
    app = await load_application(db, application_id)
    if app.state in (sm.REJECTED_BY_FILTER, sm.SUBMITTED):
        return app

    # From any non-terminal pre-submit state, walk to REJECTED_BY_FILTER
    # if the transition exists; otherwise force via event + state write
    # after recording the skip event.
    if sm.REJECTED_BY_FILTER in sm._VALID_TRANSITIONS.get(app.state, set()):
        return await sm.advance(
            application_id,
            db,
            to_state=sm.REJECTED_BY_FILTER,
            detail="user_skip",
            extra={"failure_reason": "user_skip"},
        )

    await sm._record_event(
        db,
        application_id,
        event_type="user_skip",
        from_state=app.state,
        to_state=sm.REJECTED_BY_FILTER,
        detail="user_skip",
    )
    app.state = sm.REJECTED_BY_FILTER
    app.failure_reason = "user_skip"
    await db.flush()
    await db.refresh(app)
    return app


async def record_outcome(
    db: AsyncSession, application_id: uuid.UUID, outcome: Outcome
) -> Application:
    """Move SUBMITTED/INTERVIEW into interview / offer / employer-rejected."""
    app = await load_application(db, application_id)
    return await sm.advance(
        application_id,
        db,
        to_state=outcome,
        detail=f"operator_outcome:{outcome}",
    )
