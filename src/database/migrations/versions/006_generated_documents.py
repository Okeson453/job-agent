"""Generated documents table.

Stores one row per tailored CV artefact (PDF, DOCX) with the file path and a
content hash so retries reuse the existing file instead of generating
duplicates.

Revision ID: 006
Revises: 005
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "generated_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False, server_default="cv"),
        sa.Column("format", sa.String(length=16), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sha256", sa.String(length=64), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "application_id",
            "kind",
            "format",
            name="uq_generated_documents_app_kind_format",
        ),
    )
    op.create_index(
        "ix_generated_documents_application_id",
        "generated_documents",
        ["application_id"],
    )
    op.create_index(
        "ix_generated_documents_job_id", "generated_documents", ["job_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_generated_documents_job_id", table_name="generated_documents")
    op.drop_index(
        "ix_generated_documents_application_id", table_name="generated_documents"
    )
    op.drop_table("generated_documents")
