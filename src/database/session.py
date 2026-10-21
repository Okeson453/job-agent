"""Async engine and session factory.

Pool size and overflow are controlled by environment variables so the API
process can use a small pool while the worker process uses a larger one.

asyncpg does not accept the libpq ``sslmode`` query parameter as a keyword
argument. Railway (and many hosts) append ``?sslmode=require`` to DATABASE_URL;
we strip those params and pass an SSL context via connect_args instead.
"""

from __future__ import annotations

import os
import ssl
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _normalize_database_url(database_url: str) -> tuple[str, dict]:
    """Return (asyncpg-compatible URL, connect_args) with SSL handled for asyncpg."""
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    parsed = urlparse(database_url)
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    sslmode: str | None = None
    kept: list[tuple[str, str]] = []
    for key, value in query_pairs:
        low = key.lower()
        if low in ("sslmode", "ssl"):
            sslmode = value
        else:
            kept.append((key, value))

    clean = urlunparse(parsed._replace(query=urlencode(kept)))
    connect_args: dict = {}

    if sslmode is not None:
        mode = sslmode.strip().lower()
        if mode in ("0", "false", "disable", "disabled"):
            connect_args["ssl"] = False
        elif mode in ("1", "true", "require", "prefer", "verify-ca", "verify-full"):
            ctx = ssl.create_default_context()
            # Managed providers often present certs that fail strict hostname checks
            # in container environments; require encryption without pinning CA chain.
            if mode in ("require", "prefer", "1", "true"):
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            connect_args["ssl"] = ctx
    else:
        # Heuristic: non-local hosts typically need TLS (Railway, Neon, RDS, …)
        host = (parsed.hostname or "").lower()
        if host and host not in ("localhost", "127.0.0.1", "::1") and not host.endswith(
            ".local"
        ):
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            connect_args["ssl"] = ctx

    return clean, connect_args


def _build_engine() -> AsyncEngine:
    try:
        from src.security.secrets import get_secret

        database_url = get_secret("DATABASE_URL")
    except Exception:
        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://jobagent:jobagent@localhost:5432/jobagent",
        )

    database_url, connect_args = _normalize_database_url(database_url)

    pool_size = int(os.environ.get("DB_POOL_SIZE", "5"))
    max_overflow = int(os.environ.get("DB_MAX_OVERFLOW", "10"))

    return create_async_engine(
        database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args=connect_args,
        echo=os.environ.get("DB_ECHO", "").lower() in ("1", "true", "yes"),
    )


def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, creating it on first call."""
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession that commits on clean exit and rolls back on error."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def close_engine() -> None:
    """Dispose the engine and clear process-level globals. Called on shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
