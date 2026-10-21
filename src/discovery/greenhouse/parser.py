"""Parse Greenhouse public job-board API records into normalizer field names."""

from __future__ import annotations

from typing import Any


def parse(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract title/company/description/location/etc. from a Greenhouse job dict.

    Greenhouse public board API shape (simplified):
      id, title, absolute_url, location{name}, updated_at, content, ...
    """
    location_obj = raw.get("location") or {}
    location_name = (
        location_obj.get("name") if isinstance(location_obj, dict) else str(location_obj or "")
    )

    departments = raw.get("departments") or []
    dept_names = [
        d.get("name", "") for d in departments if isinstance(d, dict)
    ]

    return {
        "external_id": str(raw.get("id", "")),
        "title": str(raw.get("title", "")).strip(),
        "company": str(raw.get("company_name") or raw.get("company") or "").strip(),
        "description": str(raw.get("content") or raw.get("description") or ""),
        "location": location_name.strip() if location_name else None,
        "remote": _is_remote(location_name, raw),
        "application_url": str(raw.get("absolute_url") or raw.get("url") or ""),
        "employment_type": None,
        "seniority": None,
        "departments": dept_names,
        "updated_at": raw.get("updated_at"),
    }


def _is_remote(location: str | None, raw: dict[str, Any]) -> bool:
    blob = f"{location or ''} {raw.get('title', '')} {raw.get('content', '')}".lower()
    return any(
        token in blob
        for token in ("remote", "work from home", "wfh", "anywhere")
    )
