"""Durable-ish Redis queues with processing list, ack, retry, and DLQ.

push → RPUSH to queue list
pop → BLPOP + track in processing list with attempts
ack → remove from processing
nack → increment attempts; requeue or DLQ
"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any

from src.observability.logging import get_logger

logger = get_logger(__name__)

DISCOVERY_QUEUE = "discovery_queue"
ANALYSIS_QUEUE = "analysis_queue"
LLM_QUEUE = "llm_queue"
APPLICATION_QUEUE = "application_queue"
BROWSER_QUEUE = "browser_queue"
NOTIFICATION_QUEUE = "notification_queue"

_MAX_ATTEMPTS = 5
_redis = None


def _dlq_key(queue_name: str) -> str:
    return f"{queue_name}:dlq"


def _processing_key(queue_name: str) -> str:
    return f"{queue_name}:processing"


async def get_redis():
    global _redis
    if _redis is not None:
        return _redis
    import redis.asyncio as redis

    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    _redis = redis.from_url(url, decode_responses=True)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


async def push(queue_name: str, payload: dict[str, Any]) -> None:
    client = await get_redis()
    body = json.dumps({"id": str(uuid.uuid4()), "payload": payload, "attempts": int(payload.get("_attempts") or 0)})
    await client.rpush(queue_name, body)


async def pop(queue_name: str, timeout: int = 5) -> dict[str, Any] | None:
    client = await get_redis()
    item = await client.blpop(queue_name, timeout=timeout)
    if item is None:
        return None
    _, body = item
    try:
        envelope = json.loads(body)
    except json.JSONDecodeError:
        envelope = {"id": str(uuid.uuid4()), "payload": {}, "attempts": 0, "raw": body}
    envelope["_queue"] = queue_name
    envelope["_body"] = body
    await client.hset(_processing_key(queue_name), envelope["id"], body)
    payload = dict(envelope.get("payload") or {})
    payload["_envelope_id"] = envelope["id"]
    payload["_queue"] = queue_name
    payload["_attempts"] = int(envelope.get("attempts") or 0)
    return payload


async def ack(message: dict[str, Any]) -> None:
    queue_name = message.get("_queue")
    env_id = message.get("_envelope_id")
    if not queue_name or not env_id:
        return
    client = await get_redis()
    await client.hdel(_processing_key(queue_name), env_id)


async def nack(message: dict[str, Any], *, error: str = "") -> None:
    queue_name = message.get("_queue") or "unknown"
    env_id = message.get("_envelope_id")
    attempts = int(message.get("_attempts") or 0) + 1
    client = await get_redis()
    payload = {k: v for k, v in message.items() if not k.startswith("_")}
    payload["_attempts"] = attempts
    body = json.dumps({"id": env_id or str(uuid.uuid4()), "payload": payload, "attempts": attempts, "error": error})
    if env_id:
        await client.hdel(_processing_key(queue_name), env_id)
    if attempts >= _MAX_ATTEMPTS:
        await client.rpush(_dlq_key(queue_name), body)
        try:
            await client.rpush(
                NOTIFICATION_QUEUE,
                json.dumps(
                    {
                        "id": str(uuid.uuid4()),
                        "payload": {
                            "type": "dlq_dead_letter",
                            "queue": queue_name,
                            "error": error,
                            "attempts": attempts,
                        },
                        "attempts": 0,
                    }
                ),
            )
        except Exception:
            pass
        logger.error("queue.dlq", queue=queue_name, attempts=attempts, error=error)
        return
    await client.rpush(queue_name, body)
    logger.warning("queue.nack", queue=queue_name, attempts=attempts, error=error)


async def is_system_paused() -> bool:
    client = await get_redis()
    value = await client.get("system:paused")
    if value is None:
        return False
    if isinstance(value, bytes):
        value = value.decode()
    return str(value).lower() in ("1", "true", "yes")


async def set_system_paused(paused: bool, *, ttl_seconds: int | None = None) -> None:
    """Assert or clear the global pause flag.

    When paused, a TTL is applied (default 3600s) so an accidental pause
    self-clears rather than permanently freezing the pipeline.
    """
    client = await get_redis()
    if paused:
        ttl = ttl_seconds
        if ttl is None:
            ttl = int(os.environ.get("SYSTEM_PAUSE_TTL_SECONDS", "3600"))
        if ttl and ttl > 0:
            await client.set("system:paused", "1", ex=ttl)
        else:
            await client.set("system:paused", "1")
    else:
        await client.delete("system:paused")
