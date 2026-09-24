"""Parse Indeed listing records into normalizer field names."""

from __future__ import annotations

from typing import Any


def parse(raw: dict[str, Any]) -> dict[str, Any]:
    location = str(raw.get("location") or raw.get("formattedLocation") or "")
    return {
        "external_id": str(raw.get("jobkey") or raw.get("id") or ""),
        "title": str(raw.get("jobtitle") or raw.get("title") or "").strip(),
        "company": str(raw.get("company") or "").strip(),
        "description": str(raw.get("snippet") or raw.get("description") or ""),
        "location": location or None,
        "remote": "remote" in location.lower() if location else False,
        "application_url": str(raw.get("url") or raw.get("link") or ""),
        "employment_type": raw.get("formattedRelativeTime"),
        "seniority": None,
    }
