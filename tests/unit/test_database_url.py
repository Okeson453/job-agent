"""DATABASE_URL normalization for asyncpg (sslmode handling)."""

from __future__ import annotations

import ssl

from src.database.session import _normalize_database_url


def test_strips_sslmode_require() -> None:
    url, args = _normalize_database_url(
        "postgres://u:p@host.example.com:5432/db?sslmode=require"
    )
    assert url.startswith("postgresql+asyncpg://")
    assert "sslmode" not in url
    assert isinstance(args.get("ssl"), ssl.SSLContext)


def test_localhost_no_forced_ssl() -> None:
    url, args = _normalize_database_url(
        "postgresql://u:p@localhost:5432/db"
    )
    assert "+asyncpg" in url
    assert args.get("ssl") in (None, False) or "ssl" not in args


def test_remote_heuristic_enables_ssl() -> None:
    _, args = _normalize_database_url(
        "postgresql://u:p@db.railway.app:5432/db"
    )
    assert isinstance(args.get("ssl"), ssl.SSLContext)
