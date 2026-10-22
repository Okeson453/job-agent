"""Salary text parsing for discovery sources.

Only annual figures are returned as ``salary_min``/``salary_max``. Hourly and
daily rates stay in the description text: the job record has no pay-period
field, and storing an hourly rate as an annual salary would misrepresent the
opportunity.
"""

from __future__ import annotations

import re

_CURRENCIES = {"£": "GBP", "$": "USD", "€": "EUR", "₦": "NGN"}

_AMOUNT = r"(?P<lo>\d[\d,]*(?:\.\d+)?)\s*(?P<lok>[kK])?"
_AMOUNT_HI = r"(?P<hi>\d[\d,]*(?:\.\d+)?)\s*(?P<hik>[kK])?"

_RANGE = re.compile(
    rf"(?P<cur>[£$€₦])?\s*{_AMOUNT}"
    rf"(?:\s*(?:-|–|—|to)\s*(?P<cur2>[£$€₦])?\s*{_AMOUNT_HI})?",
)

_HOURLY = re.compile(r"\b(per\s+hour|/\s*h(?:r|our)?|hourly|per\s+day|daily|/day)\b", re.I)
_ANNUAL = re.compile(r"\b(per\s+year|per\s+annum|/\s*yr|/\s*year|annual(?:ly)?|p\.?a\.?)\b", re.I)


def _to_int(amount: str, suffix: str | None, *, annual_hint: bool) -> int | None:
    try:
        value = float(amount.replace(",", ""))
    except ValueError:
        return None
    if suffix:
        value *= 1000
    elif annual_hint and value < 1000:
        value *= 1000
    return int(value)


def parse_annual_salary(text: str | None) -> tuple[int | None, int | None, str | None]:
    """Return (min, max, currency) for annual salaries, else (None, None, None)."""
    if not text:
        return (None, None, None)
    cleaned = " ".join(text.split())
    if _HOURLY.search(cleaned) and not _ANNUAL.search(cleaned):
        return (None, None, None)

    annual_hint = bool(_ANNUAL.search(cleaned))
    match = _RANGE.search(cleaned)
    if not match:
        return (None, None, None)

    currency = match.group("cur") or match.group("cur2")
    low = _to_int(match.group("lo"), match.group("lok"), annual_hint=annual_hint)
    high = (
        _to_int(match.group("hi"), match.group("hik"), annual_hint=annual_hint)
        if match.group("hi")
        else None
    )

    if low is None:
        return (None, None, None)
    # A bare small number with no currency/year context is not a salary figure.
    if not annual_hint and not currency and low < 1000:
        return (None, None, None)
    if not annual_hint and low < 1000:
        return (None, None, None)

    return (low, high, _CURRENCIES.get(currency or "", None))


def normalize_employment_type(text: str | None) -> str | None:
    if not text:
        return None
    lowered = text.strip().lower()
    mapping = {
        "permanent": "full_time",
        "full time": "full_time",
        "full-time": "full_time",
        "fulltime": "full_time",
        "part time": "part_time",
        "part-time": "part_time",
        "contract": "contract",
        "contractor": "contract",
        "fixed term": "contract",
        "temporary": "temporary",
        "internship": "internship",
        "intern": "internship",
        "freelance": "contract",
    }
    for key, value in mapping.items():
        if key in lowered:
            return value
    return lowered or None
