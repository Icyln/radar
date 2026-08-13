"""Phase 2 monitoring core and Phase 3 API domain.

Revision ID: 0002_phase2_phase3
Revises: 0001_phase0_phase1
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_phase2_phase3"
down_revision: str | None = "0001_phase0_phase1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_job_state_type = postgresql.ENUM("SAVED", "IGNORED", name="user_job_state_type")


def upgrade() -> None:
    bind = op.get_bind()
    user_job_state_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "job_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("job_titles", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("locations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("work_modes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("excluded_keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_profiles_user_id", "job_profiles", ["user_id"])
    op.create_index("ix_job_profiles_user_enabled", "job_profiles", ["user_id", "enabled"])

    op.create_table(
        "job_matches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("job_profile_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("match_reason", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_profile_id"], ["job_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_profile_id", "job_id", name="uq_job_match_profile_job"),
    )
    op.create_index("ix_job_matches_job_id", "job_matches", ["job_id"])
    op.create_index("ix_job_matches_job_profile_id", "job_matches", ["job_profile_id"])
    op.create_index("ix_job_matches_user_id", "job_matches", ["user_id"])
    op.create_index("ix_job_matches_user_matched", "job_matches", ["user_id", "matched_at"])

    op.create_table(
        "user_job_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column(
            "state",
            postgresql.ENUM("SAVED", "IGNORED", name="user_job_state_type", create_type=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "job_id", name="uq_user_job_state_user_job"),
    )
    op.create_index("ix_user_job_states_job_id", "user_job_states", ["job_id"])
    op.create_index("ix_user_job_states_user_id", "user_job_states", ["user_id"])
    op.create_index("ix_user_job_states_user_state", "user_job_states", ["user_id", "state"])

    op.create_table(
        "telegram_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_chat_id"),
        sa.UniqueConstraint("telegram_user_id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_telegram_connections_user_id", "telegram_connections", ["user_id"])

    op.create_table(
        "telegram_link_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_telegram_link_tokens_user_id", "telegram_link_tokens", ["user_id"])
    op.create_index("ix_telegram_link_tokens_token_hash", "telegram_link_tokens", ["token_hash"])
    op.create_index("ix_telegram_link_tokens_expires_at", "telegram_link_tokens", ["expires_at"])

    op.add_column("notifications", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_notifications_user_id_users",
        "notifications",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_user_status", "notifications", ["user_id", "status"])
    op.create_unique_constraint(
        "uq_notification_user_job_channel",
        "notifications",
        ["user_id", "job_id", "channel"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_notification_user_job_channel", "notifications", type_="unique")
    op.drop_index("ix_notifications_user_status", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_constraint("fk_notifications_user_id_users", "notifications", type_="foreignkey")
    op.drop_column("notifications", "user_id")

    op.drop_index("ix_telegram_link_tokens_expires_at", table_name="telegram_link_tokens")
    op.drop_index("ix_telegram_link_tokens_token_hash", table_name="telegram_link_tokens")
    op.drop_index("ix_telegram_link_tokens_user_id", table_name="telegram_link_tokens")
    op.drop_table("telegram_link_tokens")
    op.drop_index("ix_telegram_connections_user_id", table_name="telegram_connections")
    op.drop_table("telegram_connections")
    op.drop_index("ix_user_job_states_user_state", table_name="user_job_states")
    op.drop_index("ix_user_job_states_user_id", table_name="user_job_states")
    op.drop_index("ix_user_job_states_job_id", table_name="user_job_states")
    op.drop_table("user_job_states")
    op.drop_index("ix_job_matches_user_matched", table_name="job_matches")
    op.drop_index("ix_job_matches_user_id", table_name="job_matches")
    op.drop_index("ix_job_matches_job_profile_id", table_name="job_matches")
    op.drop_index("ix_job_matches_job_id", table_name="job_matches")
    op.drop_table("job_matches")
    op.drop_index("ix_job_profiles_user_enabled", table_name="job_profiles")
    op.drop_index("ix_job_profiles_user_id", table_name="job_profiles")
    op.drop_table("job_profiles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    user_job_state_type.drop(op.get_bind(), checkfirst=True)
