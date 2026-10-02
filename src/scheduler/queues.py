"""Durable-ish Redis queues with processing list, ack, retry, and DLQ.
push → RPUSH to queue list
pop → BLPOP + track in processing list with attempts
ack → remove from processing
nack → increment attempts; requeue or DLQ
requeue_dlq → move dead-lettered items back onto the queue (attempts reset)
reclaim_processing → return crashed in-flight items to their queue
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

ALL_QUEUES = (
    DISCOVERY_QUEUE,
    ANALYSIS_QUEUE,
    LLM_QUEUE,
    APPLICATION_QUEUE,
    BROWSER_QUEUE,
    NOTIFICATION_QUEUE,
)

_MAX_ATTEMPTS = 5
_PAUSE_KEY = "system:paused"
_REDIS_LAST_HEALTH: float = 0.0
_redis = None


def _dlq_key(queue_name: str) -> str:
    return f"{queue_name}:dlq"


def _processing_key(queue_name: str) -> str:
    return f"{queue_name}:processing"


async def get_redis():
    """Return the Redis client, creating a fresh one when unhealthy.

    On free-tier managed Redis the provider can put the instance to sleep;
    the first operations after wake-up can fail. Reconnect here so a stale
    pooled connection does not poison the whole process.
    """
    global _redis
    if _redis is not None:
        try:
            await _redis.ping()
            _REDIS_LAST_HEALTH = time.time()
            return _redis
        except Exception as exc:
            logger.warning("redis.unhealthy", error=str(exc))
            try:
                await _redis.aclose()
            except Exception:
                pass
            _redis = None
    import redis.asyncio as redis

    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    _redis = redis.from_url(url, decode_responses=True)
    # Fail fast on a dead/asleep instance instead of hanging forever.
    _redis.socket_timeout = 10
    _redis.socket_connect_timeout = 10
    return _redis


async def redis_health() -> bool:
    """Ping Redis; return True when reachable. Never raises."""
    global _redis
    try:
        client = await get_redis()
        await client.ping()
        _REDIS_LAST_HEALTH = time.time()
        return True
    except Exception:
        _redis = None
        return False


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        try:
            await _redis.aclose()
        except Exception:
            pass
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
    payload["last_error"] = error
    body = json.dumps({"id": env_id or str(uuid.uuid4()), "payload": payload, "attempts": attempts, "error": error})
    if env_id:
        try:
            await client.hdel(_processing_key(queue_name), env_id)
        except Exception:
            pass
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


async def requeue_dlq(queue_name: str, *, limit: int = 100) -> int:
    """Move dead-lettered messages back onto *queue_name* with attempts reset.

    Consumers are idempotent, so a requeued message is re-processed safely.
    Returns the number of messages moved.
    """
    client = await get_redis()
    moved = 0
    while moved < limit:
        body = await client.lpop(_dlq_key(queue_name))
        if body is None:
            break
        try:
            envelope = json.loads(body)
            envelope["attempts"] = 0
            payload = dict(envelope.get("payload") or {})
            payload.pop("_attempts", None)
            payload.pop("last_error", None)
            envelope["payload"] = payload
            out = json.dumps(envelope)
        except Exception:
            out = json.dumps({"id": str(uuid.uuid4()), "payload": {}, "attempts": 0, "raw": body})
        await client.rpush(queue_name, out)
        moved += 1
    if moved:
        logger.warning("queue.dlq_requeued", queue=queue_name, moved=moved)
    return moved


async def reclaim_processing(queue_name: str) -> int:
    """Return in-flight messages (pop'ed but never acked) to their queue.

    Only safe before consumers start (e.g. worker startup after a crash).
    Returns the number of messages reclaimed.
    """
    client = await get_redis()
    entries = await client.hgetall(_processing_key(queue_name))
    moved = 0
    for env_id, body in entries.items():
        await client.hdel(_processing_key(queue_name), env_id)
        await client.rpush(queue_name, body)
        moved += 1
    if moved:
        logger.warning("queue.processing_reclaimed", queue=queue_name, moved=moved)
    return moved


async def dlq_depths() -> dict[str, int]:
    """Return non-zero DLQ depths for all queues."""
    client = await get_redis()
    depths: dict[str, int] = {}
    for q in ALL_QUEUES:
        n = await client.llen(_dlq_key(q))
        if n:
            depths[q] = n
    return depths


async def is_system_paused() -> bool:
    client = await get_redis()
    value = await client.get(_PAUSE_KEY)
    if value is None:
        return False
    if isinstance(value, bytes):
        value = value.decode()
    if str(value).lower() not in ("1", "true", "yes"):
        return False
    # A pause key set without a TTL would freeze the pipeline forever.
    # Give it the default TTL so the system self-resumes.
    ttl = await client.ttl(_PAUSE_KEY)
    if ttl == -1:
        default_ttl = int(os.environ.get("SYSTEM_PAUSE_TTL_SECONDS", "3600"))
        if default_ttl > 0:
            await client.expire(_PAUSE_KEY, default_ttl)
            logger.warning("pause.key_no_ttl", applied_ttl=default_ttl)
    return True


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
            await client.set(_PAUSE_KEY, "1", ex=ttl)
        else:
            await client.set(_PAUSE_KEY, "1")
    else:
        await client.delete(_PAUSE_KEY)
