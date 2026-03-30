"""add material master table

Revision ID: c83bdc4e1a27
Revises: 0a6f2f338c91
Create Date: 2026-03-26 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c83bdc4e1a27"
down_revision = "0a6f2f338c91"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "materials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_code", sa.String(length=50), nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("unit", sa.String(length=30), nullable=False),
        sa.Column(
            "reorder_level",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "default_rate",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "current_stock",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("reorder_level >= 0", name="ck_materials_reorder_level_non_negative"),
        sa.CheckConstraint("default_rate >= 0", name="ck_materials_default_rate_non_negative"),
        sa.CheckConstraint("current_stock >= 0", name="ck_materials_current_stock_non_negative"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_materials_id"), "materials", ["id"], unique=False)
    op.create_index(op.f("ix_materials_item_code"), "materials", ["item_code"], unique=True)
    op.create_index(op.f("ix_materials_item_name"), "materials", ["item_name"], unique=False)
    op.create_index(op.f("ix_materials_category"), "materials", ["category"], unique=False)
    op.create_index(op.f("ix_materials_is_active"), "materials", ["is_active"], unique=False)
    op.create_index(op.f("ix_materials_company_id"), "materials", ["company_id"], unique=False)
    op.create_index(op.f("ix_materials_project_id"), "materials", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_materials_project_id"), table_name="materials")
    op.drop_index(op.f("ix_materials_company_id"), table_name="materials")
    op.drop_index(op.f("ix_materials_is_active"), table_name="materials")
    op.drop_index(op.f("ix_materials_category"), table_name="materials")
    op.drop_index(op.f("ix_materials_item_name"), table_name="materials")
    op.drop_index(op.f("ix_materials_item_code"), table_name="materials")
    op.drop_index(op.f("ix_materials_id"), table_name="materials")
    op.drop_table("materials")
