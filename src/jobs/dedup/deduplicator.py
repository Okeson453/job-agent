"""Deduplicate discovered jobs.

Fast path: Redis set of recent (source, external_id) pairs.
Fallback: indexed DB lookup, then fuzzy (company, title) match.
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.jobs.models import Job
from src.jobs.schemas import JobCreate
from src.scheduler.queues import get_redis

_REDIS_DEDUP_KEY = "dedup:jobs:recent"
_REDIS_DEDUP_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days


def _normalize_text(text: str) -> str:
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()



def _fingerprint(job: JobCreate) -> str:
    return _normalize_text(f"{job.company}|{job.title}|{job.location or ''}")


def _dedup_key(source: str, external_id: str) -> str:
    return f"{source}:{external_id}"


async def is_duplicate(job: JobCreate, db: AsyncSession) -> bool:
    """Return True if this job has already been seen.

    Checks Redis first (hot path), then the unique (source, external_id)
    constraint via DB, then a fuzzy company+title match.
    """
    key = _dedup_key(job.source, job.external_id)

    client = await get_redis()
    if await client.sismember(_REDIS_DEDUP_KEY, key):
        return True

    # Exact DB lookup.
    result = await db.execute(
        select(Job.id).where(
            Job.source == job.source,
            Job.external_id == job.external_id,
        )
    )
    if result.scalar_one_or_none() is not None:
        await _remember(key)
        return True

    # Cross-source fingerprint (company|title|location).
    fp = _fingerprint(job)
    fp_key = f"fp:{fp}"
    try:
        client = await get_redis()
        if await client.sismember(_REDIS_DEDUP_KEY, fp_key):
            await _remember(key)
            return True
    except Exception:
        pass

    # Fuzzy fallback: exact normalized company AND title (same source).
    company_norm = _normalize_text(job.company)
    title_norm = _normalize_text(job.title)
    if company_norm and title_norm:
        result = await db.execute(
            select(Job.id, Job.title, Job.company).where(Job.source == job.source).limit(50)
        )
        for row in result.all():
            if (
                _normalize_text(row.company) == company_norm
                and _normalize_text(row.title) == title_norm
            ):
                await _remember(key)
                return True

    return False


async def remember(job: JobCreate) -> None:
    """Record a job as seen in the Redis dedup set."""
    key = _dedup_key(job.source, job.external_id)
    await _remember(key)
    await _remember(f"fp:{_fingerprint(job)}")


async def _remember(key: str) -> None:
    client = await get_redis()
    await client.sadd(_REDIS_DEDUP_KEY, key)
    await client.expire(_REDIS_DEDUP_KEY, _REDIS_DEDUP_TTL_SECONDS)
