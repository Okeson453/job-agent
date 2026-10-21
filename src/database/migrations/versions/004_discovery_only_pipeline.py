"""Discovery-only pipeline: state remap, tracking timestamps, drop submission tables.

Revision ID: 004
Revises: 003
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

# Old application-prep/submission states → new tracking states.
_STATE_REMAP = {
    "APPLICATION_PREP": "DOCUMENT_PREP",
    "FACT_VALIDATION": "DOCUMENT_PREP",
    "READY": "DOCUMENT_PREP",
    "SUBMISSION": "DOCUMENT_PREP",
    "SUBMISSION_FAILED": "DOCUMENT_PREP",
    "HUMAN_INTERVENTION_REQUIRED": "DOCUMENT_PREP",
    "MANUAL_REVIEW": "DOCUMENT_PREP",
    "SUBMITTED": "APPLIED",
}


def upgrade() -> None:
    # 1. Remap legacy states onto the discovery-only pipeline.
    for old, new in _STATE_REMAP.items():
        op.execute(f"UPDATE applications SET state = '{new}' WHERE state = '{old}'")

    # 2. Rename submitted_at → applied_at (manual application timestamp)
    #    and add notified_at.
    op.alter_column("applications", "submitted_at", new_column_name="applied_at")
    op.add_column(
        "applications",
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 3. Backfill notified_at for rows that already reached a
    #    post-notification state (they were delivered to Telegram).
    op.execute(
        "UPDATE applications SET notified_at = updated_at "
        "WHERE state IN ('NOTIFIED', 'APPLIED', 'INTERVIEW', 'OFFER', "
        "'EMPLOYER_REJECTED') AND notified_at IS NULL"
    )

    # 4. Drop auto-submission artifacts.
    op.drop_column("applications", "screenshot_path")
    op.drop_table("application_answers")
    op.drop_table("automation_failures")
    op.drop_table("browser_sessions")


def downgrade() -> None:
    # Best-effort inverse: recreate dropped structures and rename columns.
    op.create_table(
        "browser_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("account_label", sa.String(128), nullable=False, server_default="default"),
        sa.Column("storage_state_enc", sa.Text(), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_browser_sessions_source", "browser_sessions", ["source"])
    op.create_table(
        "automation_failures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("failure_type", sa.String(64), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempt", sa.Integer(), server_default=sa.text("1")),
        sa.Column("context", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "application_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("validated", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.add_column(
        "applications",
        sa.Column("screenshot_path", sa.String(512), nullable=True),
    )
    op.drop_column("applications", "notified_at")
    op.alter_column("applications", "applied_at", new_column_name="submitted_at")
    for old, new in _STATE_REMAP.items():
        op.execute(f"UPDATE applications SET state = '{old}' WHERE state = '{new}'")
