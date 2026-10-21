"""Direct API submission.

Greenhouse and Lever public boards do not expose a trustworthy unauthenticated
apply API. This module always returns failure so the browser path is used.
A generic 2xx must never be recorded as SUBMITTED.
"""

from __future__ import annotations

from src.applications.models import Application
from src.applications.schemas import SubmissionResult
from src.jobs.models import Job
from src.observability.logging import get_logger

logger = get_logger(__name__)


async def submit_via_api(
    job: Job,
    application: Application,
    *,
    candidate_email: str,
    candidate_name: str,
    resume_url: str | None = None,
    cover_letter: str | None = None,
) -> SubmissionResult:
    """No verified public apply API is wired. Always fall back to browser."""
    source = (job.source or "").lower()
    logger.info(
        "ats.no_verified_apply_api",
        source=source,
        job_id=str(job.id),
        url=job.application_url,
    )
    return SubmissionResult(
        success=False,
        error=(
            f"No verified direct apply API for source '{source}'. "
            "Use browser submission path."
        ),
    )
