"""Phase 7 profile-driven active hiring discovery.

Revision ID: 0008_phase7
Revises: 0007_phase6c
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_phase7"
down_revision: str | None = "0007_phase6c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("discovery_targets", sa.Column("signal_external_id", sa.String(500)))
    op.add_column("discovery_targets", sa.Column("job_title_hint", sa.String(500)))
    op.add_column("discovery_targets", sa.Column("job_location_hint", sa.String(500)))
    op.add_column("discovery_targets", sa.Column("job_posted_at_hint", sa.DateTime(timezone=True)))
    op.create_index(
        "ix_discovery_targets_signal_posted",
        "discovery_targets",
        ["job_posted_at_hint", "status"],
    )

    op.add_column("companies", sa.Column("discovery_boost_until", sa.DateTime(timezone=True)))
    op.create_index(
        "ix_companies_discovery_boost",
        "companies",
        ["active", "discovery_boost_until"],
    )

    op.add_column("jobs", sa.Column("discovery_signal_at", sa.DateTime(timezone=True)))
    op.add_column("jobs", sa.Column("discovery_signal_source", sa.String(100)))
    op.create_index(
        "ix_jobs_status_discovery_signal_at",
        "jobs",
        ["status", "discovery_signal_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_status_discovery_signal_at", table_name="jobs")
    op.drop_column("jobs", "discovery_signal_source")
    op.drop_column("jobs", "discovery_signal_at")
    op.drop_index("ix_companies_discovery_boost", table_name="companies")
    op.drop_column("companies", "discovery_boost_until")
    op.drop_index("ix_discovery_targets_signal_posted", table_name="discovery_targets")
    op.drop_column("discovery_targets", "job_posted_at_hint")
    op.drop_column("discovery_targets", "job_location_hint")
    op.drop_column("discovery_targets", "job_title_hint")
    op.drop_column("discovery_targets", "signal_external_id")
