"""add lock version columns for concurrency control

Revision ID: 1d3f5a7b9c2e
Revises: 7c2ef1a4b6d8
Create Date: 2026-03-26 21:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1d3f5a7b9c2e"
down_revision = "7c2ef1a4b6d8"
branch_labels = None
depends_on = None


LOCKED_TABLES = (
    "materials",
    "labours",
    "material_requisitions",
    "material_receipts",
    "material_issues",
    "material_stock_adjustments",
    "labour_attendances",
    "labour_bills",
    "labour_advances",
    "payments",
    "ra_bills",
)


def upgrade() -> None:
    for table_name in LOCKED_TABLES:
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "lock_version",
                    sa.Integer(),
                    nullable=False,
                    server_default=sa.text("1"),
                )
            )


def downgrade() -> None:
    for table_name in reversed(LOCKED_TABLES):
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.drop_column("lock_version")
