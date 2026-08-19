"""Phase 7C first-class WIDE discovery jobs.

Revision ID: 0009_phase7c
Revises: 0008_phase7
Create Date: 2026-08-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_phase7c"
down_revision: str | None = "0008_phase7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Discovery-feed jobs may be known before Radar resolves the employer to a direct
    # Greenhouse/Lever/Ashby company, so those two direct-source fields become optional.
    op.alter_column("jobs", "company_id", existing_type=sa.Uuid(), nullable=True)
    op.alter_column("jobs", "ats_provider", nullable=True)

    op.add_column(
        "jobs",
        sa.Column("source_kind", sa.String(length=32), nullable=False, server_default="DIRECT_ATS"),
    )
    op.add_column("jobs", sa.Column("source_provider", sa.String(length=100), nullable=True))
    op.add_column("jobs", sa.Column("source_external_id", sa.String(length=500), nullable=True))
    op.add_column("jobs", sa.Column("source_company_name", sa.String(length=255), nullable=True))
    op.alter_column("jobs", "source_kind", server_default=None)

    op.create_unique_constraint(
        "uq_job_discovery_source_external_id",
        "jobs",
        ["source_provider", "source_external_id"],
    )
    op.create_index(
        "ix_jobs_source_kind_status",
        "jobs",
        ["source_kind", "status", "first_seen_at"],
    )


def downgrade() -> None:
    # Downgrade is intentionally strict: unresolved WIDE jobs cannot fit the old schema.
    op.execute("DELETE FROM jobs WHERE company_id IS NULL OR ats_provider IS NULL")
    op.drop_index("ix_jobs_source_kind_status", table_name="jobs")
    op.drop_constraint("uq_job_discovery_source_external_id", "jobs", type_="unique")
    op.drop_column("jobs", "source_company_name")
    op.drop_column("jobs", "source_external_id")
    op.drop_column("jobs", "source_provider")
    op.drop_column("jobs", "source_kind")
    op.alter_column("jobs", "ats_provider", nullable=False)
    op.alter_column("jobs", "company_id", existing_type=sa.Uuid(), nullable=False)
