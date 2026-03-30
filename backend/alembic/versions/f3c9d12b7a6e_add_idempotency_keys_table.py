"""add idempotency keys table

Revision ID: f3c9d12b7a6e
Revises: e4b0a2d1c8f3
Create Date: 2026-03-26 17:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f3c9d12b7a6e"
down_revision = "e4b0a2d1c8f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_key", sa.String(length=255), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("request_method", sa.String(length=10), nullable=False),
        sa.Column("request_path", sa.String(length=500), nullable=False),
        sa.Column("request_hash", sa.String(length=128), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'processing'"),
        ),
        sa.Column("response_status_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "actor_key",
            "key",
            "request_method",
            "request_path",
            name="uq_idempotency_keys_actor_key_method_path",
        ),
    )
    op.create_index(op.f("ix_idempotency_keys_id"), "idempotency_keys", ["id"], unique=False)
    op.create_index(
        op.f("ix_idempotency_keys_actor_key"),
        "idempotency_keys",
        ["actor_key"],
        unique=False,
    )
    op.create_index(op.f("ix_idempotency_keys_key"), "idempotency_keys", ["key"], unique=False)
    op.create_index(
        op.f("ix_idempotency_keys_request_method"),
        "idempotency_keys",
        ["request_method"],
        unique=False,
    )
    op.create_index(
        op.f("ix_idempotency_keys_request_path"),
        "idempotency_keys",
        ["request_path"],
        unique=False,
    )
    op.create_index(
        op.f("ix_idempotency_keys_status"),
        "idempotency_keys",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_idempotency_keys_status"), table_name="idempotency_keys")
    op.drop_index(op.f("ix_idempotency_keys_request_path"), table_name="idempotency_keys")
    op.drop_index(op.f("ix_idempotency_keys_request_method"), table_name="idempotency_keys")
    op.drop_index(op.f("ix_idempotency_keys_key"), table_name="idempotency_keys")
    op.drop_index(op.f("ix_idempotency_keys_actor_key"), table_name="idempotency_keys")
    op.drop_index(op.f("ix_idempotency_keys_id"), table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
