"""Per-part Telegram delivery tracking.

A notification is delivered in several parts (card, email draft, CV PDF, CV
DOCX). Recording each part separately lets a retried queue message skip the
parts that already succeeded instead of spamming the chat with duplicates.

Revision ID: 007
Revises: 006
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("part", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="sent"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("body_len", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "application_id", "part", name="uq_notification_deliveries_app_part"
        ),
    )
    op.create_index(
        "ix_notification_deliveries_application_id",
        "notification_deliveries",
        ["application_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_deliveries_application_id",
        table_name="notification_deliveries",
    )
    op.drop_table("notification_deliveries")
