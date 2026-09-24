"""Unit tests for domain allowlist."""

from __future__ import annotations

import os

# Ensure secrets are set before import.
os.environ["DATABASE_URL"] = "postgresql+asyncpg://x:x@localhost/x"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["TELEGRAM_BOT_TOKEN"] = "t"
os.environ["TELEGRAM_CHAT_ID"] = "0"
os.environ["ENCRYPTION_KEY"] = "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlcyEhIQ=="
os.environ["ALLOWED_DOMAINS"] = (
    "boards-api.greenhouse.io,boards.greenhouse.io,"
    "api.lever.co,jobs.lever.co,www.linkedin.com,www.indeed.com"
)

from src.security.secrets import reload_secrets
from src.security.allowlist import is_allowed, reset_allowlist_cache

reload_secrets()
reset_allowlist_cache()


class TestAllowlist:
    def setup_method(self) -> None:
        os.environ["ALLOWED_DOMAINS"] = (
            "boards-api.greenhouse.io,boards.greenhouse.io,"
            "api.lever.co,jobs.lever.co,www.linkedin.com,www.indeed.com"
        )
        reload_secrets()
        reset_allowlist_cache()

    def test_allowed_domain(self) -> None:
        assert is_allowed("https://boards.greenhouse.io/acme/jobs/123") is True
        assert is_allowed("https://boards-api.greenhouse.io/v1/boards/stripe/jobs") is True
        assert is_allowed("https://api.lever.co/v0/postings/shopify") is True

    def test_allowed_subdomain(self) -> None:
        assert is_allowed("https://jobs.lever.co/company/abc") is True

    def test_blocked_domain(self) -> None:
        assert is_allowed("https://evil.example.com/phish") is False

    def test_blocked_unrelated(self) -> None:
        assert is_allowed("https://www.google.com/") is False

    def test_invalid_url(self) -> None:
        assert is_allowed("not-a-url") is False
        assert is_allowed("") is False
