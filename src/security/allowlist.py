"""Domain allowlist for browser navigation and discovery HTTP (Section 20).

Playwright route interception and discovery adapters use is_allowed() to
block hosts outside the configured set. ALLOWED_DOMAINS is comma-separated
hostnames (no scheme or path).

Built-in discovery API hosts are always permitted so a stale Railway env
value cannot break source polling.
"""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlparse

from src.security.secrets import get_secret

_BUILTIN_DISCOVERY_HOSTS: frozenset[str] = frozenset(
    {
        "boards-api.greenhouse.io",
        "boards.greenhouse.io",
        "api.lever.co",
        "jobs.lever.co",
        "remoteok.com",
        "www.remoteok.com",
        "himalayas.app",
        "www.himalayas.app",
        "wellfound.com",
        "www.wellfound.com",
        "www.workatastartup.com",
        "workatastartup.com",
        "www.linkedin.com",
        "linkedin.com",
        "www.indeed.com",
        "indeed.com",
        "www.welcometothejungle.com",
        "welcometothejungle.com",
        "arc.dev",
        "www.arc.dev",
        "contra.com",
        "www.contra.com",
        "stripe.com",
        "www.stripe.com",
        "vercel.com",
        "www.vercel.com",
        "www.cloudflare.com",
        "cloudflare.com",
    }
)


@lru_cache(maxsize=1)
def _allowed_hosts() -> frozenset[str]:
    raw = get_secret("ALLOWED_DOMAINS")
    hosts = {h.strip().lower() for h in raw.split(",") if h.strip()}
    return frozenset(hosts) | _BUILTIN_DISCOVERY_HOSTS


def is_allowed(url: str) -> bool:
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
    for domain in allowed:
        if host.endswith("." + domain):
            return True
    return False


def get_allowed_domains() -> frozenset[str]:
    return _allowed_hosts()


def reset_allowlist_cache() -> None:
    _allowed_hosts.cache_clear()
