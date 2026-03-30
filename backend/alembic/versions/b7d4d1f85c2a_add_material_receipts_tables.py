"""add material receipts tables

Revision ID: b7d4d1f85c2a
Revises: 9f4a1a72d6bc
Create Date: 2026-03-26 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7d4d1f85c2a"
down_revision = "9f4a1a72d6bc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "material_receipts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("receipt_no", sa.String(length=100), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("received_by", sa.Integer(), nullable=False),
        sa.Column("receipt_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'received'"),
        ),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column(
            "total_amount",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["received_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_material_receipts_id"), "material_receipts", ["id"], unique=False)
    op.create_index(
        op.f("ix_material_receipts_receipt_no"),
        "material_receipts",
        ["receipt_no"],
        unique=True,
    )
    op.create_index(
        op.f("ix_material_receipts_vendor_id"),
        "material_receipts",
        ["vendor_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_receipts_project_id"),
        "material_receipts",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_receipts_received_by"),
        "material_receipts",
        ["received_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_receipts_receipt_date"),
        "material_receipts",
        ["receipt_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_receipts_status"),
        "material_receipts",
        ["status"],
        unique=False,
    )

    op.create_table(
        "material_receipt_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("receipt_id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column(
            "received_qty",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "unit_rate",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "line_amount",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("received_qty > 0", name="ck_material_receipt_items_received_qty_positive"),
        sa.CheckConstraint("unit_rate >= 0", name="ck_material_receipt_items_unit_rate_non_negative"),
        sa.CheckConstraint("line_amount >= 0", name="ck_material_receipt_items_line_amount_non_negative"),
        sa.ForeignKeyConstraint(["receipt_id"], ["material_receipts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "receipt_id",
            "material_id",
            name="uq_material_receipt_items_receipt_material",
        ),
    )
    op.create_index(
        op.f("ix_material_receipt_items_id"),
        "material_receipt_items",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_receipt_items_receipt_id"),
        "material_receipt_items",
        ["receipt_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_receipt_items_material_id"),
        "material_receipt_items",
        ["material_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_material_receipt_items_material_id"),
        table_name="material_receipt_items",
    )
    op.drop_index(
        op.f("ix_material_receipt_items_receipt_id"),
        table_name="material_receipt_items",
    )
    op.drop_index(
        op.f("ix_material_receipt_items_id"),
        table_name="material_receipt_items",
    )
    op.drop_table("material_receipt_items")

    op.drop_index(op.f("ix_material_receipts_status"), table_name="material_receipts")
    op.drop_index(op.f("ix_material_receipts_receipt_date"), table_name="material_receipts")
    op.drop_index(op.f("ix_material_receipts_received_by"), table_name="material_receipts")
    op.drop_index(op.f("ix_material_receipts_project_id"), table_name="material_receipts")
    op.drop_index(op.f("ix_material_receipts_vendor_id"), table_name="material_receipts")
    op.drop_index(op.f("ix_material_receipts_receipt_no"), table_name="material_receipts")
    op.drop_index(op.f("ix_material_receipts_id"), table_name="material_receipts")
    op.drop_table("material_receipts")
