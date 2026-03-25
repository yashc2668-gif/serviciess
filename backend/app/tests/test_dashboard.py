"""Dashboard aggregate consistency tests."""

import unittest

from app.services.dashboard_service import get_contract_dashboard, get_dashboard_finance, get_dashboard_summary
from app.tests.helpers import FinanceDbTestCase


class DashboardTests(FinanceDbTestCase):
    def test_dashboard_totals_are_consistent(self):
        first_bill = self.create_ra_bill(
            bill_no=31,
            status="approved",
            gross_amount="1100.00",
            total_deductions="100.00",
            net_payable="1000.00",
        )
        second_bill = self.create_ra_bill(
            bill_no=32,
            status="partially_paid",
            gross_amount="1650.00",
            total_deductions="150.00",
            net_payable="1500.00",
        )
        self.add_deduction(first_bill, deduction_type="retention", amount="100.00")
        self.add_deduction(second_bill, deduction_type="retention", amount="150.00")
        self.add_deduction(second_bill, deduction_type="penalty", amount="50.00")

        first_payment = self.create_payment_record(amount="800.00", status="released")
        second_payment = self.create_payment_record(amount="200.00", status="approved")
        self.add_allocation(payment=first_payment, bill=first_bill, amount="300.00")
        self.add_allocation(payment=first_payment, bill=second_bill, amount="500.00")
        self.create_secured_advance(advance_amount="5000.00", balance="2500.00")

        summary = get_dashboard_summary(self.db)
        finance = get_dashboard_finance(self.db)
        contract_dashboard = get_contract_dashboard(self.db, self.contract.id)

        self.assertEqual(summary.total_projects, 1)
        self.assertEqual(summary.active_contracts, 1)
        self.assertEqual(summary.total_billed_amount, finance.total_billed_amount)
        self.assertEqual(summary.total_paid_amount, finance.total_paid_amount)
        self.assertEqual(summary.outstanding_payable, finance.outstanding_payable)
        self.assertEqual(summary.total_billed_amount, 2500.0)
        self.assertEqual(summary.total_paid_amount, 800.0)
        self.assertEqual(summary.outstanding_payable, 1700.0)
        self.assertEqual(summary.secured_advance_outstanding, 2500.0)
        self.assertEqual(summary.pending_ra_bills_by_status, [])
        self.assertEqual(len(summary.pending_payments_by_status), 1)
        self.assertEqual(summary.pending_payments_by_status[0].status, "approved")

        self.assertEqual(len(finance.project_wise_billed_vs_paid), 1)
        self.assertEqual(len(finance.project_wise_finance_summary), 1)
        self.assertEqual(finance.project_wise_billed_vs_paid[0].billed_amount, 2500.0)
        self.assertEqual(finance.project_wise_billed_vs_paid[0].paid_amount, 800.0)
        self.assertEqual(finance.project_wise_finance_summary[0].outstanding_amount, 1700.0)
        self.assertEqual(len(finance.contract_wise_finance_summary), 1)
        self.assertEqual(finance.contract_wise_outstanding[0].outstanding_amount, 1700.0)
        self.assertEqual(finance.retention_outstanding_summary.total_retention_deducted, 250.0)
        self.assertEqual(contract_dashboard.total_billed_amount, 2500.0)
        self.assertEqual(contract_dashboard.total_paid_amount, 800.0)
        self.assertEqual(contract_dashboard.outstanding_payable, 1700.0)


if __name__ == "__main__":
    unittest.main()
