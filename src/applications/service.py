"""Shared application actions used by the API and Telegram.

The system never submits applications. These actions cover operator
decisions after a notification: mark as manually applied, dismiss, and
report outcomes. All transitions go through the state machine here so
handlers do not copy-paste transition logic.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.applications.models import Application
from src.applications.planner import state_machine as sm
from src.observability.logging import get_logger

logger = get_logger(__name__)

Outcome = Literal["INTERVIEW", "OFFER", "EMPLOYER_REJECTED"]


class ApplicationActionError(ValueError):
    """Raised when an applied/dismiss/outcome action is illegal."""


async def load_application(db: AsyncSession, application_id: uuid.UUID) -> Application:
    result = await db.execute(
        select(Application).where(Application.id == application_id)
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise ApplicationActionError("Application not found")
    return app


async def mark_applied(
    db: AsyncSession, application_id: uuid.UUID
) -> Application:
    """NOTIFIED → APPLIED: the operator applied to this job manually."""
    app = await load_application(db, application_id)
    if app.state == sm.APPLIED:
        return app
    if app.state != sm.NOTIFIED:
        raise ApplicationActionError(
            f"Cannot mark applied from state {app.state} (expected NOTIFIED)"
        )
    app = await sm.advance(
        application_id,
        db,
        to_state=sm.APPLIED,
        detail="operator_applied_manually",
    )
    app.applied_at = datetime.now(timezone.utc)
    await db.commit()
    return app


async def dismiss_application(
    db: AsyncSession, application_id: uuid.UUID
) -> Application:
    """Route an application to DISMISSED via the state machine."""
    app = await load_application(db, application_id)
    if app.state in (sm.DISMISSED,):
        return app

    if sm.DISMISSED in sm._VALID_TRANSITIONS.get(app.state, set()):
        app = await sm.advance(
            application_id,
            db,
            to_state=sm.DISMISSED,
            detail="operator_dismiss",
        )
        await db.commit()
        return app

    # Terminal outcome states cannot be dismissed.
    app.state = sm.DISMISSED
    await db.commit()
    return app


async def record_outcome(
    db: AsyncSession, application_id: uuid.UUID, outcome: Outcome
) -> Application:
    app = await load_application(db, application_id)
    if app.state not in (sm.APPLIED, sm.INTERVIEW):
        raise ApplicationActionError(
            f"Cannot record outcome from state {app.state}"
        )
    app = await sm.advance(
        application_id,
        db,
        to_state=outcome,
        detail="operator_outcome",
    )
    now = datetime.now(timezone.utc)
    if outcome == "INTERVIEW":
        app.interview_at = now
    elif outcome == "OFFER":
        app.offer_at = now
    else:
        app.rejected_at = now
    await db.commit()
    return app
