"""Transactional outbox helpers.

Write business state and an outbox row in the same DB session/commit, then
publish to Redis and mark published. Prevents lost queue messages after DB commit.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, func, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base
from src.scheduler.queues import push


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    queue_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


async def enqueue_outbox(
    db: AsyncSession, queue_name: str, payload: dict[str, Any]
) -> OutboxEvent:
    row = OutboxEvent(queue_name=queue_name, payload=payload, status="pending")
    db.add(row)
    await db.flush()
    return row


async def publish_pending_outbox(db: AsyncSession, *, limit: int = 50) -> int:
    result = await db.execute(
        select(OutboxEvent)
        .where(OutboxEvent.status == "pending")
        .order_by(OutboxEvent.created_at)
        .limit(limit)
    )
    rows = list(result.scalars().all())
    published = 0
    for row in rows:
        try:
            await push(row.queue_name, dict(row.payload))
            row.status = "published"
            row.published_at = func.now()  # type: ignore[assignment]
            published += 1
        except Exception as exc:
            row.attempts = int(row.attempts or 0) + 1
            row.last_error = str(exc)
            if row.attempts >= 10:
                row.status = "failed"
    await db.flush()
    return published
