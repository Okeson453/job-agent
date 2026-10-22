"""Parse Turing job cards.

Turing renders cards client-side as ``<article data-job-card-id>``. There is no
per-job href; the canonical route is ``/jobs?jobId=<id>``. Detail content is
only available to signed-in users, so description is the card summary and the
listing URL is always included for the user to read the full post.
"""

from __future__ import annotations

from typing import Any

from src.discovery.html import HTMLParser

COMPANY = "Turing"
_BASE = "https://work.turing.com/jobs"


def _clean(value: str | None) -> str:
    return " ".join((value or "").split())


def parse_card(card: Any) -> dict[str, Any] | None:
    job_id = _clean(card.attributes.get("data-job-card-id"))
    if not job_id:
        return None
    title_node = card.css_first("h3")
    title = _clean(title_node.text() if title_node else "")
    if not title:
        return None
    description_node = card.css_first("p")
    description = _clean(description_node.text() if description_node else "")

    return {
        "external_id": job_id,
        "title": title,
        "company": COMPANY,
        "description": description,
        "location": None,
        "remote": False,
        "employment_type": None,
        "application_url": f"{_BASE}?jobId={job_id}",
    }


def parse_listing_html(html: str) -> list[dict[str, Any]]:
    tree = HTMLParser(html)
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for card in tree.css("article[data-job-card-id]"):
        record = parse_card(card)
        if record is None or record["external_id"] in seen:
            continue
        seen.add(record["external_id"])
        results.append(record)
    return results


def parse(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "external_id": str(raw.get("external_id") or ""),
        "title": _clean(raw.get("title")),
        "company": _clean(raw.get("company")) or COMPANY,
        "description": str(raw.get("description") or ""),
        "location": raw.get("location"),
        "remote": bool(raw.get("remote", False)),
        "employment_type": raw.get("employment_type"),
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "application_url": str(raw.get("application_url") or ""),
        "employer_apply_url": raw.get("employer_apply_url"),
        "technologies": [],
    }
