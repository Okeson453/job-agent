from __future__ import annotations
from typing import Any

def parse(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "external_id": str(raw.get("external_id") or ""),
        "title": str(raw.get("title") or "").strip(),
        "company": str(raw.get("company") or "").strip(),
        "description": str(raw.get("description") or ""),
        "location": "Remote",
        "remote": True,
        "application_url": str(raw.get("application_url") or ""),
        "employment_type": "contract",
        "technologies": list(raw.get("technologies") or []),
    }
