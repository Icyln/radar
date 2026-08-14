"""Phase 4.3 profile coverage modes and per-user company watchlists.

Revision ID: 0003_phase4_3
Revises: 0002_phase2_phase3
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_phase4_3"
down_revision: str | None = "0002_phase2_phase3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

profile_coverage_mode = postgresql.ENUM("WATCHLIST", "WIDE", name="profile_coverage_mode")


def upgrade() -> None:
    bind = op.get_bind()
    profile_coverage_mode.create(bind, checkfirst=True)

    op.add_column(
        "job_profiles",
        sa.Column(
            "coverage_mode",
            postgresql.ENUM(
                "WATCHLIST", "WIDE", name="profile_coverage_mode", create_type=False
            ),
            server_default="WIDE",
            nullable=False,
        ),
    )
    # Existing profiles retain Phase 4.2 behavior: search every known active source.
    op.alter_column("job_profiles", "coverage_mode", server_default=None)

    op.create_table(
        "user_company_watchlists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "company_id", name="uq_user_company_watchlist_user_company"
        ),
    )
    op.create_index(
        "ix_user_company_watchlists_user_id", "user_company_watchlists", ["user_id"]
    )
    op.create_index(
        "ix_user_company_watchlists_company_id", "user_company_watchlists", ["company_id"]
    )
    op.create_index(
        "ix_user_company_watchlists_user_company",
        "user_company_watchlists",
        ["user_id", "company_id"],
    )
    op.create_index("ix_jobs_status_first_seen", "jobs", ["status", "first_seen_at"])


def downgrade() -> None:
    op.drop_index("ix_jobs_status_first_seen", table_name="jobs")
    op.drop_index("ix_user_company_watchlists_user_company", table_name="user_company_watchlists")
    op.drop_index("ix_user_company_watchlists_company_id", table_name="user_company_watchlists")
    op.drop_index("ix_user_company_watchlists_user_id", table_name="user_company_watchlists")
    op.drop_table("user_company_watchlists")
    op.drop_column("job_profiles", "coverage_mode")
    profile_coverage_mode.drop(op.get_bind(), checkfirst=True)
