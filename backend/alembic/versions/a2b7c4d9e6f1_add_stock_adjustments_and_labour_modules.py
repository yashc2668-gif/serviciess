"""add stock adjustments and labour modules

Revision ID: a2b7c4d9e6f1
Revises: f1a9b63d42ee
Create Date: 2026-03-26 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a2b7c4d9e6f1"
down_revision = "f1a9b63d42ee"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "material_stock_adjustments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("adjustment_no", sa.String(length=100), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("adjusted_by", sa.Integer(), nullable=False),
        sa.Column("adjustment_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'posted'"),
        ),
        sa.Column("reason", sa.String(length=255), nullable=True),
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
        sa.ForeignKeyConstraint(["adjusted_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_material_stock_adjustments_id"),
        "material_stock_adjustments",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_stock_adjustments_adjustment_no"),
        "material_stock_adjustments",
        ["adjustment_no"],
        unique=True,
    )
    op.create_index(
        op.f("ix_material_stock_adjustments_project_id"),
        "material_stock_adjustments",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_stock_adjustments_adjusted_by"),
        "material_stock_adjustments",
        ["adjusted_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_stock_adjustments_adjustment_date"),
        "material_stock_adjustments",
        ["adjustment_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_stock_adjustments_status"),
        "material_stock_adjustments",
        ["status"],
        unique=False,
    )

    op.create_table(
        "material_stock_adjustment_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("adjustment_id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("qty_change", sa.Numeric(precision=14, scale=3), nullable=False),
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
        sa.CheckConstraint(
            "qty_change <> 0",
            name="ck_material_stock_adj_items_qty_change_non_zero",
        ),
        sa.CheckConstraint(
            "unit_rate >= 0",
            name="ck_material_stock_adj_items_unit_rate_non_negative",
        ),
        sa.CheckConstraint(
            "line_amount >= 0",
            name="ck_material_stock_adj_items_line_amount_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["adjustment_id"],
            ["material_stock_adjustments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "adjustment_id",
            "material_id",
            name="uq_material_stock_adjustment_items_adjustment_material",
        ),
    )
    op.create_index(
        op.f("ix_material_stock_adjustment_items_id"),
        "material_stock_adjustment_items",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_stock_adjustment_items_adjustment_id"),
        "material_stock_adjustment_items",
        ["adjustment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_stock_adjustment_items_material_id"),
        "material_stock_adjustment_items",
        ["material_id"],
        unique=False,
    )

    op.create_table(
        "labour_contractors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contractor_code", sa.String(length=50), nullable=False),
        sa.Column("contractor_name", sa.String(length=255), nullable=False),
        sa.Column("gang_name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_labour_contractors_id"),
        "labour_contractors",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_contractors_contractor_code"),
        "labour_contractors",
        ["contractor_code"],
        unique=True,
    )
    op.create_index(
        op.f("ix_labour_contractors_contractor_name"),
        "labour_contractors",
        ["contractor_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_contractors_is_active"),
        "labour_contractors",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "labours",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("labour_code", sa.String(length=50), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("skill_type", sa.String(length=100), nullable=True),
        sa.Column(
            "default_wage_rate",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("unit", sa.String(length=20), nullable=False, server_default=sa.text("'day'")),
        sa.Column("contractor_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("default_wage_rate >= 0", name="ck_labours_default_wage_rate_non_negative"),
        sa.ForeignKeyConstraint(["contractor_id"], ["labour_contractors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_labours_id"), "labours", ["id"], unique=False)
    op.create_index(op.f("ix_labours_labour_code"), "labours", ["labour_code"], unique=True)
    op.create_index(op.f("ix_labours_full_name"), "labours", ["full_name"], unique=False)
    op.create_index(op.f("ix_labours_skill_type"), "labours", ["skill_type"], unique=False)
    op.create_index(op.f("ix_labours_contractor_id"), "labours", ["contractor_id"], unique=False)
    op.create_index(op.f("ix_labours_is_active"), "labours", ["is_active"], unique=False)

    op.create_table(
        "labour_attendances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("muster_no", sa.String(length=100), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("marked_by", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column(
            "total_wage",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("total_wage >= 0", name="ck_labour_attendances_total_wage_non_negative"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["marked_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_labour_attendances_id"),
        "labour_attendances",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_attendances_muster_no"),
        "labour_attendances",
        ["muster_no"],
        unique=True,
    )
    op.create_index(
        op.f("ix_labour_attendances_project_id"),
        "labour_attendances",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_attendances_marked_by"),
        "labour_attendances",
        ["marked_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_attendances_attendance_date"),
        "labour_attendances",
        ["attendance_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_attendances_status"),
        "labour_attendances",
        ["status"],
        unique=False,
    )

    op.create_table(
        "labour_attendance_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("attendance_id", sa.Integer(), nullable=False),
        sa.Column("labour_id", sa.Integer(), nullable=False),
        sa.Column(
            "present_days",
            sa.Numeric(precision=8, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "overtime_hours",
            sa.Numeric(precision=8, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "wage_rate",
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
        sa.CheckConstraint(
            "present_days > 0",
            name="ck_labour_attendance_items_present_days_positive",
        ),
        sa.CheckConstraint(
            "overtime_hours >= 0",
            name="ck_labour_attendance_items_overtime_non_negative",
        ),
        sa.CheckConstraint(
            "wage_rate >= 0",
            name="ck_labour_attendance_items_wage_rate_non_negative",
        ),
        sa.CheckConstraint(
            "line_amount >= 0",
            name="ck_labour_attendance_items_line_amount_non_negative",
        ),
        sa.ForeignKeyConstraint(["attendance_id"], ["labour_attendances.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["labour_id"], ["labours.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "attendance_id",
            "labour_id",
            name="uq_labour_attendance_items_attendance_labour",
        ),
    )
    op.create_index(
        op.f("ix_labour_attendance_items_id"),
        "labour_attendance_items",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_attendance_items_attendance_id"),
        "labour_attendance_items",
        ["attendance_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_attendance_items_labour_id"),
        "labour_attendance_items",
        ["labour_id"],
        unique=False,
    )

    op.create_table(
        "labour_productivities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("labour_id", sa.Integer(), nullable=True),
        sa.Column("activity_name", sa.String(length=255), nullable=False),
        sa.Column(
            "quantity",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("unit", sa.String(length=30), nullable=False, server_default=sa.text("'unit'")),
        sa.Column("productivity_date", sa.Date(), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("quantity > 0", name="ck_labour_productivities_quantity_positive"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["labour_id"], ["labours.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_labour_productivities_id"),
        "labour_productivities",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_productivities_project_id"),
        "labour_productivities",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_productivities_labour_id"),
        "labour_productivities",
        ["labour_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_productivities_activity_name"),
        "labour_productivities",
        ["activity_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_productivities_productivity_date"),
        "labour_productivities",
        ["productivity_date"],
        unique=False,
    )

    op.create_table(
        "labour_bills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bill_no", sa.String(length=100), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("contractor_id", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column(
            "gross_amount",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "deductions",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "net_amount",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("gross_amount >= 0", name="ck_labour_bills_gross_non_negative"),
        sa.CheckConstraint("deductions >= 0", name="ck_labour_bills_deductions_non_negative"),
        sa.CheckConstraint("net_amount >= 0", name="ck_labour_bills_net_non_negative"),
        sa.CheckConstraint("deductions <= gross_amount", name="ck_labour_bills_deductions_lte_gross"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["contractor_id"], ["labour_contractors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_labour_bills_id"), "labour_bills", ["id"], unique=False)
    op.create_index(op.f("ix_labour_bills_bill_no"), "labour_bills", ["bill_no"], unique=True)
    op.create_index(op.f("ix_labour_bills_project_id"), "labour_bills", ["project_id"], unique=False)
    op.create_index(
        op.f("ix_labour_bills_contractor_id"),
        "labour_bills",
        ["contractor_id"],
        unique=False,
    )
    op.create_index(op.f("ix_labour_bills_status"), "labour_bills", ["status"], unique=False)

    op.create_table(
        "labour_advances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("advance_no", sa.String(length=100), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("contractor_id", sa.Integer(), nullable=False),
        sa.Column("advance_date", sa.Date(), nullable=False),
        sa.Column(
            "amount",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "recovered_amount",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "balance_amount",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("amount > 0", name="ck_labour_advances_amount_positive"),
        sa.CheckConstraint(
            "recovered_amount >= 0",
            name="ck_labour_advances_recovered_non_negative",
        ),
        sa.CheckConstraint(
            "balance_amount >= 0",
            name="ck_labour_advances_balance_non_negative",
        ),
        sa.CheckConstraint(
            "recovered_amount <= amount",
            name="ck_labour_advances_recovered_lte_amount",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["contractor_id"], ["labour_contractors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_labour_advances_id"),
        "labour_advances",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_advances_advance_no"),
        "labour_advances",
        ["advance_no"],
        unique=True,
    )
    op.create_index(
        op.f("ix_labour_advances_project_id"),
        "labour_advances",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_advances_contractor_id"),
        "labour_advances",
        ["contractor_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_advances_advance_date"),
        "labour_advances",
        ["advance_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_advances_status"),
        "labour_advances",
        ["status"],
        unique=False,
    )

    op.create_table(
        "labour_advance_recoveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("advance_id", sa.Integer(), nullable=False),
        sa.Column("labour_bill_id", sa.Integer(), nullable=True),
        sa.Column("recovery_date", sa.Date(), nullable=False),
        sa.Column(
            "amount",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(
            "amount > 0",
            name="ck_labour_advance_recoveries_amount_positive",
        ),
        sa.ForeignKeyConstraint(["advance_id"], ["labour_advances.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["labour_bill_id"], ["labour_bills.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_labour_advance_recoveries_id"),
        "labour_advance_recoveries",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_advance_recoveries_advance_id"),
        "labour_advance_recoveries",
        ["advance_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_advance_recoveries_labour_bill_id"),
        "labour_advance_recoveries",
        ["labour_bill_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labour_advance_recoveries_recovery_date"),
        "labour_advance_recoveries",
        ["recovery_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_labour_advance_recoveries_recovery_date"),
        table_name="labour_advance_recoveries",
    )
    op.drop_index(
        op.f("ix_labour_advance_recoveries_labour_bill_id"),
        table_name="labour_advance_recoveries",
    )
    op.drop_index(
        op.f("ix_labour_advance_recoveries_advance_id"),
        table_name="labour_advance_recoveries",
    )
    op.drop_index(
        op.f("ix_labour_advance_recoveries_id"),
        table_name="labour_advance_recoveries",
    )
    op.drop_table("labour_advance_recoveries")

    op.drop_index(op.f("ix_labour_advances_status"), table_name="labour_advances")
    op.drop_index(op.f("ix_labour_advances_advance_date"), table_name="labour_advances")
    op.drop_index(op.f("ix_labour_advances_contractor_id"), table_name="labour_advances")
    op.drop_index(op.f("ix_labour_advances_project_id"), table_name="labour_advances")
    op.drop_index(op.f("ix_labour_advances_advance_no"), table_name="labour_advances")
    op.drop_index(op.f("ix_labour_advances_id"), table_name="labour_advances")
    op.drop_table("labour_advances")

    op.drop_index(op.f("ix_labour_bills_status"), table_name="labour_bills")
    op.drop_index(op.f("ix_labour_bills_contractor_id"), table_name="labour_bills")
    op.drop_index(op.f("ix_labour_bills_project_id"), table_name="labour_bills")
    op.drop_index(op.f("ix_labour_bills_bill_no"), table_name="labour_bills")
    op.drop_index(op.f("ix_labour_bills_id"), table_name="labour_bills")
    op.drop_table("labour_bills")

    op.drop_index(
        op.f("ix_labour_productivities_productivity_date"),
        table_name="labour_productivities",
    )
    op.drop_index(
        op.f("ix_labour_productivities_activity_name"),
        table_name="labour_productivities",
    )
    op.drop_index(op.f("ix_labour_productivities_labour_id"), table_name="labour_productivities")
    op.drop_index(op.f("ix_labour_productivities_project_id"), table_name="labour_productivities")
    op.drop_index(op.f("ix_labour_productivities_id"), table_name="labour_productivities")
    op.drop_table("labour_productivities")

    op.drop_index(op.f("ix_labour_attendance_items_labour_id"), table_name="labour_attendance_items")
    op.drop_index(
        op.f("ix_labour_attendance_items_attendance_id"),
        table_name="labour_attendance_items",
    )
    op.drop_index(op.f("ix_labour_attendance_items_id"), table_name="labour_attendance_items")
    op.drop_table("labour_attendance_items")

    op.drop_index(op.f("ix_labour_attendances_status"), table_name="labour_attendances")
    op.drop_index(
        op.f("ix_labour_attendances_attendance_date"),
        table_name="labour_attendances",
    )
    op.drop_index(op.f("ix_labour_attendances_marked_by"), table_name="labour_attendances")
    op.drop_index(op.f("ix_labour_attendances_project_id"), table_name="labour_attendances")
    op.drop_index(op.f("ix_labour_attendances_muster_no"), table_name="labour_attendances")
    op.drop_index(op.f("ix_labour_attendances_id"), table_name="labour_attendances")
    op.drop_table("labour_attendances")

    op.drop_index(op.f("ix_labours_is_active"), table_name="labours")
    op.drop_index(op.f("ix_labours_contractor_id"), table_name="labours")
    op.drop_index(op.f("ix_labours_skill_type"), table_name="labours")
    op.drop_index(op.f("ix_labours_full_name"), table_name="labours")
    op.drop_index(op.f("ix_labours_labour_code"), table_name="labours")
    op.drop_index(op.f("ix_labours_id"), table_name="labours")
    op.drop_table("labours")

    op.drop_index(op.f("ix_labour_contractors_is_active"), table_name="labour_contractors")
    op.drop_index(
        op.f("ix_labour_contractors_contractor_name"),
        table_name="labour_contractors",
    )
    op.drop_index(
        op.f("ix_labour_contractors_contractor_code"),
        table_name="labour_contractors",
    )
    op.drop_index(op.f("ix_labour_contractors_id"), table_name="labour_contractors")
    op.drop_table("labour_contractors")

    op.drop_index(
        op.f("ix_material_stock_adjustment_items_material_id"),
        table_name="material_stock_adjustment_items",
    )
    op.drop_index(
        op.f("ix_material_stock_adjustment_items_adjustment_id"),
        table_name="material_stock_adjustment_items",
    )
    op.drop_index(
        op.f("ix_material_stock_adjustment_items_id"),
        table_name="material_stock_adjustment_items",
    )
    op.drop_table("material_stock_adjustment_items")

    op.drop_index(
        op.f("ix_material_stock_adjustments_status"),
        table_name="material_stock_adjustments",
    )
    op.drop_index(
        op.f("ix_material_stock_adjustments_adjustment_date"),
        table_name="material_stock_adjustments",
    )
    op.drop_index(
        op.f("ix_material_stock_adjustments_adjusted_by"),
        table_name="material_stock_adjustments",
    )
    op.drop_index(
        op.f("ix_material_stock_adjustments_project_id"),
        table_name="material_stock_adjustments",
    )
    op.drop_index(
        op.f("ix_material_stock_adjustments_adjustment_no"),
        table_name="material_stock_adjustments",
    )
    op.drop_index(
        op.f("ix_material_stock_adjustments_id"),
        table_name="material_stock_adjustments",
    )
    op.drop_table("material_stock_adjustments")
