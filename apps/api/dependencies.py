"""FastAPI dependency providers."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

from fastapi import Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_session_factory
from src.scheduler.queues import get_redis
from src.security.secrets import get_secret


async def get_db_session() -> AsyncIterator[AsyncSession]:
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


async def get_redis_dep():
    return await get_redis()


def get_current_config() -> dict[str, str]:
    return {
        "application_mode": get_secret("APPLICATION_MODE_DEFAULT"),
        "match_threshold": get_secret("MATCH_THRESHOLD"),
        "browser_concurrency": get_secret("BROWSER_WORKER_CONCURRENCY"),
    }


async def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """Optional API key gate.

    If API_KEY is unset/empty, auth is disabled (local/dev).
    If set, every non-health request must send matching X-API-Key.
    """
    try:
        expected = (get_secret("API_KEY") or "").strip()
    except Exception:
        expected = os.environ.get("API_KEY", "").strip()
    env = os.environ.get("APP_ENV", os.environ.get("ENVIRONMENT", "development")).lower()
    if not expected:
        if env in ("production", "prod", "staging"):
            raise HTTPException(
                status_code=503,
                detail="API_KEY must be configured in production",
            )
        return
    if not x_api_key or x_api_key.strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
