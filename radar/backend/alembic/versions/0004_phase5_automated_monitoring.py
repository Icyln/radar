"""Phase 5 automated monitoring run observability.

Revision ID: 0004_phase5
Revises: 0003_phase4_3
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_phase5"
down_revision: str | None = "0003_phase4_3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _enum(name: str, *values: str) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    op.create_table(
        "monitor_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            _enum("crawler_status", "SUCCESS", "PARTIAL", "FAILED", "SKIPPED"),
            nullable=False,
        ),
        sa.Column("source_scope", sa.String(length=20), nullable=False),
        sa.Column(
            "priority",
            _enum("monitoring_priority", "HIGH", "NORMAL", "LOW"),
            nullable=True,
        ),
        sa.Column("shard_index", sa.Integer(), nullable=False),
        sa.Column("shard_count", sa.Integer(), nullable=False),
        sa.Column("batch_size", sa.Integer(), nullable=True),
        sa.Column("min_age_minutes", sa.Integer(), nullable=True),
        sa.Column("max_concurrency", sa.Integer(), nullable=False),
        sa.Column("companies_selected", sa.Integer(), nullable=False),
        sa.Column("companies_succeeded", sa.Integer(), nullable=False),
        sa.Column("companies_failed", sa.Integer(), nullable=False),
        sa.Column("companies_skipped", sa.Integer(), nullable=False),
        sa.Column("notifications_sent", sa.Integer(), nullable=False),
        sa.Column("trigger", sa.String(length=100), nullable=True),
        sa.Column("external_run_id", sa.String(length=255), nullable=True),
        sa.Column("error_type", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_monitor_runs_started_at", "monitor_runs", ["started_at"])
    op.create_index("ix_monitor_runs_scope_started", "monitor_runs", ["source_scope", "started_at"])
    op.create_index("ix_monitor_runs_status_started", "monitor_runs", ["status", "started_at"])

    op.add_column("crawler_logs", sa.Column("monitor_run_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_crawler_logs_monitor_run_id",
        "crawler_logs",
        "monitor_runs",
        ["monitor_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_crawler_logs_monitor_run_id", "crawler_logs", ["monitor_run_id"])


def downgrade() -> None:
    op.drop_index("ix_crawler_logs_monitor_run_id", table_name="crawler_logs")
    op.drop_constraint("fk_crawler_logs_monitor_run_id", "crawler_logs", type_="foreignkey")
    op.drop_column("crawler_logs", "monitor_run_id")
    op.drop_index("ix_monitor_runs_status_started", table_name="monitor_runs")
    op.drop_index("ix_monitor_runs_scope_started", table_name="monitor_runs")
    op.drop_index("ix_monitor_runs_started_at", table_name="monitor_runs")
    op.drop_table("monitor_runs")
