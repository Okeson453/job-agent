"""Pause / resume control endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from src.scheduler.queues import is_system_paused, set_system_paused

router = APIRouter(prefix="/control", tags=["control"])


@router.post("/pause")
async def pause() -> dict[str, str]:
    await set_system_paused(True)
    return {"status": "paused"}


@router.post("/resume")
async def resume() -> dict[str, str]:
    await set_system_paused(False)
    return {"status": "running"}


@router.get("/status")
async def status() -> dict[str, bool]:
    return {"paused": await is_system_paused()}
