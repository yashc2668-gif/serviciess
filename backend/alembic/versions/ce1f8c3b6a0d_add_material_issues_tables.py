"""add material issues tables

Revision ID: ce1f8c3b6a0d
Revises: b7d4d1f85c2a
Create Date: 2026-03-26 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ce1f8c3b6a0d"
down_revision = "b7d4d1f85c2a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "material_issues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("issue_no", sa.String(length=100), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("issued_by", sa.Integer(), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'issued'"),
        ),
        sa.Column("site_name", sa.String(length=255), nullable=True),
        sa.Column("activity_name", sa.String(length=255), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column(
            "total_amount",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["issued_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_material_issues_id"), "material_issues", ["id"], unique=False)
    op.create_index(
        op.f("ix_material_issues_issue_no"),
        "material_issues",
        ["issue_no"],
        unique=True,
    )
    op.create_index(
        op.f("ix_material_issues_project_id"),
        "material_issues",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_issues_issued_by"),
        "material_issues",
        ["issued_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_issues_issue_date"),
        "material_issues",
        ["issue_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_issues_status"),
        "material_issues",
        ["status"],
        unique=False,
    )

    op.create_table(
        "material_issue_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("issue_id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column(
            "issued_qty",
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
        sa.CheckConstraint("issued_qty > 0", name="ck_material_issue_items_issued_qty_positive"),
        sa.CheckConstraint("unit_rate >= 0", name="ck_material_issue_items_unit_rate_non_negative"),
        sa.CheckConstraint("line_amount >= 0", name="ck_material_issue_items_line_amount_non_negative"),
        sa.ForeignKeyConstraint(["issue_id"], ["material_issues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "issue_id",
            "material_id",
            name="uq_material_issue_items_issue_material",
        ),
    )
    op.create_index(
        op.f("ix_material_issue_items_id"),
        "material_issue_items",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_issue_items_issue_id"),
        "material_issue_items",
        ["issue_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_issue_items_material_id"),
        "material_issue_items",
        ["material_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_material_issue_items_material_id"),
        table_name="material_issue_items",
    )
    op.drop_index(
        op.f("ix_material_issue_items_issue_id"),
        table_name="material_issue_items",
    )
    op.drop_index(
        op.f("ix_material_issue_items_id"),
        table_name="material_issue_items",
    )
    op.drop_table("material_issue_items")

    op.drop_index(op.f("ix_material_issues_status"), table_name="material_issues")
    op.drop_index(op.f("ix_material_issues_issue_date"), table_name="material_issues")
    op.drop_index(op.f("ix_material_issues_issued_by"), table_name="material_issues")
    op.drop_index(op.f("ix_material_issues_project_id"), table_name="material_issues")
    op.drop_index(op.f("ix_material_issues_issue_no"), table_name="material_issues")
    op.drop_index(op.f("ix_material_issues_id"), table_name="material_issues")
    op.drop_table("material_issues")
