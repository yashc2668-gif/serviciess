"""add data safety constraints

Revision ID: 7c2ef1a4b6d8
Revises: f3c9d12b7a6e
Create Date: 2026-03-26 19:10:00.000000
"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "7c2ef1a4b6d8"
down_revision = "f3c9d12b7a6e"
branch_labels = None
depends_on = None


def _create_inventory_append_only_guards() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            """
            CREATE FUNCTION prevent_inventory_transaction_mutation()
            RETURNS trigger
            AS $$
            BEGIN
                RAISE EXCEPTION 'inventory_transactions is append-only and cannot be changed';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_inventory_transactions_no_update
            BEFORE UPDATE ON inventory_transactions
            FOR EACH ROW
            EXECUTE FUNCTION prevent_inventory_transaction_mutation();
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_inventory_transactions_no_delete
            BEFORE DELETE ON inventory_transactions
            FOR EACH ROW
            EXECUTE FUNCTION prevent_inventory_transaction_mutation();
            """
        )
        return

    if dialect == "sqlite":
        op.execute(
            """
            CREATE TRIGGER trg_inventory_transactions_no_update
            BEFORE UPDATE ON inventory_transactions
            BEGIN
                SELECT RAISE(ABORT, 'inventory_transactions is append-only and cannot be changed');
            END;
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_inventory_transactions_no_delete
            BEFORE DELETE ON inventory_transactions
            BEGIN
                SELECT RAISE(ABORT, 'inventory_transactions is append-only and cannot be changed');
            END;
            """
        )


def _drop_inventory_append_only_guards() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_inventory_transactions_no_delete ON inventory_transactions;")
        op.execute("DROP TRIGGER IF EXISTS trg_inventory_transactions_no_update ON inventory_transactions;")
        op.execute("DROP FUNCTION IF EXISTS prevent_inventory_transaction_mutation();")
        return

    if dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_inventory_transactions_no_delete;")
        op.execute("DROP TRIGGER IF EXISTS trg_inventory_transactions_no_update;")


def upgrade() -> None:
    with op.batch_alter_table("materials", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_materials_reorder_level_nonnegative",
            "reorder_level >= 0",
        )
        batch_op.create_check_constraint(
            "ck_materials_default_rate_nonnegative",
            "default_rate >= 0",
        )
        batch_op.create_check_constraint(
            "ck_materials_current_stock_nonnegative",
            "current_stock >= 0",
        )

    with op.batch_alter_table("material_requisitions", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_material_requisitions_status_valid",
            "status IN ('draft', 'submitted', 'approved', 'partially_issued', 'issued', 'rejected', 'cancelled')",
        )

    with op.batch_alter_table("material_requisition_items", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_material_requisition_items_requisition_material",
            ["requisition_id", "material_id"],
        )
        batch_op.create_check_constraint(
            "ck_material_requisition_items_requested_qty_positive",
            "requested_qty > 0",
        )
        batch_op.create_check_constraint(
            "ck_material_requisition_items_approved_qty_nonnegative",
            "approved_qty >= 0",
        )
        batch_op.create_check_constraint(
            "ck_material_requisition_items_issued_qty_nonnegative",
            "issued_qty >= 0",
        )
        batch_op.create_check_constraint(
            "ck_material_requisition_items_approved_qty_lte_requested_qty",
            "approved_qty <= requested_qty",
        )
        batch_op.create_check_constraint(
            "ck_material_requisition_items_issued_qty_lte_approved_qty",
            "issued_qty <= approved_qty",
        )

    with op.batch_alter_table("material_receipts", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_material_receipts_status_valid",
            "status IN ('draft', 'received', 'cancelled')",
        )
        batch_op.create_check_constraint(
            "ck_material_receipts_total_amount_nonnegative",
            "total_amount >= 0",
        )

    with op.batch_alter_table("material_receipt_items", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_material_receipt_items_receipt_material",
            ["receipt_id", "material_id"],
        )
        batch_op.create_check_constraint(
            "ck_material_receipt_items_received_qty_positive",
            "received_qty > 0",
        )
        batch_op.create_check_constraint(
            "ck_material_receipt_items_unit_rate_nonnegative",
            "unit_rate >= 0",
        )
        batch_op.create_check_constraint(
            "ck_material_receipt_items_line_amount_nonnegative",
            "line_amount >= 0",
        )

    with op.batch_alter_table("material_issues", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_material_issues_status_valid",
            "status IN ('draft', 'issued', 'cancelled')",
        )
        batch_op.create_check_constraint(
            "ck_material_issues_total_amount_nonnegative",
            "total_amount >= 0",
        )

    with op.batch_alter_table("material_issue_items", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_material_issue_items_issue_material",
            ["issue_id", "material_id"],
        )
        batch_op.create_check_constraint(
            "ck_material_issue_items_issued_qty_positive",
            "issued_qty > 0",
        )
        batch_op.create_check_constraint(
            "ck_material_issue_items_unit_rate_nonnegative",
            "unit_rate >= 0",
        )
        batch_op.create_check_constraint(
            "ck_material_issue_items_line_amount_nonnegative",
            "line_amount >= 0",
        )

    with op.batch_alter_table("material_stock_adjustments", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_material_stock_adjustments_status_valid",
            "status IN ('draft', 'posted', 'cancelled')",
        )
        batch_op.create_check_constraint(
            "ck_material_stock_adjustments_total_amount_nonnegative",
            "total_amount >= 0",
        )

    with op.batch_alter_table("material_stock_adjustment_items", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_material_stock_adjustment_items_adjustment_material",
            ["adjustment_id", "material_id"],
        )
        batch_op.create_check_constraint(
            "ck_material_stock_adjustment_items_qty_change_nonzero",
            "qty_change <> 0",
        )
        batch_op.create_check_constraint(
            "ck_material_stock_adjustment_items_unit_rate_nonnegative",
            "unit_rate >= 0",
        )
        batch_op.create_check_constraint(
            "ck_material_stock_adjustment_items_line_amount_nonnegative",
            "line_amount >= 0",
        )

    with op.batch_alter_table("labours", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_labours_daily_rate_nonnegative",
            "daily_rate >= 0",
        )
        batch_op.create_check_constraint(
            "ck_labours_default_wage_rate_nonnegative",
            "default_wage_rate >= 0",
        )

    with op.batch_alter_table("labour_attendances", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_labour_attendances_status_valid",
            "status IN ('draft', 'submitted', 'approved', 'cancelled')",
        )
        batch_op.create_check_constraint(
            "ck_labour_attendances_total_wage_nonnegative",
            "total_wage >= 0",
        )

    with op.batch_alter_table("labour_attendance_items", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_labour_attendance_items_attendance_labour",
            ["attendance_id", "labour_id"],
        )
        batch_op.create_check_constraint(
            "ck_labour_attendance_items_status_valid",
            "attendance_status IN ('present', 'absent', 'half_day', 'leave')",
        )
        batch_op.create_check_constraint(
            "ck_labour_attendance_items_present_days_nonnegative",
            "present_days >= 0",
        )
        batch_op.create_check_constraint(
            "ck_labour_attendance_items_overtime_hours_nonnegative",
            "overtime_hours >= 0",
        )
        batch_op.create_check_constraint(
            "ck_labour_attendance_items_wage_rate_nonnegative",
            "wage_rate >= 0",
        )
        batch_op.create_check_constraint(
            "ck_labour_attendance_items_line_amount_nonnegative",
            "line_amount >= 0",
        )
        batch_op.create_check_constraint(
            "ck_labour_attendance_items_absent_leave_present_days_zero",
            "attendance_status NOT IN ('absent', 'leave') OR present_days = 0",
        )

    with op.batch_alter_table("labour_bills", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_labour_bills_status_valid",
            "status IN ('draft', 'submitted', 'approved', 'paid', 'cancelled')",
        )
        batch_op.create_check_constraint(
            "ck_labour_bills_period_order",
            "period_end >= period_start",
        )
        batch_op.create_check_constraint(
            "ck_labour_bills_gross_amount_nonnegative",
            "gross_amount >= 0",
        )
        batch_op.create_check_constraint(
            "ck_labour_bills_deductions_nonnegative",
            "deductions >= 0",
        )
        batch_op.create_check_constraint(
            "ck_labour_bills_net_amount_nonnegative",
            "net_amount >= 0",
        )
        batch_op.create_check_constraint(
            "ck_labour_bills_net_payable_nonnegative",
            "net_payable >= 0",
        )
        batch_op.create_check_constraint(
            "ck_labour_bills_deductions_lte_gross",
            "deductions <= gross_amount",
        )

    with op.batch_alter_table("labour_bill_items", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_labour_bill_items_quantity_nonnegative",
            "quantity >= 0",
        )
        batch_op.create_check_constraint(
            "ck_labour_bill_items_rate_nonnegative",
            "rate >= 0",
        )
        batch_op.create_check_constraint(
            "ck_labour_bill_items_amount_nonnegative",
            "amount >= 0",
        )

    with op.batch_alter_table("labour_advances", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_labour_advances_status_valid",
            "status IN ('active', 'closed', 'cancelled')",
        )
        batch_op.create_check_constraint(
            "ck_labour_advances_amount_positive",
            "amount > 0",
        )
        batch_op.create_check_constraint(
            "ck_labour_advances_recovered_amount_nonnegative",
            "recovered_amount >= 0",
        )
        batch_op.create_check_constraint(
            "ck_labour_advances_balance_amount_nonnegative",
            "balance_amount >= 0",
        )
        batch_op.create_check_constraint(
            "ck_labour_advances_recovered_amount_lte_amount",
            "recovered_amount <= amount",
        )
        batch_op.create_check_constraint(
            "ck_labour_advances_balance_amount_lte_amount",
            "balance_amount <= amount",
        )
        batch_op.create_check_constraint(
            "ck_labour_advances_balance_matches_amount",
            "recovered_amount + balance_amount = amount",
        )

    with op.batch_alter_table("labour_advance_recoveries", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_labour_advance_recoveries_amount_positive",
            "amount > 0",
        )

    with op.batch_alter_table("labour_productivities", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_labour_productivities_quantity_done_nonnegative",
            "quantity_done >= 0",
        )
        batch_op.create_check_constraint(
            "ck_labour_productivities_labour_count_positive",
            "labour_count > 0",
        )
        batch_op.create_check_constraint(
            "ck_labour_productivities_productivity_value_nonnegative",
            "productivity_value >= 0",
        )
        batch_op.create_check_constraint(
            "ck_labour_productivities_quantity_nonnegative",
            "quantity >= 0",
        )

    with op.batch_alter_table("inventory_transactions", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_inventory_transactions_qty_in_nonnegative",
            "qty_in >= 0",
        )
        batch_op.create_check_constraint(
            "ck_inventory_transactions_qty_out_nonnegative",
            "qty_out >= 0",
        )
        batch_op.create_check_constraint(
            "ck_inventory_transactions_balance_after_nonnegative",
            "balance_after >= 0",
        )
        batch_op.create_check_constraint(
            "ck_inventory_transactions_has_quantity_movement",
            "qty_in > 0 OR qty_out > 0",
        )
        batch_op.create_check_constraint(
            "ck_inventory_transactions_single_direction",
            "NOT (qty_in > 0 AND qty_out > 0)",
        )

    _create_inventory_append_only_guards()


def downgrade() -> None:
    _drop_inventory_append_only_guards()

    with op.batch_alter_table("inventory_transactions", schema=None) as batch_op:
        batch_op.drop_constraint("ck_inventory_transactions_single_direction", type_="check")
        batch_op.drop_constraint(
            "ck_inventory_transactions_has_quantity_movement",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_inventory_transactions_balance_after_nonnegative",
            type_="check",
        )
        batch_op.drop_constraint("ck_inventory_transactions_qty_out_nonnegative", type_="check")
        batch_op.drop_constraint("ck_inventory_transactions_qty_in_nonnegative", type_="check")

    with op.batch_alter_table("labour_productivities", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_labour_productivities_quantity_nonnegative",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_labour_productivities_productivity_value_nonnegative",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_labour_productivities_labour_count_positive",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_labour_productivities_quantity_done_nonnegative",
            type_="check",
        )

    with op.batch_alter_table("labour_advance_recoveries", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_labour_advance_recoveries_amount_positive",
            type_="check",
        )

    with op.batch_alter_table("labour_advances", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_labour_advances_balance_matches_amount",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_labour_advances_balance_amount_lte_amount",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_labour_advances_recovered_amount_lte_amount",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_labour_advances_balance_amount_nonnegative",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_labour_advances_recovered_amount_nonnegative",
            type_="check",
        )
        batch_op.drop_constraint("ck_labour_advances_amount_positive", type_="check")
        batch_op.drop_constraint("ck_labour_advances_status_valid", type_="check")

    with op.batch_alter_table("labour_bill_items", schema=None) as batch_op:
        batch_op.drop_constraint("ck_labour_bill_items_amount_nonnegative", type_="check")
        batch_op.drop_constraint("ck_labour_bill_items_rate_nonnegative", type_="check")
        batch_op.drop_constraint("ck_labour_bill_items_quantity_nonnegative", type_="check")

    with op.batch_alter_table("labour_bills", schema=None) as batch_op:
        batch_op.drop_constraint("ck_labour_bills_deductions_lte_gross", type_="check")
        batch_op.drop_constraint("ck_labour_bills_net_payable_nonnegative", type_="check")
        batch_op.drop_constraint("ck_labour_bills_net_amount_nonnegative", type_="check")
        batch_op.drop_constraint("ck_labour_bills_deductions_nonnegative", type_="check")
        batch_op.drop_constraint("ck_labour_bills_gross_amount_nonnegative", type_="check")
        batch_op.drop_constraint("ck_labour_bills_period_order", type_="check")
        batch_op.drop_constraint("ck_labour_bills_status_valid", type_="check")

    with op.batch_alter_table("labour_attendance_items", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_labour_attendance_items_absent_leave_present_days_zero",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_labour_attendance_items_line_amount_nonnegative",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_labour_attendance_items_wage_rate_nonnegative",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_labour_attendance_items_overtime_hours_nonnegative",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_labour_attendance_items_present_days_nonnegative",
            type_="check",
        )
        batch_op.drop_constraint("ck_labour_attendance_items_status_valid", type_="check")
        batch_op.drop_constraint(
            "uq_labour_attendance_items_attendance_labour",
            type_="unique",
        )

    with op.batch_alter_table("labour_attendances", schema=None) as batch_op:
        batch_op.drop_constraint("ck_labour_attendances_total_wage_nonnegative", type_="check")
        batch_op.drop_constraint("ck_labour_attendances_status_valid", type_="check")

    with op.batch_alter_table("labours", schema=None) as batch_op:
        batch_op.drop_constraint("ck_labours_default_wage_rate_nonnegative", type_="check")
        batch_op.drop_constraint("ck_labours_daily_rate_nonnegative", type_="check")

    with op.batch_alter_table("material_stock_adjustment_items", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_material_stock_adjustment_items_line_amount_nonnegative",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_material_stock_adjustment_items_unit_rate_nonnegative",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_material_stock_adjustment_items_qty_change_nonzero",
            type_="check",
        )
        batch_op.drop_constraint(
            "uq_material_stock_adjustment_items_adjustment_material",
            type_="unique",
        )

    with op.batch_alter_table("material_stock_adjustments", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_material_stock_adjustments_total_amount_nonnegative",
            type_="check",
        )
        batch_op.drop_constraint("ck_material_stock_adjustments_status_valid", type_="check")

    with op.batch_alter_table("material_issue_items", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_material_issue_items_line_amount_nonnegative",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_material_issue_items_unit_rate_nonnegative",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_material_issue_items_issued_qty_positive",
            type_="check",
        )
        batch_op.drop_constraint(
            "uq_material_issue_items_issue_material",
            type_="unique",
        )

    with op.batch_alter_table("material_issues", schema=None) as batch_op:
        batch_op.drop_constraint("ck_material_issues_total_amount_nonnegative", type_="check")
        batch_op.drop_constraint("ck_material_issues_status_valid", type_="check")

    with op.batch_alter_table("material_receipt_items", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_material_receipt_items_line_amount_nonnegative",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_material_receipt_items_unit_rate_nonnegative",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_material_receipt_items_received_qty_positive",
            type_="check",
        )
        batch_op.drop_constraint(
            "uq_material_receipt_items_receipt_material",
            type_="unique",
        )

    with op.batch_alter_table("material_receipts", schema=None) as batch_op:
        batch_op.drop_constraint("ck_material_receipts_total_amount_nonnegative", type_="check")
        batch_op.drop_constraint("ck_material_receipts_status_valid", type_="check")

    with op.batch_alter_table("material_requisition_items", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_material_requisition_items_issued_qty_lte_approved_qty",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_material_requisition_items_approved_qty_lte_requested_qty",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_material_requisition_items_issued_qty_nonnegative",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_material_requisition_items_approved_qty_nonnegative",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_material_requisition_items_requested_qty_positive",
            type_="check",
        )
        batch_op.drop_constraint(
            "uq_material_requisition_items_requisition_material",
            type_="unique",
        )

    with op.batch_alter_table("material_requisitions", schema=None) as batch_op:
        batch_op.drop_constraint("ck_material_requisitions_status_valid", type_="check")

    with op.batch_alter_table("materials", schema=None) as batch_op:
        batch_op.drop_constraint("ck_materials_current_stock_nonnegative", type_="check")
        batch_op.drop_constraint("ck_materials_default_rate_nonnegative", type_="check")
        batch_op.drop_constraint("ck_materials_reorder_level_nonnegative", type_="check")
