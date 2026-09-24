"""Normalize source-specific raw dicts into JobCreate.

This is the only place a Job object is constructed from raw source data.
"""

from __future__ import annotations

from typing import Any, Callable

from src.discovery.greenhouse.parser import parse as greenhouse_parse
from src.discovery.lever.parser import parse as lever_parse
from src.jobs.parser.description_parser import extract
from src.jobs.schemas import JobCreate
from src.observability.logging import get_logger

logger = get_logger(__name__)

def _coerce_seniority(value: object) -> str | None:
    """Normalize source-specific seniority shapes to str | None."""
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
        return ", ".join(dict.fromkeys(values)) or None
    return str(value).strip() or None



_PARSERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "greenhouse": greenhouse_parse,
    "lever": lever_parse,
}


def register_parser(source: str, parser: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
    """Allow additional source parsers to register at import time."""
    _PARSERS[source] = parser


def normalize(source: str, raw: dict[str, Any]) -> JobCreate:
    """Call the matching source parser, run description extraction, assemble JobCreate."""
    parser = _PARSERS.get(source)
    if parser is None:
        # Generic passthrough for sources that already emit normalizer-shaped dicts.
        fields = dict(raw)
    else:
        fields = parser(raw)

    description = str(fields.get("description") or "")
    extracted = extract(description)

    technologies = list(fields.get("technologies") or [])
    for t in extracted.get("technologies") or []:
        if t not in technologies:
            technologies.append(t)

    seniority = _coerce_seniority(fields.get("seniority") or extracted.get("seniority"))
    salary = extracted.get("salary")

    salary_min = fields.get("salary_min")
    salary_max = fields.get("salary_max")
    salary_currency = fields.get("salary_currency")
    if salary is not None:
        salary_min = salary_min if salary_min is not None else salary.min
        salary_max = salary_max if salary_max is not None else salary.max
        salary_currency = salary_currency or salary.currency

    application_url = str(fields.get("application_url") or "").strip()
    if not application_url:
        raise ValueError(f"Job from {source} missing application_url")

    external_id = str(fields.get("external_id") or "").strip()
    if not external_id:
        raise ValueError(f"Job from {source} missing external_id")

    title = str(fields.get("title") or "").strip()
    company = str(fields.get("company") or "").strip()
    if not title or not company:
        raise ValueError(f"Job from {source} missing title or company")

    return JobCreate(
        source=source,
        external_id=external_id,
        title=title,
        company=company,
        description=description,
        location=fields.get("location"),
        remote=bool(fields.get("remote", False)),
        countries=fields.get("countries"),
        employment_type=fields.get("employment_type"),
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
        seniority=seniority,
        technologies=technologies or None,
        application_url=application_url,
    )
