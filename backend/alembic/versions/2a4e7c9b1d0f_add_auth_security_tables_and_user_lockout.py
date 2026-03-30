"""add auth security tables and user lockout fields

Revision ID: 2a4e7c9b1d0f
Revises: 1d3f5a7b9c2e
Create Date: 2026-03-28 08:35:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "2a4e7c9b1d0f"
down_revision: str | None = "1d3f5a7b9c2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("users", sa.Column("last_failed_login_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_locked_until", "users", ["locked_until"], unique=False)

    op.create_table(
        "refresh_token_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.String(length=64), nullable=False),
        sa.Column("token_jti", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reuse_detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_jti", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_refresh_token_sessions_user_id", "refresh_token_sessions", ["user_id"], unique=False)
    op.create_index("ix_refresh_token_sessions_family_id", "refresh_token_sessions", ["family_id"], unique=False)
    op.create_index("ix_refresh_token_sessions_token_jti", "refresh_token_sessions", ["token_jti"], unique=True)
    op.create_index("ix_refresh_token_sessions_expires_at", "refresh_token_sessions", ["expires_at"], unique=False)
    op.create_index("ix_refresh_token_sessions_revoked_at", "refresh_token_sessions", ["revoked_at"], unique=False)

    op.create_table(
        "password_reset_otps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("otp_hash", sa.String(length=64), nullable=False),
        sa.Column("attempts_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_ip", sa.String(length=64), nullable=True),
        sa.Column("requested_user_agent", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_password_reset_otps_user_id", "password_reset_otps", ["user_id"], unique=False)
    op.create_index("ix_password_reset_otps_expires_at", "password_reset_otps", ["expires_at"], unique=False)
    op.create_index("ix_password_reset_otps_consumed_at", "password_reset_otps", ["consumed_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_password_reset_otps_consumed_at", table_name="password_reset_otps")
    op.drop_index("ix_password_reset_otps_expires_at", table_name="password_reset_otps")
    op.drop_index("ix_password_reset_otps_user_id", table_name="password_reset_otps")
    op.drop_table("password_reset_otps")

    op.drop_index("ix_refresh_token_sessions_revoked_at", table_name="refresh_token_sessions")
    op.drop_index("ix_refresh_token_sessions_expires_at", table_name="refresh_token_sessions")
    op.drop_index("ix_refresh_token_sessions_token_jti", table_name="refresh_token_sessions")
    op.drop_index("ix_refresh_token_sessions_family_id", table_name="refresh_token_sessions")
    op.drop_index("ix_refresh_token_sessions_user_id", table_name="refresh_token_sessions")
    op.drop_table("refresh_token_sessions")

    op.drop_index("ix_users_locked_until", table_name="users")
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "last_failed_login_at")
    op.drop_column("users", "failed_login_attempts")
