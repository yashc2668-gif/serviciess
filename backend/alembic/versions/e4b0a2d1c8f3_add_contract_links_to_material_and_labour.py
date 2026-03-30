"""add contract links to material and labour records

Revision ID: e4b0a2d1c8f3
Revises: d9c6f2a1b4e7
Create Date: 2026-03-26 15:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e4b0a2d1c8f3"
down_revision = "d9c6f2a1b4e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("material_requisitions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("contract_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            op.f("ix_material_requisitions_contract_id"),
            ["contract_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_material_requisitions_contract_id",
            "contracts",
            ["contract_id"],
            ["id"],
        )

    with op.batch_alter_table("material_issues", schema=None) as batch_op:
        batch_op.add_column(sa.Column("contract_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            op.f("ix_material_issues_contract_id"),
            ["contract_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_material_issues_contract_id",
            "contracts",
            ["contract_id"],
            ["id"],
        )

    with op.batch_alter_table("labour_bills", schema=None) as batch_op:
        batch_op.add_column(sa.Column("contract_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            op.f("ix_labour_bills_contract_id"),
            ["contract_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_labour_bills_contract_id",
            "contracts",
            ["contract_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("labour_bills", schema=None) as batch_op:
        batch_op.drop_constraint("fk_labour_bills_contract_id", type_="foreignkey")
        batch_op.drop_index(op.f("ix_labour_bills_contract_id"))
        batch_op.drop_column("contract_id")

    with op.batch_alter_table("material_issues", schema=None) as batch_op:
        batch_op.drop_constraint("fk_material_issues_contract_id", type_="foreignkey")
        batch_op.drop_index(op.f("ix_material_issues_contract_id"))
        batch_op.drop_column("contract_id")

    with op.batch_alter_table("material_requisitions", schema=None) as batch_op:
        batch_op.drop_constraint("fk_material_requisitions_contract_id", type_="foreignkey")
        batch_op.drop_index(op.f("ix_material_requisitions_contract_id"))
        batch_op.drop_column("contract_id")
