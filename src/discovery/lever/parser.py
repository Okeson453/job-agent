"""Parse Lever public postings API records into normalizer field names."""

from __future__ import annotations

from typing import Any


def parse(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract fields from a Lever job posting dict.

    Lever public API shape:
      id, text, categories{location, commitment, team, department},
      descriptionPlain / description, hostedUrl, createdAt, ...
    """
    categories = raw.get("categories") or {}
    location = categories.get("location") if isinstance(categories, dict) else None
    commitment = categories.get("commitment") if isinstance(categories, dict) else None

    description = (
        raw.get("descriptionPlain")
        or raw.get("description")
        or raw.get("content")
        or ""
    )

    return {
        "external_id": str(raw.get("id", "")),
        "title": str(raw.get("text") or raw.get("title") or "").strip(),
        "company": str(raw.get("company") or "").strip(),
        "description": str(description),
        "location": str(location).strip() if location else None,
        "remote": _is_remote(location, raw),
        "application_url": str(raw.get("hostedUrl") or raw.get("applyUrl") or ""),
        "employment_type": str(commitment) if commitment else None,
        "seniority": None,
        "created_at": raw.get("createdAt"),
    }


def _is_remote(location: str | None, raw: dict[str, Any]) -> bool:
    blob = f"{location or ''} {raw.get('text', '')} {raw.get('descriptionPlain', '')}".lower()
    return any(token in blob for token in ("remote", "work from home", "wfh", "anywhere"))
