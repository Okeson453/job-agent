"""Parse ExpertWoka opportunity cards and detail pages.

ExpertWoka is server-rendered, so listings and details are fetched with plain
HTTP. Cards expose company, title, location, work type, compensation, tags and
posting date. Detail pages add the full description, skill tags and, when the
employer publishes one, the external application link.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from src.discovery.html import HTMLParser
from src.discovery.salary import normalize_employment_type, parse_annual_salary

_BASE = "https://expertwoka.com"
_MAX_JD_CHARS = 12000


def _clean(value: str | None) -> str:
    return " ".join((value or "").split())


def _external_id(href: str) -> str:
    path = urlparse(href).path.rstrip("/")
    return path.rsplit("/", 1)[-1] or href


def _work_type(card: Any) -> str | None:
    meta_spans = card.css(".ew-opportunity-meta span")
    for span in meta_spans:
        text = _clean(span.text())
        if text.lower() in ("remote", "hybrid", "on-site", "onsite"):
            return text
    return None


def parse_card(card: Any) -> dict[str, Any] | None:
    href = (card.attributes.get("href") or "").strip()
    if not href:
        return None
    url = href if href.startswith("http") else f"{_BASE}{href}"

    title_node = card.css_first(".ew-opportunity-title h3") or card.css_first("h3")
    title = _clean(title_node.text() if title_node else "")
    if not title:
        return None

    company_node = card.css_first(".ew-opportunity-company span")
    company = _clean(company_node.text() if company_node else "") or "ExpertWoka"
    location_node = card.css_first("[data-eligibility]")
    location = _clean(location_node.text() if location_node else "") or None
    salary_node = card.css_first(".ew-opportunity-salary")
    salary_text = _clean(salary_node.text() if salary_node else "")
    salary_min, salary_max, currency = parse_annual_salary(salary_text)
    work_type = _work_type(card)
    tags = [_clean(tag.text()) for tag in card.css(".ew-tag") if _clean(tag.text())]
    posted_node = card.css_first("time[datetime]")

    return {
        "external_id": _external_id(url),
        "title": title,
        "company": company,
        "description": "",
        "location": location,
        "remote": (work_type or "").lower() == "remote",
        "work_type": work_type,
        "salary_text": salary_text,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "salary_currency": currency,
        "technologies": tags,
        "posted_at": posted_node.attributes.get("datetime") if posted_node else None,
        "application_url": url,
    }


def parse_listing_html(html: str) -> list[dict[str, Any]]:
    tree = HTMLParser(html)
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for card in tree.css("a.ew-opportunity-card"):
        record = parse_card(card)
        if record is None or record["external_id"] in seen:
            continue
        seen.add(record["external_id"])
        results.append(record)
    return results


def _stat_map(tree: Any) -> dict[str, str]:
    stats: dict[str, str] = {}
    for stat in tree.css(".ew-job-stat"):
        label_node = stat.css_first(".ew-job-stat-label")
        value_node = stat.css_first(".ew-job-stat-value")
        if label_node and value_node:
            stats[_clean(label_node.text()).lower()] = _clean(value_node.text())
    return stats


def parse_detail_html(html: str) -> dict[str, Any]:
    tree = HTMLParser(html)
    details: dict[str, Any] = {}

    title_node = tree.css_first(".ew-job-title") or tree.css_first("h1")
    if title_node:
        title = _clean(title_node.text())
        if title:
            details["title"] = title

    company_node = tree.css_first(".ew-job-company-link")
    if company_node:
        company = _clean(company_node.text())
        if company:
            details["company"] = company

    description_node = tree.css_first(".ew-job-description")
    if description_node:
        text = description_node.text(separator="\n", strip=False)
        text = "\n".join(line.strip() for line in text.splitlines())
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if text:
            details["description"] = text[:_MAX_JD_CHARS]

    stats = _stat_map(tree)
    if stats.get("location"):
        details["location"] = stats["location"]
    if stats.get("work type"):
        details["remote"] = stats["work type"].lower() == "remote"
        details["work_type"] = stats["work type"]
    if stats.get("compensation"):
        salary_min, salary_max, currency = parse_annual_salary(stats["compensation"])
        details["salary_text"] = stats["compensation"]
        if salary_min is not None:
            details["salary_min"] = salary_min
            details["salary_max"] = salary_max
            details["salary_currency"] = currency

    skills = [
        _clean(node.text())
        for node in tree.css(".ew-job-skills .ew-job-tag")
        if _clean(node.text())
    ]
    if skills:
        existing = details.get("technologies") or []
        details["technologies"] = list(dict.fromkeys([*existing, *skills]))

    apply_node = tree.css_first("a.ew-job-apply[href]")
    if apply_node:
        href = (apply_node.attributes.get("href") or "").strip()
        if href.startswith("http") and "expertwoka.com" not in href:
            details["employer_apply_url"] = href

    description_lower = str(details.get("description", "")).lower()
    for token, value in (
        ("full-time", "full_time"),
        ("full time", "full_time"),
        ("part-time", "part_time"),
        ("internship", "internship"),
        ("contract", "contract"),
    ):
        if token in description_lower:
            details["employment_type"] = normalize_employment_type(value)
            break

    return details


def parse(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "external_id": str(raw.get("external_id") or ""),
        "title": _clean(raw.get("title")),
        "company": _clean(raw.get("company")) or "ExpertWoka",
        "description": str(raw.get("description") or ""),
        "location": raw.get("location"),
        "remote": bool(raw.get("remote", False)),
        "employment_type": raw.get("employment_type"),
        "salary_min": raw.get("salary_min"),
        "salary_max": raw.get("salary_max"),
        "salary_currency": raw.get("salary_currency"),
        "application_url": str(raw.get("application_url") or ""),
        "employer_apply_url": raw.get("employer_apply_url"),
        "technologies": list(raw.get("technologies") or []),
    }
