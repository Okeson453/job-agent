"""Durable-ish Redis queues with processing list, ack, retry, and DLQ.

Pattern:
  push → main list
  pop  → BRPOPLPUSH main → processing (message stays until ack)
  ack  → LREM processing
  nack → increment attempts; requeue or DLQ
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

import redis.asyncio as aioredis

from src.security.secrets import get_secret

ANALYSIS_QUEUE = "analysis_queue"
LLM_QUEUE = "llm_queue"
APPLICATION_QUEUE = "application_queue"
BROWSER_QUEUE = "browser_queue"
NOTIFICATION_QUEUE = "notification_queue"
DISCOVERY_QUEUE = "discovery_queue"

ALL_QUEUES = (
    DISCOVERY_QUEUE,
    ANALYSIS_QUEUE,
    LLM_QUEUE,
    APPLICATION_QUEUE,
    BROWSER_QUEUE,
    NOTIFICATION_QUEUE,
)

_MAX_ATTEMPTS = 5
_redis: aioredis.Redis | None = None


def _processing_key(queue_name: str) -> str:
    return f"{queue_name}:processing"


def _dlq_key(queue_name: str) -> str:
    return f"{queue_name}:dlq"


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        url = get_secret("REDIS_URL")
        _redis = aioredis.from_url(url, decode_responses=True)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def _envelope(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "attempts": int(payload.get("attempts") or 0),
        "enqueued_at": payload.get("enqueued_at") or time.time(),
        "payload": {k: v for k, v in payload.items() if k not in ("attempts", "enqueued_at", "id")},
    }


async def push(queue_name: str, payload: dict[str, Any]) -> str:
    """Push a payload. Returns message id."""
    client = await get_redis()
    env = _envelope(payload)
    await client.rpush(queue_name, json.dumps(env))
    return env["id"]


async def pop(queue_name: str, timeout: int = 5) -> dict[str, Any] | None:
    """Move one message from main list to processing list and return it.

    Caller must ack() or nack() the returned message.
    Returned dict includes _queue, _raw, _msg_id plus original payload keys.
    """
    client = await get_redis()
    processing = _processing_key(queue_name)
    result = await client.brpoplpush(queue_name, processing, timeout=timeout)
    if result is None:
        return None
    try:
        env = json.loads(result)
    except json.JSONDecodeError:
        # Legacy plain payloads
        env = {"id": str(uuid.uuid4()), "attempts": 0, "payload": json.loads(result) if result.startswith("{") else {}}
        if not env["payload"] and result.startswith("{"):
            try:
                env["payload"] = json.loads(result)
            except Exception:
                env["payload"] = {"raw": result}

    if "payload" not in env and isinstance(env, dict):
        # Already a flat legacy message
        payload = {k: v for k, v in env.items() if k not in ("id", "attempts", "enqueued_at")}
        env = {
            "id": env.get("id") or str(uuid.uuid4()),
            "attempts": int(env.get("attempts") or 0),
            "payload": payload,
        }

    data = dict(env.get("payload") or {})
    data["_queue"] = queue_name
    data["_raw"] = result
    data["_msg_id"] = env.get("id")
    data["_attempts"] = int(env.get("attempts") or 0)
    return data


async def ack(message: dict[str, Any]) -> None:
    """Remove message from the processing list after successful handling."""
    queue_name = message.get("_queue")
    raw = message.get("_raw")
    if not queue_name or raw is None:
        return
    client = await get_redis()
    await client.lrem(_processing_key(queue_name), 1, raw)


async def nack(message: dict[str, Any], *, error: str | None = None) -> None:
    """Requeue with attempt increment, or dead-letter after max attempts."""
    queue_name = message.get("_queue")
    raw = message.get("_raw")
    if not queue_name or raw is None:
        return
    client = await get_redis()
    processing = _processing_key(queue_name)
    await client.lrem(processing, 1, raw)

    attempts = int(message.get("_attempts") or 0) + 1
    payload = {
        k: v
        for k, v in message.items()
        if not k.startswith("_")
    }
    env = {
        "id": message.get("_msg_id") or str(uuid.uuid4()),
        "attempts": attempts,
        "enqueued_at": time.time(),
        "last_error": error,
        "payload": payload,
    }
    body = json.dumps(env)
    if attempts >= _MAX_ATTEMPTS:
        await client.rpush(_dlq_key(queue_name), body)
        # Operator visibility — design §19 "If repeated → Telegram alert"
        try:
            note = {
                "id": str(__import__("uuid").uuid4()),
                "attempts": 0,
                "enqueued_at": time.time(),
                "payload": {
                    "type": "dlq_dead_letter",
                    "queue": queue_name,
                    "attempts": attempts,
                    "last_error": error,
                    "original": payload,
                },
            }
            await client.rpush(NOTIFICATION_QUEUE, __import__("json").dumps(note))
        except Exception:
            pass
    else:
        await client.rpush(queue_name, body)


async def queue_length(queue_name: str) -> int:
    client = await get_redis()
    return int(await client.llen(queue_name))


async def is_system_paused() -> bool:
    client = await get_redis()
    value = await client.get("system:paused")
    return value is not None and value.lower() in ("1", "true", "yes")


async def set_system_paused(paused: bool) -> None:
    client = await get_redis()
    if paused:
        await client.set("system:paused", "1")
    else:
        await client.delete("system:paused")
