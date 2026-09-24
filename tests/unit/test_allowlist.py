"""Unit tests for domain allowlist."""

from __future__ import annotations

import os

# Ensure secrets are set before import.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "t")
os.environ.setdefault("TELEGRAM_CHAT_ID", "0")
os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlcyEhIQ==")
os.environ.setdefault(
    "ALLOWED_DOMAINS",
    "boards.greenhouse.io,jobs.lever.co,www.linkedin.com,www.indeed.com",
)

from src.security.allowlist import is_allowed, reset_allowlist_cache


class TestAllowlist:
    def setup_method(self) -> None:
        reset_allowlist_cache()

    def test_allowed_domain(self) -> None:
        assert is_allowed("https://boards.greenhouse.io/acme/jobs/123") is True

    def test_allowed_subdomain(self) -> None:
        # jobs.lever.co is listed; subdomain of listed host
        assert is_allowed("https://jobs.lever.co/company/abc") is True

    def test_blocked_domain(self) -> None:
        assert is_allowed("https://evil.example.com/phish") is False

    def test_blocked_unrelated(self) -> None:
        assert is_allowed("https://www.google.com/") is False

    def test_invalid_url(self) -> None:
        assert is_allowed("not-a-url") is False
        assert is_allowed("") is False
