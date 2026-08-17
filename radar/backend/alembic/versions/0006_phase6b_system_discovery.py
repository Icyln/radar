"""Phase 6B system-managed discovery feeds and revalidation.

Revision ID: 0006_phase6b
Revises: 0005_phase6
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_phase6b"
down_revision: str | None = "0005_phase6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    origin = postgresql.ENUM("USER", "SYSTEM_FEED", name="discovery_target_origin")
    origin.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "discovery_targets",
        sa.Column(
            "origin",
            postgresql.ENUM(name="discovery_target_origin", create_type=False),
            nullable=False,
            server_default="USER",
        ),
    )
    op.add_column("discovery_targets", sa.Column("source_label", sa.String(length=255)))
    op.create_index(
        "ix_discovery_targets_origin_status",
        "discovery_targets",
        ["origin", "status"],
    )

    op.add_column(
        "source_candidates",
        sa.Column("last_revalidated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "source_candidates",
        sa.Column(
            "revalidation_failure_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("source_candidates", "revalidation_failure_count")
    op.drop_column("source_candidates", "last_revalidated_at")
    op.drop_index("ix_discovery_targets_origin_status", table_name="discovery_targets")
    op.drop_column("discovery_targets", "source_label")
    op.drop_column("discovery_targets", "origin")
    postgresql.ENUM(name="discovery_target_origin").drop(op.get_bind(), checkfirst=True)
