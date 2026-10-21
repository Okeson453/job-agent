"""Outbox, application unique job_id, lifecycle timestamps, browser sessions, failures.

Revision ID: 003
Revises: 002
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("queue_name", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_outbox_events_queue_name", "outbox_events", ["queue_name"])
    op.create_index("ix_outbox_events_status", "outbox_events", ["status"])

    for col in ("submitted_at", "interview_at", "offer_at", "rejected_at"):
        op.add_column(
            "applications",
            sa.Column(col, sa.DateTime(timezone=True), nullable=True),
        )

    op.create_unique_constraint("uq_applications_job_id", "applications", ["job_id"])

    op.create_table(
        "browser_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column(
            "account_label",
            sa.String(128),
            nullable=False,
            server_default="default",
        ),
        sa.Column("storage_state_enc", sa.Text(), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_browser_sessions_source", "browser_sessions", ["source"])

    op.create_table(
        "automation_failures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("failure_type", sa.String(64), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempt", sa.Integer(), server_default="1"),
        sa.Column("context", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_automation_failures_application_id",
        "automation_failures",
        ["application_id"],
    )

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("channel", sa.String(32), nullable=False, server_default="telegram"),
        sa.Column("msg_type", sa.String(64), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(16), nullable=False, server_default="sent"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_index(
        "ix_automation_failures_application_id", table_name="automation_failures"
    )
    op.drop_table("automation_failures")
    op.drop_index("ix_browser_sessions_source", table_name="browser_sessions")
    op.drop_table("browser_sessions")
    op.drop_constraint("uq_applications_job_id", "applications", type_="unique")
    for col in ("submitted_at", "interview_at", "offer_at", "rejected_at"):
        op.drop_column("applications", col)
    op.drop_index("ix_outbox_events_status", table_name="outbox_events")
    op.drop_index("ix_outbox_events_queue_name", table_name="outbox_events")
    op.drop_table("outbox_events")
