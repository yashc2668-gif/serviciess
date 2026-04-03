"""add site expenses module

Revision ID: 3f9a4d7c2b11
Revises: e5b3a8f2c7d1
Create Date: 2026-04-03 09:25:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3f9a4d7c2b11"
down_revision = "e5b3a8f2c7d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_expenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("expense_no", sa.String(length=100), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=True),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("expense_head", sa.String(length=100), nullable=False),
        sa.Column("payee_name", sa.String(length=255), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("payment_mode", sa.String(length=30), nullable=True),
        sa.Column("reference_no", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_by", sa.Integer(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("lock_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.CheckConstraint("amount > 0", name="ck_site_expenses_amount_positive"),
        sa.CheckConstraint("status IN ('draft', 'approved', 'paid')", name="ck_site_expenses_status_valid"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["paid_by"], ["users.id"]),
    )
    op.create_index("ix_site_expenses_expense_no", "site_expenses", ["expense_no"], unique=True)
    op.create_index("ix_site_expenses_project_id", "site_expenses", ["project_id"])
    op.create_index("ix_site_expenses_vendor_id", "site_expenses", ["vendor_id"])
    op.create_index("ix_site_expenses_expense_date", "site_expenses", ["expense_date"])
    op.create_index("ix_site_expenses_expense_head", "site_expenses", ["expense_head"])
    op.create_index("ix_site_expenses_status", "site_expenses", ["status"])


def downgrade() -> None:
    op.drop_index("ix_site_expenses_status", table_name="site_expenses")
    op.drop_index("ix_site_expenses_expense_head", table_name="site_expenses")
    op.drop_index("ix_site_expenses_expense_date", table_name="site_expenses")
    op.drop_index("ix_site_expenses_vendor_id", table_name="site_expenses")
    op.drop_index("ix_site_expenses_project_id", table_name="site_expenses")
    op.drop_index("ix_site_expenses_expense_no", table_name="site_expenses")
    op.drop_table("site_expenses")
