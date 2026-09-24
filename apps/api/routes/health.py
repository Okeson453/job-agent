"""Health and readiness endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from sqlalchemy import text

from src.database.session import get_engine
from src.scheduler.queues import get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Process liveness — no dependency checks."""
    return {"status": "ok"}


@router.get("/health/ready")
async def ready() -> dict[str, str]:
    """Readiness: DB and Redis connectivity with 1s timeout each."""
    errors: list[str] = []

    try:
        engine = get_engine()
        async with asyncio.timeout(1.0):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
    except Exception as exc:
        errors.append(f"db: {exc}")

    try:
        async with asyncio.timeout(1.0):
            client = await get_redis()
            await client.ping()
    except Exception as exc:
        errors.append(f"redis: {exc}")

    if errors:
        from fastapi.responses import JSONResponse

        return JSONResponse(  # type: ignore[return-value]
            status_code=503,
            content={"status": "not_ready", "errors": errors},
        )
    return {"status": "ready"}
