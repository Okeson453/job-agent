"""Persistent browser session metadata (encrypted storage_state JSON)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, func, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base
from src.security.encryption import decrypt, encrypt


class BrowserSession(Base):
    __tablename__ = "browser_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    account_label: Mapped[str] = mapped_column(String(128), nullable=False, default="default")
    # Encrypted Playwright storage_state JSON
    storage_state_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


async def save_storage_state(
    db: AsyncSession,
    *,
    source: str,
    account_label: str = "default",
    storage_state_json: str,
) -> BrowserSession:
    result = await db.execute(
        select(BrowserSession).where(
            BrowserSession.source == source,
            BrowserSession.account_label == account_label,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = BrowserSession(source=source, account_label=account_label)
        db.add(row)
    row.storage_state_enc = encrypt(storage_state_json)
    await db.flush()
    return row


async def load_storage_state(
    db: AsyncSession, *, source: str, account_label: str = "default"
) -> str | None:
    result = await db.execute(
        select(BrowserSession).where(
            BrowserSession.source == source,
            BrowserSession.account_label == account_label,
        )
    )
    row = result.scalar_one_or_none()
    if row is None or not row.storage_state_enc:
        return None
    return decrypt(row.storage_state_enc)
