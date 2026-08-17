"""Phase 6 targeted ATS discovery and source validation.

Revision ID: 0005_phase6
Revises: 0004_phase5
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_phase6"
down_revision: str | None = "0004_phase5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    target_status = postgresql.ENUM(
        "PENDING", "SCANNING", "COMPLETE", "FAILED", name="discovery_target_status"
    )
    candidate_status = postgresql.ENUM(
        "DISCOVERED", "VALIDATING", "VALID", "INVALID", name="discovery_candidate_status"
    )
    target_status.create(op.get_bind(), checkfirst=True)
    candidate_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "discovery_targets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("submitted_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("url", sa.String(length=1500), nullable=False),
        sa.Column("company_name_hint", sa.String(length=255), nullable=True),
        sa.Column("auto_watch", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "status",
            postgresql.ENUM(name="discovery_target_status", create_type=False),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("scan_attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pages_scanned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sources_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_type", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_discovery_targets_status_created", "discovery_targets", ["status", "created_at"]
    )
    op.create_index(
        "ix_discovery_targets_user_created",
        "discovery_targets",
        ["submitted_by_user_id", "created_at"],
    )

    op.create_table(
        "source_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("discovery_target_id", sa.Uuid(), nullable=True),
        sa.Column("name_hint", sa.String(length=255), nullable=True),
        sa.Column(
            "ats_provider",
            postgresql.ENUM(name="ats_provider", create_type=False),
            nullable=False,
        ),
        sa.Column("ats_identifier", sa.String(length=255), nullable=False),
        sa.Column("career_url", sa.String(length=1500), nullable=False),
        sa.Column("source_url", sa.String(length=1500), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="discovery_candidate_status", create_type=False),
            nullable=False,
            server_default="DISCOVERED",
        ),
        sa.Column("validation_attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("jobs_seen", sa.Integer(), nullable=True),
        sa.Column("error_type", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("promoted_company_id", sa.Uuid(), nullable=True),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["discovery_target_id"], ["discovery_targets.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["promoted_company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ats_provider", "ats_identifier", name="uq_source_candidate_provider_identifier"
        ),
    )
    op.create_index(
        "ix_source_candidates_status_created", "source_candidates", ["status", "created_at"]
    )
    op.create_index(
        "ix_source_candidates_target", "source_candidates", ["discovery_target_id"]
    )

    op.create_table(
        "discovery_target_candidates",
        sa.Column("discovery_target_id", sa.Uuid(), nullable=False),
        sa.Column("source_candidate_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["discovery_target_id"], ["discovery_targets.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_candidate_id"], ["source_candidates.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("discovery_target_id", "source_candidate_id"),
    )


def downgrade() -> None:
    op.drop_table("discovery_target_candidates")
    op.drop_index("ix_source_candidates_target", table_name="source_candidates")
    op.drop_index("ix_source_candidates_status_created", table_name="source_candidates")
    op.drop_table("source_candidates")
    op.drop_index("ix_discovery_targets_user_created", table_name="discovery_targets")
    op.drop_index("ix_discovery_targets_status_created", table_name="discovery_targets")
    op.drop_table("discovery_targets")
    postgresql.ENUM(name="discovery_candidate_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="discovery_target_status").drop(op.get_bind(), checkfirst=True)
