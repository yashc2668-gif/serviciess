"""add inventory transactions ledger

Revision ID: f1a9b63d42ee
Revises: ce1f8c3b6a0d
Create Date: 2026-03-26 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f1a9b63d42ee"
down_revision = "ce1f8c3b6a0d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("transaction_type", sa.String(length=50), nullable=False),
        sa.Column(
            "qty_in",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "qty_out",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "balance_after",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("reference_type", sa.String(length=50), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("qty_in >= 0", name="ck_inventory_txn_qty_in_non_negative"),
        sa.CheckConstraint("qty_out >= 0", name="ck_inventory_txn_qty_out_non_negative"),
        sa.CheckConstraint(
            "qty_in + qty_out > 0",
            name="ck_inventory_txn_qty_presence",
        ),
        sa.CheckConstraint(
            "NOT (qty_in > 0 AND qty_out > 0)",
            name="ck_inventory_txn_single_direction",
        ),
        sa.CheckConstraint(
            "balance_after >= 0",
            name="ck_inventory_txn_balance_after_non_negative",
        ),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_inventory_transactions_id"),
        "inventory_transactions",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_transactions_material_id"),
        "inventory_transactions",
        ["material_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_transactions_project_id"),
        "inventory_transactions",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_transactions_transaction_type"),
        "inventory_transactions",
        ["transaction_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_transactions_reference_type"),
        "inventory_transactions",
        ["reference_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_transactions_reference_id"),
        "inventory_transactions",
        ["reference_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_transactions_transaction_date"),
        "inventory_transactions",
        ["transaction_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_inventory_transactions_transaction_date"),
        table_name="inventory_transactions",
    )
    op.drop_index(
        op.f("ix_inventory_transactions_reference_id"),
        table_name="inventory_transactions",
    )
    op.drop_index(
        op.f("ix_inventory_transactions_reference_type"),
        table_name="inventory_transactions",
    )
    op.drop_index(
        op.f("ix_inventory_transactions_transaction_type"),
        table_name="inventory_transactions",
    )
    op.drop_index(
        op.f("ix_inventory_transactions_project_id"),
        table_name="inventory_transactions",
    )
    op.drop_index(
        op.f("ix_inventory_transactions_material_id"),
        table_name="inventory_transactions",
    )
    op.drop_index(
        op.f("ix_inventory_transactions_id"),
        table_name="inventory_transactions",
    )
    op.drop_table("inventory_transactions")
