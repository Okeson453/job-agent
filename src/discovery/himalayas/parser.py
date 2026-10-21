from __future__ import annotations
from typing import Any

def _normalize_seniority(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        values = [
            str(item).strip()
            for item in value
            if item is not None and str(item).strip()
        ]
        # preserve order, drop dups
        return ", ".join(dict.fromkeys(values)) or None
    return str(value).strip() or None


def parse(raw: dict[str, Any]) -> dict[str, Any]:
    rid = (
        raw.get("id")
        or raw.get("slug")
        or raw.get("guid")
        or raw.get("applicationLink")
        or ""
    )
    title = str(raw.get("title") or raw.get("name") or "").strip()
    company_obj = raw.get("company")
    if isinstance(company_obj, dict):
        company = str(company_obj.get("name") or company_obj.get("title") or "").strip()
    else:
        company = str(
            company_obj or raw.get("companyName") or raw.get("companySlug") or ""
        ).strip()
    desc = str(raw.get("description") or raw.get("excerpt") or "")
    loc = raw.get("location") or raw.get("locations") or raw.get("locationRestrictions") or "Remote"
    if isinstance(loc, list):
        loc = ", ".join(str(x) for x in loc) if loc else "Remote"
    url = str(
        raw.get("applicationLink")
        or raw.get("url")
        or raw.get("guid")
        or ""
    )
    if not url:
        slug = raw.get("slug") or rid
        url = f"https://himalayas.app/jobs/{slug}" if slug else ""
    emp = raw.get("employmentType") or raw.get("type")
    if isinstance(emp, list):
        emp = ", ".join(str(x) for x in emp)
    tags = raw.get("categories") or raw.get("skills") or raw.get("parentCategories") or []
    if not isinstance(tags, list):
        tags = []
    if not rid:
        rid = f"{company}-{title}".lower().replace(" ", "-")[:80]
    return {
        "external_id": str(rid),
        "title": title,
        "company": company or "Unknown",
        "description": desc,
        "location": str(loc),
        "remote": True,
        "application_url": url,
        "employment_type": str(emp) if emp else None,
        "technologies": [str(t) for t in tags],
        "salary_min": raw.get("minSalary"),
        "salary_max": raw.get("maxSalary"),
        "salary_currency": raw.get("currency"),
        "seniority": _normalize_seniority(raw.get("seniority")),
    }
