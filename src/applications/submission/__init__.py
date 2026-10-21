"""ATS submission and result tracking."""

from src.applications.submission.ats_client import submit_via_api
from src.applications.submission.tracker import record_result

__all__ = ["record_result", "submit_via_api"]
