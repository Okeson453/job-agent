"""Job.state mutations with a recorded reason.

Job and Application keep separate state columns (pipeline vs application
lifecycle). This module is the only writer of Job.state so matching and
LLM workers do not scatter raw assignments.
"""

from __future__ import annotations

from src.jobs.models import Job
from src.observability.logging import get_logger

logger = get_logger(__name__)

ALLOWED_JOB_STATES = frozenset(
    {
        "DISCOVERED",
        "NORMALIZED",
        "ELIGIBILITY_CHECK",
        "MATCHED",
        "QUALIFIED",
        "REJECTED_BY_FILTER",
        "LOW_MATCH",
        "DUPLICATE",
    }
)


def set_job_state(job: Job, state: str, *, reason: str | None = None) -> None:
    """Set Job.state if *state* is a known job-pipeline value."""
    if state not in ALLOWED_JOB_STATES:
        raise ValueError(f"Unknown job state '{state}'")
    previous = job.state
    job.state = state
    logger.info(
        "job.state",
        job_id=str(job.id),
        from_state=previous,
        to_state=state,
        reason=reason,
    )
