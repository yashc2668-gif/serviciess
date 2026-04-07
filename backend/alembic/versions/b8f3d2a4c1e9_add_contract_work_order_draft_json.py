"""add contract work order draft json

Revision ID: b8f3d2a4c1e9
Revises: 6a2e1d4c9b8f
Create Date: 2026-04-06 15:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b8f3d2a4c1e9"
down_revision = "6a2e1d4c9b8f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("contracts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("work_order_draft", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("contracts", schema=None) as batch_op:
        batch_op.drop_column("work_order_draft")
