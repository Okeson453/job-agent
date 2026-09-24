"""Outbound HTTP for discovery — allowlist enforced."""

from __future__ import annotations

import httpx

from src.security.allowlist import is_allowed


class AllowlistBlocked(RuntimeError):
    pass


async def allowed_get(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict | None = None,
) -> httpx.Response:
    if not is_allowed(url):
        raise AllowlistBlocked(f"URL not on allowlist: {url}")
    return await client.get(url, params=params)
