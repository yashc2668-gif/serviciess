"""add bbs module

Revision ID: 3c7e5d9a1f20
Revises: 3f9a4d7c2b11
Create Date: 2026-04-04 09:45:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3c7e5d9a1f20"
down_revision = "3f9a4d7c2b11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bar_bending_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contract_id", sa.Integer(), nullable=False),
        sa.Column("drawing_no", sa.String(length=120), nullable=False),
        sa.Column("member_location", sa.String(length=255), nullable=False),
        sa.Column("bar_mark", sa.String(length=80), nullable=False),
        sa.Column("dia_mm", sa.Numeric(precision=10, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("cut_length_mm", sa.Numeric(precision=12, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("shape_code", sa.String(length=60), nullable=True),
        sa.Column("nos", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("unit_weight", sa.Numeric(precision=12, scale=3), nullable=False, server_default=sa.text("0")),
        sa.Column("total_weight", sa.Numeric(precision=14, scale=3), nullable=False, server_default=sa.text("0")),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("lock_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bar_bending_schedules_id", "bar_bending_schedules", ["id"])
    op.create_index("ix_bar_bending_schedules_contract_id", "bar_bending_schedules", ["contract_id"])
    op.create_index("ix_bar_bending_schedules_drawing_no", "bar_bending_schedules", ["drawing_no"])
    op.create_index("ix_bar_bending_schedules_bar_mark", "bar_bending_schedules", ["bar_mark"])


def downgrade() -> None:
    op.drop_index("ix_bar_bending_schedules_bar_mark", table_name="bar_bending_schedules")
    op.drop_index("ix_bar_bending_schedules_drawing_no", table_name="bar_bending_schedules")
    op.drop_index("ix_bar_bending_schedules_contract_id", table_name="bar_bending_schedules")
    op.drop_index("ix_bar_bending_schedules_id", table_name="bar_bending_schedules")
    op.drop_table("bar_bending_schedules")
