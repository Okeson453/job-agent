"""Parse Wellfound listing records into normalizer field names."""

from __future__ import annotations

from typing import Any


def parse(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "external_id": str(raw.get("id") or ""),
        "title": str(raw.get("title") or "").strip(),
        "company": str(
            (raw.get("startup") or {}).get("name") or raw.get("company") or ""
        ).strip(),
        "description": str(raw.get("description") or ""),
        "location": str(raw.get("location") or "") or None,
        "remote": bool(raw.get("remote") or False),
        "application_url": str(raw.get("url") or raw.get("apply_url") or ""),
        "employment_type": raw.get("job_type"),
        "seniority": None,
    }
