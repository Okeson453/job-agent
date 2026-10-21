"""Eligibility check between NORMALIZED and MATCHED.

Filters on remote preference, Nigeria eligibility, and excluded companies
from the candidate profile / preferences.
"""

from __future__ import annotations

from src.candidate.schemas import CandidateProfile
from src.jobs.models import Job


def check_eligibility(
    job: Job, profile: CandidateProfile, *, excluded_companies: list[str] | None = None
) -> tuple[bool, str]:
    """Return (eligible, reason). Reason is empty when eligible."""
    company = (job.company or "").lower()
    for excluded in excluded_companies or []:
        if excluded and excluded.lower() in company:
            return False, f"excluded_company:{excluded}"

    if job.remote and not profile.remote_ok:
        return False, "remote_not_accepted"

    if not job.remote and profile.remote_ok:
        # On-site-only roles are allowed only when the location is Nigeria.
        location = (job.location or "").lower()
        countries = [c.lower() for c in (job.countries or [])]
        if "nigeria" not in location and "nigeria" not in countries and "ng" not in countries:
            if not profile.nigeria_eligible:
                return False, "location_not_eligible"
            # Candidate is Nigeria-eligible but job is on-site elsewhere.
            return False, "onsite_outside_nigeria"

    return True, ""
