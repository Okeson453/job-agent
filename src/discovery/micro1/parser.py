"""Parse micro1 opportunity cards.

micro1 gates its opportunity list behind an expert login, so the public page
usually renders navigation only. If cards do appear, they are anchors whose
path continues past ``/experts/opportunities/``.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from src.discovery.html import HTMLParser

COMPANY = "micro1"
_BASE = "https://www.micro1.ai"
_RESERVED = {"", "experts", "opportunities", "login", "refer", "reviews"}


def _clean(value: str | None) -> str:
    return " ".join((value or "").split())


def _is_opportunity_link(href: str) -> bool:
    path = urlparse(href).path.rstrip("/")
    parts = [part for part in path.split("/") if part]
    if len(parts) < 3 or parts[0] != "experts" or parts[1] != "opportunities":
        return False
    return parts[-1].lower() not in _RESERVED


def parse_listing_html(html: str) -> list[dict[str, Any]]:
    tree = HTMLParser(html)
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for anchor in tree.css("a[href]"):
        href = (anchor.attributes.get("href") or "").strip()
        if not _is_opportunity_link(href):
            continue
        url = href if href.startswith("http") else f"{_BASE}{href}"
        title = _clean(anchor.text())
        if not title or len(title) > 200:
            continue
        external_id = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
        if external_id in seen:
            continue
        seen.add(external_id)
        results.append(
            {
                "external_id": external_id,
                "title": title,
                "company": COMPANY,
                "description": "",
                "location": None,
                "remote": False,
                "employment_type": None,
                "application_url": url,
            }
        )
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
