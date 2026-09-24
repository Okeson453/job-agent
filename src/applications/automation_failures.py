"""Durable automation failure records."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class AutomationFailure(Base):
    __tablename__ = "automation_failures"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    failure_type: Mapped[str] = mapped_column(String(64), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


async def record_failure(
    db: AsyncSession,
    *,
    failure_type: str,
    error: str | None = None,
    application_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    attempt: int = 1,
    context: dict[str, Any] | None = None,
) -> AutomationFailure:
    row = AutomationFailure(
        failure_type=failure_type,
        error=error,
        application_id=application_id,
        job_id=job_id,
        attempt=attempt,
        context=context,
    )
    db.add(row)
    await db.flush()
    return row
