"""Record submission results. Only writer of SUBMITTED / SUBMISSION_FAILED state."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from datetime import datetime, timezone

from src.applications.planner import state_machine as sm
from src.applications.schemas import SubmissionResult
from src.observability.logging import get_logger

logger = get_logger(__name__)


async def record_result(
    application_id: uuid.UUID,
    result: SubmissionResult,
    db: AsyncSession,
) -> None:
    """Write SUBMITTED or SUBMISSION_FAILED and append an ApplicationEvent."""
    if result.success:
        app = await sm.advance(
            application_id,
            db,
            to_state=sm.SUBMITTED,
            detail=result.confirmation_id or "submitted",
            extra={
                "screenshot_path": result.screenshot_path,
            },
        )
        app.submitted_at = datetime.now(timezone.utc)
        logger.info(
            "submission.success",
            application_id=str(application_id),
            confirmation=result.confirmation_id,
        )
    else:
        await sm.advance(
            application_id,
            db,
            to_state=sm.SUBMISSION_FAILED,
            detail=result.error or "unknown failure",
            extra={
                "failure_reason": result.error,
                "screenshot_path": result.screenshot_path,
            },
        )
        logger.error(
            "submission.failed",
            application_id=str(application_id),
            error=result.error,
        )
