"""Health, readiness, and worker heartbeat endpoints."""

from __future__ import annotations

import asyncio
import time

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


@router.get("/health/workers")
async def workers() -> dict:
    """Worker loop heartbeat + queue depths + pause flag."""
    data: dict = {"status": "ok", "paused": False, "ticks": {}, "queues": {}, "dlq": {}}
    try:
        client = await get_redis()
        paused = await client.get("system:paused")
        data["paused"] = paused in (b"1", "1", 1, True)
        for name in (
            "discovery",
            "matching",
            "llm",
            "application",
            "browser",
            "notification",
        ):
            raw = await client.get(f"worker:{name}:beat")
            if raw is not None:
                try:
                    data["ticks"][name] = int(raw)
                except (TypeError, ValueError):
                    data["ticks"][name] = str(raw)
        for q in (
            "discovery_queue",
            "analysis_queue",
            "llm_queue",
            "application_queue",
            "browser_queue",
            "notification_queue",
        ):
            data["queues"][q] = await client.llen(q)
            data["dlq"][q] = await client.llen(f"{q}:dlq")
        now = int(time.time())
        stale = [
            n for n, ts in data["ticks"].items()
            if isinstance(ts, int) and now - ts > 1800
        ]
        data["stale_loops"] = stale
        if stale:
            data["status"] = "degraded"
    except Exception as exc:
        data["status"] = "error"
        data["error"] = str(exc)
    return data
