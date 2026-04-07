"""add contract type and client fields

Revision ID: 6a2e1d4c9b8f
Revises: 3c7e5d9a1f20
Create Date: 2026-04-04 13:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6a2e1d4c9b8f"
down_revision = "3c7e5d9a1f20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("contracts", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "contract_type",
                sa.String(length=30),
                nullable=False,
                server_default="vendor_contract",
            )
        )
        batch_op.add_column(
            sa.Column("client_name", sa.String(length=255), nullable=True)
        )
        batch_op.alter_column("vendor_id", existing_type=sa.Integer(), nullable=True)

    op.execute(
        sa.text(
            "UPDATE contracts SET contract_type = 'vendor_contract' WHERE contract_type IS NULL"
        )
    )

    with op.batch_alter_table("contracts", schema=None) as batch_op:
        batch_op.alter_column(
            "contract_type",
            existing_type=sa.String(length=30),
            server_default=None,
        )


def downgrade() -> None:
    with op.batch_alter_table("contracts", schema=None) as batch_op:
        batch_op.drop_column("client_name")
        batch_op.drop_column("contract_type")
        batch_op.alter_column("vendor_id", existing_type=sa.Integer(), nullable=False)
