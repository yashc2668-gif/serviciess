"""add labour bill items table

Revision ID: b13d7e4a9c2f
Revises: a2b7c4d9e6f1
Create Date: 2026-03-26 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b13d7e4a9c2f"
down_revision = "a2b7c4d9e6f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "labour_bill_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bill_id", sa.Integer(), nullable=False),
        sa.Column("attendance_id", sa.Integer(), nullable=True),
        sa.Column("labour_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column(
            "quantity",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "rate",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "amount",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("quantity >= 0", name="ck_labour_bill_items_quantity_non_negative"),
        sa.CheckConstraint("rate >= 0", name="ck_labour_bill_items_rate_non_negative"),
        sa.CheckConstraint("amount >= 0", name="ck_labour_bill_items_amount_non_negative"),
        sa.ForeignKeyConstraint(["bill_id"], ["labour_bills.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["attendance_id"], ["labour_attendances.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["labour_id"], ["labours.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_labour_bill_items_id"), "labour_bill_items", ["id"], unique=False)
    op.create_index(
        op.f("ix_labour_bill_items_bill_id"),
        "labour_bill_items",
        ["bill_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_bill_items_attendance_id"),
        "labour_bill_items",
        ["attendance_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_bill_items_labour_id"),
        "labour_bill_items",
        ["labour_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_labour_bill_items_labour_id"), table_name="labour_bill_items")
    op.drop_index(op.f("ix_labour_bill_items_attendance_id"), table_name="labour_bill_items")
    op.drop_index(op.f("ix_labour_bill_items_bill_id"), table_name="labour_bill_items")
    op.drop_index(op.f("ix_labour_bill_items_id"), table_name="labour_bill_items")
    op.drop_table("labour_bill_items")
