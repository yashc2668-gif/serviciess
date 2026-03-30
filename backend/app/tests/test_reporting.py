"""Reporting service regression tests for Phase 4 slices."""

import unittest
from datetime import date, timedelta
from decimal import Decimal

import app.db.base  # noqa: F401

from app.models.labour_productivity import LabourProductivity
from app.models.payment import Payment
from app.services.reporting_service import get_labour_productivity_report, get_mis_summary
from app.tests.helpers import FinanceDbTestCase
from app.utils.pagination import PaginationParams


def _shift_month(anchor: date, offset: int) -> date:
    month_index = (anchor.month - 1) + offset
    year = anchor.year + (month_index // 12)
    month = (month_index % 12) + 1
    return date(year, month, 1)


class ReportingServiceTests(FinanceDbTestCase):
    def _create_productivity_entry(
        self,
        *,
        trade: str,
        unit: str,
        quantity_done: str,
        labour_count: int,
        productivity_date: date,
    ) -> LabourProductivity:
        quantity = Decimal(quantity_done)
        entry = LabourProductivity(
            project_id=self.project.id,
            contract_id=self.contract.id,
            date=productivity_date,
            trade=trade,
            quantity_done=quantity,
            labour_count=labour_count,
            productivity_value=quantity / Decimal(labour_count),
            labour_id=None,
            activity_name=trade,
            quantity=quantity,
            unit=unit,
            productivity_date=productivity_date,
            remarks=None,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def test_mis_summary_returns_monthly_kpis_and_project_pressure(self):
        today = date.today()
        current_month_start = today.replace(day=1)
        previous_month_start = _shift_month(current_month_start, -1)

        current_bill = self.create_ra_bill(
            bill_no=41,
            status="approved",
            net_payable="1000.00",
            bill_date=current_month_start.replace(day=10),
        )
        previous_bill = self.create_ra_bill(
            bill_no=42,
            status="approved",
            net_payable="700.00",
            bill_date=previous_month_start.replace(day=12),
        )
        self.add_deduction(current_bill, deduction_type="retention", amount="100.00")
        self.add_deduction(previous_bill, deduction_type="retention", amount="60.00")

        current_payment = Payment(
            contract_id=self.contract.id,
            payment_date=current_month_start.replace(day=16),
            amount=Decimal("600.00"),
            status="released",
        )
        previous_payment = Payment(
            contract_id=self.contract.id,
            payment_date=previous_month_start.replace(day=18),
            amount=Decimal("400.00"),
            status="released",
        )
        overdue_pending_payment = Payment(
            contract_id=self.contract.id,
            payment_date=today - timedelta(days=45),
            amount=Decimal("250.00"),
            status="approved",
        )
        self.db.add_all([current_payment, previous_payment, overdue_pending_payment])
        self.db.commit()
        self.db.refresh(current_payment)
        self.db.refresh(previous_payment)

        self.add_allocation(payment=current_payment, bill=current_bill, amount="400.00")
        self.add_allocation(payment=previous_payment, bill=previous_bill, amount="300.00")
        self.create_secured_advance(advance_amount="5000.00", balance="1200.00")

        report = get_mis_summary(
            self.db,
            current_user=self.user,
            months=3,
            top_limit=3,
        )

        summary = report["summary"]
        self.assertEqual(summary["current_month"], current_month_start.strftime("%Y-%m"))
        self.assertEqual(summary["previous_month"], previous_month_start.strftime("%Y-%m"))
        self.assertEqual(summary["project_count"], 1)
        self.assertEqual(summary["active_project_count"], 1)
        self.assertEqual(summary["active_contract_count"], 1)
        self.assertEqual(summary["current_month_billed_amount"], 1000.0)
        self.assertEqual(summary["previous_month_billed_amount"], 700.0)
        self.assertEqual(summary["current_month_released_amount"], 600.0)
        self.assertEqual(summary["previous_month_released_amount"], 400.0)
        self.assertEqual(summary["current_month_net_amount"], 400.0)
        self.assertEqual(summary["payment_release_coverage_pct"], 60.0)
        self.assertEqual(summary["outstanding_payable"], 1000.0)
        self.assertEqual(summary["overdue_pending_payment_amount"], 250.0)
        self.assertEqual(summary["retention_held_amount"], 160.0)
        self.assertEqual(summary["secured_advance_outstanding"], 1200.0)
        self.assertEqual(len(report["monthly_trend"]), 3)
        self.assertEqual(report["top_outstanding_projects"][0]["project_name"], self.project.name)
        self.assertEqual(report["top_outstanding_projects"][0]["outstanding_amount"], 1000.0)

    def test_labour_productivity_report_groups_trade_unit_against_benchmark(self):
        today = date.today()
        self._create_productivity_entry(
            trade="mason",
            unit="sqm",
            quantity_done="120.000",
            labour_count=20,
            productivity_date=today - timedelta(days=12),
        )
        self._create_productivity_entry(
            trade="mason",
            unit="sqm",
            quantity_done="80.000",
            labour_count=20,
            productivity_date=today - timedelta(days=70),
        )
        self._create_productivity_entry(
            trade="carpenter",
            unit="sqm",
            quantity_done="30.000",
            labour_count=10,
            productivity_date=today - timedelta(days=8),
        )
        self._create_productivity_entry(
            trade="carpenter",
            unit="sqm",
            quantity_done="70.000",
            labour_count=10,
            productivity_date=today - timedelta(days=75),
        )

        report = get_labour_productivity_report(
            self.db,
            current_user=self.user,
            pagination=PaginationParams(page=1, limit=10, skip=0),
        )

        self.assertEqual(report["summary"]["records_logged"], 2)
        self.assertEqual(report["summary"]["active_trade_groups"], 2)
        self.assertEqual(report["summary"]["below_benchmark_groups"], 1)
        rows = {row["trade"]: row for row in report["items"]}
        self.assertEqual(rows["mason"]["recent_productivity"], 6.0)
        self.assertEqual(rows["mason"]["benchmark_productivity"], 4.0)
        self.assertEqual(rows["mason"]["benchmark_status"], "above_benchmark")
        self.assertEqual(rows["carpenter"]["recent_productivity"], 3.0)
        self.assertEqual(rows["carpenter"]["benchmark_productivity"], 7.0)
        self.assertEqual(rows["carpenter"]["benchmark_status"], "below_benchmark")
        self.assertEqual(report["watchlist"][0]["trade"], "carpenter")


if __name__ == "__main__":
    unittest.main()
