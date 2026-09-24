"""Domain allowlist for browser navigation (Section 20).

Playwright route interception uses is_allowed() to block any navigation
outside the configured set. The list is loaded from ALLOWED_DOMAINS env
(comma-separated hostnames, no scheme or path).
"""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlparse

from src.security.secrets import get_secret


@lru_cache(maxsize=1)
def _allowed_hosts() -> frozenset[str]:
    raw = get_secret("ALLOWED_DOMAINS")
    hosts = {h.strip().lower() for h in raw.split(",") if h.strip()}
    return frozenset(hosts)


def is_allowed(url: str) -> bool:
    """Return True if the URL's hostname is on the allowlist.

    Subdomains of an allowed host are permitted (e.g. jobs.example.com
    matches when example.com is listed). Invalid URLs return False.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    allowed = _allowed_hosts()
    if host in allowed:
        return True
    # Permit subdomains of an allowed registrable domain.
    for domain in allowed:
        if host.endswith("." + domain):
            return True
    return False


def get_allowed_domains() -> frozenset[str]:
    """Return the current allowlist (for diagnostics / tests)."""
    return _allowed_hosts()


def reset_allowlist_cache() -> None:
    """Clear the cached allowlist. Intended for tests only."""
    _allowed_hosts.cache_clear()
