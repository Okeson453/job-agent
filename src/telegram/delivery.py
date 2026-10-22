"""Track which parts of a notification have already been delivered."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base

# Parts of an opportunity notification.
PART_CARD = "card"
PART_EMAIL = "email"
PART_CV_PDF = "cv_pdf"
PART_CV_DOCX = "cv_docx"


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    part: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="sent")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_len: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "application_id", "part", name="uq_notification_deliveries_app_part"
        ),
    )


async def delivered_parts(
    db: AsyncSession, application_id: uuid.UUID | str
) -> set[str]:
    app_id = uuid.UUID(str(application_id))
    rows = (
        await db.execute(
            select(NotificationDelivery.part).where(
                NotificationDelivery.application_id == app_id,
                NotificationDelivery.status == "sent",
            )
        )
    ).scalars().all()
    return set(rows)


async def _row(
    db: AsyncSession, application_id: uuid.UUID | str, part: str
) -> NotificationDelivery | None:
    app_id = uuid.UUID(str(application_id))
    return (
        await db.execute(
            select(NotificationDelivery).where(
                NotificationDelivery.application_id == app_id,
                NotificationDelivery.part == part,
            )
        )
    ).scalar_one_or_none()


async def mark_sent(
    db: AsyncSession,
    application_id: uuid.UUID | str,
    part: str,
    *,
    body_len: int | None = None,
) -> None:
    row = await _row(db, application_id, part)
    if row is None:
        row = NotificationDelivery(
            application_id=uuid.UUID(str(application_id)), part=part
        )
        db.add(row)
    row.status = "sent"
    row.error = None
    row.body_len = body_len
    row.attempts = (row.attempts or 0) + 1
    await db.flush()


async def mark_skipped(
    db: AsyncSession,
    application_id: uuid.UUID | str,
    part: str,
    reason: str,
) -> None:
    """Record that a part was intentionally not sent (policy/config)."""
    row = await _row(db, application_id, part)
    if row is None:
        row = NotificationDelivery(
            application_id=uuid.UUID(str(application_id)), part=part
        )
        db.add(row)
    row.status = "skipped"
    row.error = reason[:1000]
    await db.flush()


async def count_sent_today(db: AsyncSession, part: str = PART_CARD) -> int:
    """How many of ``part`` have already been delivered today (UTC)."""
    start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    total = (
        await db.execute(
            select(func.count())
            .select_from(NotificationDelivery)
            .where(
                NotificationDelivery.part == part,
                NotificationDelivery.status == "sent",
                NotificationDelivery.created_at >= start,
            )
        )
    ).scalar_one()
    return int(total or 0)


async def mark_failed(
    db: AsyncSession,
    application_id: uuid.UUID | str,
    part: str,
    error: str,
) -> None:
    row = await _row(db, application_id, part)
    if row is None:
        row = NotificationDelivery(
            application_id=uuid.UUID(str(application_id)), part=part
        )
        db.add(row)
    row.status = "failed"
    row.error = error[:1000]
    row.attempts = (row.attempts or 0) + 1
    await db.flush()
