"""Parse LinkedIn listing records into normalizer field names."""

from __future__ import annotations

from typing import Any


def parse(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "external_id": str(raw.get("id") or raw.get("jobPostingId") or ""),
        "title": str(raw.get("title") or "").strip(),
        "company": str(
            (raw.get("companyDetails") or {}).get("companyName")
            or raw.get("company")
            or ""
        ).strip(),
        "description": str(raw.get("description") or raw.get("jobDescription") or ""),
        "location": str(raw.get("formattedLocation") or raw.get("location") or "") or None,
        "remote": bool(raw.get("workRemoteAllowed") or "remote" in str(raw.get("title", "")).lower()),
        "application_url": str(raw.get("jobPostingUrl") or raw.get("url") or ""),
        "employment_type": raw.get("employmentStatus"),
        "seniority": raw.get("experienceLevel"),
    }
