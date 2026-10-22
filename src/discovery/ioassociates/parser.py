"""Parse iO Associates listing cards and job detail pages.

The listing is a Tailwind grid of ``<article>`` cards; each card links to
``/jobs/<slug>-<id>/``. Detail pages carry the full description in
``.jd-content`` plus a meta row (category, location, salary, employment type).
"""

from __future__ import annotations

import re
from typing import Any

from src.discovery.html import HTMLParser
from src.discovery.salary import normalize_employment_type, parse_annual_salary

COMPANY = "iO Associates"
_BASE = "https://www.ioassociates.co.uk"
_ID_PATTERN = re.compile(r"-(\d+)/?$")


def _clean(value: str | None) -> str:
    return " ".join((value or "").split())


def _card_link(card: Any) -> str | None:
    for anchor in card.css("a[href]"):
        href = anchor.attributes.get("href") or ""
        if "/jobs/" in href and "#" not in href:
            return href if href.startswith("http") else f"{_BASE}{href}"
    return None


def parse_card(card: Any) -> dict[str, Any] | None:
    """Turn one ``<article>`` node into a raw record."""
    url = _card_link(card)
    if not url:
        return None
    match = _ID_PATTERN.search(url.rstrip("/") + "/")
    external_id = match.group(1) if match else url

    title_node = card.css_first("h3")
    location_node = card.css_first("h4")
    salary_node = card.css_first("h5")
    title = _clean(title_node.text() if title_node else "")
    if not title:
        return None
    location = _clean(location_node.text() if location_node else "") or None
    salary_text = _clean(salary_node.text() if salary_node else "")

    snippet = ""
    for div in card.css("div"):
        cls = div.attributes.get("class") or ""
        if "overflow-hidden" in cls and "flex-1" in cls:
            snippet = _clean(div.text())
            break

    salary_min, salary_max, currency = parse_annual_salary(salary_text)
    remote = bool(location and "remote" in location.lower())

    return {
        "external_id": external_id,
        "title": title,
        "company": COMPANY,
        "location": location,
        "remote": remote,
        "salary_text": salary_text,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "salary_currency": currency,
        "description": snippet,
        "application_url": url,
    }


def parse_listing_html(html: str) -> list[dict[str, Any]]:
    tree = HTMLParser(html)
    cards = tree.css("main article") or tree.css("article")
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for card in cards:
        record = parse_card(card)
        if record is None or record["external_id"] in seen:
            continue
        seen.add(record["external_id"])
        results.append(record)
    return results


def parse_detail_html(html: str) -> dict[str, Any]:
    """Extract detail-level fields from a job page. Missing pieces are omitted."""
    tree = HTMLParser(html)
    details: dict[str, Any] = {}

    title_node = tree.css_first("h1")
    if title_node:
        title = _clean(title_node.text())
        if title:
            details["title"] = title

    description_node = tree.css_first(".jd-content")
    if description_node:
        text = description_node.text(separator="\n", strip=False)
        text = "\n".join(line.strip() for line in text.splitlines())
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if text:
            details["description"] = text

    # Meta row: category, location, salary, employment type. It is the only
    # container holding three or more h6 children; earlier headings in the hero
    # (location) must not be mistaken for it.
    meta: list[str] = []
    candidates: list[list[str]] = []
    for container in tree.css("div"):
        values = [
            _clean(child.text())
            for child in container.css("h6")
            if _clean(child.text())
        ]
        if 3 <= len(values) <= 5:
            candidates.append(values)
    if candidates:
        meta = min(candidates, key=len)
    if meta:
        for value in meta:
            lowered = value.lower()
            if any(
                token in lowered
                for token in ("permanent", "contract", "part time", "full time", "fixed term")
            ):
                details["employment_type"] = normalize_employment_type(value)
        # Location is the second meta entry on job pages; salary the third.
        if len(meta) >= 3:
            details.setdefault("location", meta[1])
            salary_min, salary_max, currency = parse_annual_salary(meta[2])
            if salary_min is not None:
                details["salary_min"] = salary_min
                details["salary_max"] = salary_max
                details["salary_currency"] = currency
            details.setdefault("salary_text", meta[2])

    details["remote"] = bool(
        "remote" in str(details.get("location", "")).lower()
        or "fully remote" in str(details.get("description", "")).lower()[:400]
    )
    return details


def parse(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalizer-facing shape."""
    return {
        "external_id": str(raw.get("external_id") or ""),
        "title": _clean(raw.get("title")),
        "company": _clean(raw.get("company")) or COMPANY,
        "description": str(raw.get("description") or ""),
        "location": raw.get("location"),
        "remote": bool(raw.get("remote", False)),
        "employment_type": raw.get("employment_type"),
        "salary_min": raw.get("salary_min"),
        "salary_max": raw.get("salary_max"),
        "salary_currency": raw.get("salary_currency"),
        "application_url": str(raw.get("application_url") or ""),
        "employer_apply_url": raw.get("employer_apply_url"),
        "technologies": [],
    }
