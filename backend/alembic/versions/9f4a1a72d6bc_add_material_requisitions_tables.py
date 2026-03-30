"""add material requisitions tables

Revision ID: 9f4a1a72d6bc
Revises: c83bdc4e1a27
Create Date: 2026-03-26 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9f4a1a72d6bc"
down_revision = "c83bdc4e1a27"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "material_requisitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("requisition_no", sa.String(length=100), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("requested_by", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_material_requisitions_id"),
        "material_requisitions",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_requisitions_requisition_no"),
        "material_requisitions",
        ["requisition_no"],
        unique=True,
    )
    op.create_index(
        op.f("ix_material_requisitions_project_id"),
        "material_requisitions",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_requisitions_requested_by"),
        "material_requisitions",
        ["requested_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_requisitions_status"),
        "material_requisitions",
        ["status"],
        unique=False,
    )

    op.create_table(
        "material_requisition_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("requisition_id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column(
            "requested_qty",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "approved_qty",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "issued_qty",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("requested_qty > 0", name="ck_material_req_items_requested_qty_positive"),
        sa.CheckConstraint("approved_qty >= 0", name="ck_material_req_items_approved_qty_non_negative"),
        sa.CheckConstraint("issued_qty >= 0", name="ck_material_req_items_issued_qty_non_negative"),
        sa.CheckConstraint(
            "approved_qty <= requested_qty",
            name="ck_material_req_items_approved_qty_lte_requested_qty",
        ),
        sa.CheckConstraint(
            "issued_qty <= approved_qty",
            name="ck_material_req_items_issued_qty_lte_approved_qty",
        ),
        sa.ForeignKeyConstraint(
            ["requisition_id"],
            ["material_requisitions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "requisition_id",
            "material_id",
            name="uq_material_requisition_items_requisition_material",
        ),
    )
    op.create_index(
        op.f("ix_material_requisition_items_id"),
        "material_requisition_items",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_requisition_items_requisition_id"),
        "material_requisition_items",
        ["requisition_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_requisition_items_material_id"),
        "material_requisition_items",
        ["material_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_material_requisition_items_material_id"),
        table_name="material_requisition_items",
    )
    op.drop_index(
        op.f("ix_material_requisition_items_requisition_id"),
        table_name="material_requisition_items",
    )
    op.drop_index(
        op.f("ix_material_requisition_items_id"),
        table_name="material_requisition_items",
    )
    op.drop_table("material_requisition_items")

    op.drop_index(
        op.f("ix_material_requisitions_status"),
        table_name="material_requisitions",
    )
    op.drop_index(
        op.f("ix_material_requisitions_requested_by"),
        table_name="material_requisitions",
    )
    op.drop_index(
        op.f("ix_material_requisitions_project_id"),
        table_name="material_requisitions",
    )
    op.drop_index(
        op.f("ix_material_requisitions_requisition_no"),
        table_name="material_requisitions",
    )
    op.drop_index(
        op.f("ix_material_requisitions_id"),
        table_name="material_requisitions",
    )
    op.drop_table("material_requisitions")
