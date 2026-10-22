"""Add employer application URL to jobs.

Some aggregator listings link out to the employer's own application form.
Keeping it in its own column preserves the original listing URL for
deduplication and the notification card, while retaining the direct route the
user may choose to visit.

Revision ID: 005
Revises: 004
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("employer_apply_url", sa.String(length=1024), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("jobs", "employer_apply_url")
