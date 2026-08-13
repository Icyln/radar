"""Phase 0 and Phase 1 foundation.

Revision ID: 0001_phase0_phase1
Revises:
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_phase0_phase1"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ats_provider = postgresql.ENUM("GREENHOUSE", "LEVER", "ASHBY", name="ats_provider")
monitoring_priority = postgresql.ENUM("HIGH", "NORMAL", "LOW", name="monitoring_priority")
work_mode = postgresql.ENUM("REMOTE", "HYBRID", "ONSITE", "UNKNOWN", name="work_mode")
job_status = postgresql.ENUM("ACTIVE", "UNKNOWN", "CLOSED", name="job_status")
crawler_status = postgresql.ENUM("SUCCESS", "PARTIAL", "FAILED", "SKIPPED", name="crawler_status")
notification_channel = postgresql.ENUM("TELEGRAM", name="notification_channel")
notification_status = postgresql.ENUM("PENDING", "SENDING", "SENT", "FAILED", name="notification_status")


def _enum(name: str, *values: str) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    for enum in (
        ats_provider,
        monitoring_priority,
        work_mode,
        job_status,
        crawler_status,
        notification_channel,
        notification_status,
    ):
        enum.create(bind, checkfirst=True)

    op.create_table(
        "companies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("website", sa.String(1000), nullable=True),
        sa.Column("career_url", sa.String(1000), nullable=False),
        sa.Column("ats_provider", _enum("ats_provider", "GREENHOUSE", "LEVER", "ASHBY"), nullable=False),
        sa.Column("ats_identifier", sa.String(255), nullable=False),
        sa.Column("monitoring_priority", _enum("monitoring_priority", "HIGH", "NORMAL", "LOW"), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ats_provider", "ats_identifier", name="uq_company_provider_identifier"),
    )
    op.create_index("ix_companies_monitoring", "companies", ["active", "monitoring_priority", "last_checked_at"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("ats_provider", _enum("ats_provider", "GREENHOUSE", "LEVER", "ASHBY"), nullable=False),
        sa.Column("external_job_id", sa.String(255), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("work_mode", _enum("work_mode", "REMOTE", "HYBRID", "ONSITE", "UNKNOWN"), nullable=False),
        sa.Column("employment_type", sa.String(100), nullable=True),
        sa.Column("apply_url", sa.String(2000), nullable=False),
        sa.Column("source_url", sa.String(2000), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("missing_count", sa.Integer(), nullable=False),
        sa.Column("status", _enum("job_status", "ACTIVE", "UNKNOWN", "CLOSED"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "ats_provider", "external_job_id", name="uq_job_provider_external_id"),
        sa.UniqueConstraint("company_id", "fingerprint", name="uq_job_company_fingerprint"),
    )
    op.create_index("ix_jobs_company_id", "jobs", ["company_id"])
    op.create_index("ix_jobs_company_status", "jobs", ["company_id", "status"])
    op.create_index("ix_jobs_status_last_seen", "jobs", ["status", "last_seen_at"])

    op.create_table(
        "crawler_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("ats_provider", _enum("ats_provider", "GREENHOUSE", "LEVER", "ASHBY"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", _enum("crawler_status", "SUCCESS", "PARTIAL", "FAILED", "SKIPPED"), nullable=False),
        sa.Column("jobs_received", sa.Integer(), nullable=False),
        sa.Column("jobs_new", sa.Integer(), nullable=False),
        sa.Column("jobs_updated", sa.Integer(), nullable=False),
        sa.Column("jobs_closed", sa.Integer(), nullable=False),
        sa.Column("matches_created", sa.Integer(), nullable=False),
        sa.Column("notifications_sent", sa.Integer(), nullable=False),
        sa.Column("error_type", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crawler_logs_company_id", "crawler_logs", ["company_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("crawler_log_id", sa.Uuid(), nullable=True),
        sa.Column("channel", _enum("notification_channel", "TELEGRAM"), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("status", _enum("notification_status", "PENDING", "SENDING", "SENT", "FAILED"), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("telegram_message_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["crawler_log_id"], ["crawler_logs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "channel", "recipient", name="uq_notification_job_channel_recipient"),
    )
    op.create_index("ix_notifications_job_id", "notifications", ["job_id"])
    op.create_index("ix_notifications_crawler_log_id", "notifications", ["crawler_log_id"])
    op.create_index("ix_notifications_delivery", "notifications", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_notifications_delivery", table_name="notifications")
    op.drop_index("ix_notifications_crawler_log_id", table_name="notifications")
    op.drop_index("ix_notifications_job_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_crawler_logs_company_id", table_name="crawler_logs")
    op.drop_table("crawler_logs")
    op.drop_index("ix_jobs_status_last_seen", table_name="jobs")
    op.drop_index("ix_jobs_company_status", table_name="jobs")
    op.drop_index("ix_jobs_company_id", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_companies_monitoring", table_name="companies")
    op.drop_table("companies")

    bind = op.get_bind()
    for enum in (
        notification_status,
        notification_channel,
        crawler_status,
        job_status,
        work_mode,
        monitoring_priority,
        ats_provider,
    ):
        enum.drop(bind, checkfirst=True)
