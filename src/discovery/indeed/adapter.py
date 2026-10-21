"""Indeed adapter — uses only permitted public/search endpoints.

No CAPTCHA bypass, no anti-bot evasion. If the endpoint requires human
verification, the adapter stops and surfaces the failure.
"""

from __future__ import annotations

import html
import os
import re
from typing import Any

import httpx

from src.discovery.http import AllowlistBlocked, allowed_get

from src.discovery.base import JobSource
from src.discovery.indeed.parser import parse
from src.jobs.normalizer.normalizer import register_parser
from src.observability.logging import get_logger

logger = get_logger(__name__)

_ITEM = re.compile(r"<item>(.*?)</item>", re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r"<([^>]+)>(.*?)</\1>", re.IGNORECASE | re.DOTALL)


def _strip_html(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_rss(xml: str) -> list[dict[str, Any]]:
    """Minimal RSS item parser — no external XML dependency."""
    items: list[dict[str, Any]] = []
    for block in _ITEM.findall(xml):
        fields = {m.group(1).lower(): m.group(2).strip() for m in _TAG.finditer(block)}
        title = _strip_html(fields.get("title") or "")
        desc = _strip_html(fields.get("description") or "")
        link = fields.get("link") or ""
        guid = fields.get("guid") or link
        # Company often appears as "Title - Company" or in source tag.
        company = _strip_html(fields.get("source") or "")
        if not company and " - " in title:
            parts = title.rsplit(" - ", 1)
            if len(parts) == 2:
                title, company = parts[0].strip(), parts[1].strip()
        location = ""
        loc_m = re.search(r"([A-Za-z .]+,\s*[A-Z]{2})\b", desc)
        if loc_m:
            location = loc_m.group(1)
        raw = {
            "jobkey": guid,
            "jobtitle": title,
            "company": company,
            "snippet": desc[:2000],
            "url": link,
            "location": location,
        }
        if raw["jobkey"] and raw["jobtitle"]:
            items.append(raw)
    return items


# Register parser so the normalizer can find it.
register_parser("indeed", parse)


class IndeedAdapter(JobSource):
    source_name = "indeed"
    default_poll_interval_minutes = 60
    rate_limit_per_minute = 5

    def __init__(self) -> None:
        self._query = os.environ.get("INDEED_QUERY", "backend engineer remote")
        self._location = os.environ.get("INDEED_LOCATION", "remote")

    async def discover(self) -> list[dict[str, Any]]:
        """Fetch from Indeed's public RSS/search where available.

        Indeed aggressively blocks automated access. On any block or CAPTCHA
        signal, return empty and log — never attempt to circumvent.
        """
        try:
            await self._acquire_rate_limit()
        except RuntimeError:
            return []
        # Public RSS-style endpoint (when available for a given query).
        url = "https://www.indeed.com/rss"
        params = {"q": self._query, "l": self._location}
        timeout = httpx.Timeout(20.0, connect=10.0)

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await allowed_get(client, url, params=params)
                if resp.status_code in (403, 429, 503):
                    logger.warning(
                        "indeed.blocked",
                        status=resp.status_code,
                        reason="access restricted; no bypass attempted",
                    )
                    return []
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "")
                if "json" in content_type:
                    data = resp.json()
                    items = data if isinstance(data, list) else data.get("results", [])
                    return [parse(item) for item in items if item]
                if "xml" in content_type or "rss" in content_type or resp.text.lstrip().startswith("<"):
                    return _parse_rss(resp.text)
                logger.info("indeed.non_json_response", content_type=content_type)
                return []
        except (httpx.HTTPError, AllowlistBlocked) as exc:
            logger.error("indeed.discover.error", error=str(exc))
            return []
