"""Discovery HTTP allowlist gate."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "t")
os.environ.setdefault("TELEGRAM_CHAT_ID", "0")
os.environ.setdefault("ENCRYPTION_KEY", "QUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUE=")
os.environ.setdefault(
    "ALLOWED_DOMAINS", "boards-api.greenhouse.io,boards.greenhouse.io,api.lever.co,jobs.lever.co"
)

from src.discovery.http import AllowlistBlocked, allowed_get
from src.security.allowlist import reset_allowlist_cache
from src.security.secrets import reload_secrets


class TestDiscoveryAllowlist:
    def setup_method(self) -> None:
        reload_secrets()
        reset_allowlist_cache()

    def test_unknown_host_blocked_sync_check(self) -> None:
        from src.security.allowlist import is_allowed

        assert is_allowed("https://boards.greenhouse.io/x") is True
        assert is_allowed("https://evil.example/jobs") is False
