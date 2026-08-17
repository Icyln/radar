"""Phase 6C freshness-aware matching and baseline evidence.

Revision ID: 0007_phase6c
Revises: 0006_phase6b
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_phase6c"
down_revision: str | None = "0006_phase6b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "job_profiles",
        sa.Column("max_job_age_days", sa.Integer(), nullable=True, server_default="30"),
    )
    op.add_column(
        "job_profiles",
        sa.Column(
            "include_unknown_posted_at",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    # Existing jobs with no provider publication date are conservatively treated as
    # baseline inventory. Radar must not make them look fresh merely because this
    # migration (or initial source discovery) happened recently.
    op.add_column(
        "jobs",
        sa.Column("baseline_imported", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column("jobs", "baseline_imported", server_default=sa.false())
    op.create_index("ix_jobs_status_posted_at", "jobs", ["status", "posted_at"])


def downgrade() -> None:
    op.drop_index("ix_jobs_status_posted_at", table_name="jobs")
    op.drop_column("jobs", "baseline_imported")
    op.drop_column("job_profiles", "include_unknown_posted_at")
    op.drop_column("job_profiles", "max_job_age_days")
