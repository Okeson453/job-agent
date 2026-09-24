"""Application decision engine (Section 8).

Every module that changes an application's state does so by calling advance(),
never by writing state= directly.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.applications.models import Application, ApplicationEvent
from src.observability.logging import get_logger

logger = get_logger(__name__)

# Canonical states from the design document.
DISCOVERED = "DISCOVERED"
NORMALIZED = "NORMALIZED"
ELIGIBILITY_CHECK = "ELIGIBILITY_CHECK"
MATCHED = "MATCHED"
QUALIFIED = "QUALIFIED"
APPLICATION_PREP = "APPLICATION_PREP"
FACT_VALIDATION = "FACT_VALIDATION"
READY = "READY"
SUBMISSION = "SUBMISSION"
SUBMITTED = "SUBMITTED"
INTERVIEW = "INTERVIEW"
OFFER = "OFFER"
EMPLOYER_REJECTED = "EMPLOYER_REJECTED"

# Failure / terminal states.
REJECTED_BY_FILTER = "REJECTED_BY_FILTER"
LOW_MATCH = "LOW_MATCH"
MISSING_INFORMATION = "MISSING_INFORMATION"
MANUAL_REVIEW = "MANUAL_REVIEW"
SUBMISSION_FAILED = "SUBMISSION_FAILED"
DUPLICATE = "DUPLICATE"
HUMAN_INTERVENTION_REQUIRED = "HUMAN_INTERVENTION_REQUIRED"

_VALID_TRANSITIONS: dict[str, set[str]] = {
    DISCOVERED: {NORMALIZED, REJECTED_BY_FILTER, DUPLICATE},
    NORMALIZED: {ELIGIBILITY_CHECK, REJECTED_BY_FILTER},
    ELIGIBILITY_CHECK: {MATCHED, REJECTED_BY_FILTER},
    MATCHED: {QUALIFIED, LOW_MATCH, REJECTED_BY_FILTER},
    QUALIFIED: {APPLICATION_PREP, MISSING_INFORMATION},
    APPLICATION_PREP: {FACT_VALIDATION, MISSING_INFORMATION},
    FACT_VALIDATION: {READY, MANUAL_REVIEW},
    READY: {SUBMISSION, MANUAL_REVIEW},
    SUBMISSION: {SUBMITTED, SUBMISSION_FAILED, HUMAN_INTERVENTION_REQUIRED},
    SUBMITTED: {INTERVIEW, EMPLOYER_REJECTED, OFFER},
    INTERVIEW: {OFFER, EMPLOYER_REJECTED},
    OFFER: set(),
    EMPLOYER_REJECTED: set(),
    REJECTED_BY_FILTER: set(),
    LOW_MATCH: set(),
    MISSING_INFORMATION: set(),
    MANUAL_REVIEW: {READY, REJECTED_BY_FILTER, SUBMISSION},
    SUBMISSION_FAILED: {SUBMISSION, MANUAL_REVIEW, HUMAN_INTERVENTION_REQUIRED},
    HUMAN_INTERVENTION_REQUIRED: {SUBMISSION, MANUAL_REVIEW, REJECTED_BY_FILTER},
    DUPLICATE: set(),
}


async def _record_event(
    db: AsyncSession,
    application_id: uuid.UUID,
    event_type: str,
    from_state: str | None,
    to_state: str | None,
    detail: str | None = None,
) -> None:
    db.add(
        ApplicationEvent(
            application_id=application_id,
            event_type=event_type,
            from_state=from_state,
            to_state=to_state,
            detail=detail,
        )
    )


async def advance(
    application_id: uuid.UUID,
    db: AsyncSession,
    *,
    to_state: str,
    detail: str | None = None,
    extra: dict[str, Any] | None = None,
) -> Application:
    """Transition an application to *to_state* if the transition is valid.

    Raises ValueError on illegal transitions. Records an ApplicationEvent.
    """
    result = await db.execute(
        select(Application).where(Application.id == application_id)
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise ValueError(f"Application {application_id} not found")

    current = app.state
    allowed = _VALID_TRANSITIONS.get(current, set())
    if to_state not in allowed:
        raise ValueError(
            f"Illegal transition {current} → {to_state} for application {application_id}"
        )

    app.state = to_state
    if extra:
        # Application columns that may be updated during a transition.
        # Callers pass "metadata"; it is written to the ORM attribute metadata_.
        allowed_fields = {
            "cv_profile_name",
            "cover_letter",
            "failure_reason",
            "screenshot_path",
            "mode",
            "metadata",
        }
        for key, value in extra.items():
            if key == "metadata":
                app.metadata_ = value
            elif key in allowed_fields and hasattr(app, key):
                setattr(app, key, value)

    await _record_event(
        db,
        application_id,
        event_type="state_transition",
        from_state=current,
        to_state=to_state,
        detail=detail,
    )
    await db.flush()
    await db.refresh(app)

    logger.info(
        "application.transition",
        application_id=str(application_id),
        from_state=current,
        to_state=to_state,
    )
    return app


async def create_application(
    db: AsyncSession,
    job_id: uuid.UUID,
    *,
    mode: str = "APPROVAL",
) -> Application:
    """Idempotent create: one application row per job_id."""
    result = await db.execute(select(Application).where(Application.job_id == job_id))
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    app = Application(job_id=job_id, state=DISCOVERED, mode=mode)
    db.add(app)
    try:
        await db.flush()
    except Exception:
        await db.rollback()
        result = await db.execute(select(Application).where(Application.job_id == job_id))
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing
        raise
    await _record_event(
        db,
        app.id,
        event_type="created",
        from_state=None,
        to_state=DISCOVERED,
    )
    await db.refresh(app)
    return app


def is_terminal(state: str) -> bool:
    """Return True if *state* has no outgoing transitions."""
    return len(_VALID_TRANSITIONS.get(state, set())) == 0
