from __future__ import annotations
from typing import Any

def parse(raw: dict[str, Any]) -> dict[str, Any]:
    rid = raw.get("id") or raw.get("slug") or ""
    tags = raw.get("tags") or []
    location = str(raw.get("location") or "")
    desc = str(raw.get("description") or raw.get("html") or "")
    company = str(raw.get("company") or "").strip()
    title = str(raw.get("position") or raw.get("title") or "").strip()
    url = str(raw.get("url") or raw.get("apply_url") or "")
    if url and not url.startswith("http"):
        url = f"https://remoteok.com/l/{rid}" if rid else url
    if not url and rid:
        url = f"https://remoteok.com/remote-jobs/{rid}"
    return {
        "external_id": str(rid),
        "title": title,
        "company": company,
        "description": desc,
        "location": location or "Remote",
        "remote": True,
        "application_url": url,
        "employment_type": None,
        "technologies": [str(t) for t in tags] if isinstance(tags, list) else [],
        "salary_min": raw.get("salary_min"),
        "salary_max": raw.get("salary_max"),
        "salary_currency": "USD" if raw.get("salary_min") or raw.get("salary_max") else None,
    }
