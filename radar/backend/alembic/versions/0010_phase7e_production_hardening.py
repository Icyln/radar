"""Phase 7E production hardening and automation health.

Revision ID: 0010_phase7e
Revises: 0009_phase7c
Create Date: 2026-08-19
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_phase7e"
down_revision: str | None = "0009_phase7c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discovery_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", postgresql.ENUM(name="crawler_status", create_type=False), nullable=False),
        sa.Column("trigger", sa.String(length=100), nullable=True),
        sa.Column("external_run_id", sa.String(length=255), nullable=True),
        sa.Column("profiles", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("queries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("signals_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("signals_relevant", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_new", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_existing", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_deduplicated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matches_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notifications_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider_warnings", sa.Text(), nullable=True),
        sa.Column("candidates_promoted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_marked_unknown", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_closed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_type", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_discovery_runs_started_at", "discovery_runs", ["started_at"])
    op.create_index("ix_discovery_runs_completed_at", "discovery_runs", ["completed_at"])
    op.create_index("ix_discovery_runs_trigger", "discovery_runs", ["trigger"])
    op.create_index("ix_discovery_runs_external_run_id", "discovery_runs", ["external_run_id"])

    op.create_table(
        "job_source_observations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("source_kind", sa.String(length=32), nullable=False),
        sa.Column("source_provider", sa.String(length=255), nullable=False),
        sa.Column("source_external_id", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.String(length=2000), nullable=False),
        sa.Column("apply_url", sa.String(length=2000), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_provider",
            "source_external_id",
            name="uq_job_source_observation_provider_external",
        ),
    )
    op.create_index("ix_job_source_observations_job_id", "job_source_observations", ["job_id"])
    op.create_index(
        "ix_job_source_observations_job_seen",
        "job_source_observations",
        ["job_id", "last_seen_at"],
    )

    # Existing Phase 7C rows are lazily backfilled into this table the next time
    # their source is observed. This keeps the migration portable and avoids requiring
    # database-specific UUID generation functions.


def downgrade() -> None:
    op.drop_index("ix_job_source_observations_job_seen", table_name="job_source_observations")
    op.drop_index("ix_job_source_observations_job_id", table_name="job_source_observations")
    op.drop_table("job_source_observations")

    op.drop_index("ix_discovery_runs_external_run_id", table_name="discovery_runs")
    op.drop_index("ix_discovery_runs_trigger", table_name="discovery_runs")
    op.drop_index("ix_discovery_runs_completed_at", table_name="discovery_runs")
    op.drop_index("ix_discovery_runs_started_at", table_name="discovery_runs")
    op.drop_table("discovery_runs")
