"""Phase 4 — Reports & BI extension tests.

Covers:
  4.9  WBS (Work Breakdown Structure) report + export
  4.3  Cash flow export
  4.6  Ageing analysis export
  4.8  MIS summary export
"""

import unittest
from datetime import date, timedelta
from decimal import Decimal

import app.db.base  # noqa: F401

from app.models.boq import BOQItem
from app.models.measurement import Measurement
from app.models.measurement_item import MeasurementItem
from app.models.payment import Payment
from app.models.ra_bill_item import RABillItem
from app.models.work_done import WorkDoneItem
from app.services.reporting_service import (
    get_ageing_analysis_for_export,
    get_cash_flow_forecast_for_export,
    get_mis_summary_for_export,
    get_wbs_report,
    list_wbs_report_for_export,
)
from app.tests.helpers import FinanceDbTestCase
from app.utils.pagination import PaginationParams


class WBSReportTests(FinanceDbTestCase):
    """Test the WBS report service logic."""

    def _seed_boq_and_work(self) -> tuple:
        """Create BOQ items + a measurement + work-done entries."""
        boq1 = BOQItem(
            contract_id=self.contract.id,
            item_code="FW-001",
            description="Foundation work",
            unit="cum",
            quantity=Decimal("100.000"),
            rate=Decimal("500.00"),
            amount=Decimal("50000.00"),
            category="Foundation",
        )
        boq2 = BOQItem(
            contract_id=self.contract.id,
            item_code="SW-001",
            description="Structural steel",
            unit="MT",
            quantity=Decimal("50.000"),
            rate=Decimal("1000.00"),
            amount=Decimal("50000.00"),
            category="Structural",
        )
        self.db.add_all([boq1, boq2])
        self.db.flush()

        measurement = Measurement(
            contract_id=self.contract.id,
            measurement_no="MEAS-001",
            measurement_date=date.today() - timedelta(days=10),
            status="approved",
            created_by=self.user.id,
        )
        self.db.add(measurement)
        self.db.flush()

        mi1 = MeasurementItem(
            measurement_id=measurement.id,
            boq_item_id=boq1.id,
            description_snapshot="Foundation work",
            unit_snapshot="cum",
            previous_quantity=Decimal("0.000"),
            current_quantity=Decimal("40.000"),
            cumulative_quantity=Decimal("40.000"),
            rate=Decimal("500.00"),
            amount=Decimal("20000.00"),
        )
        mi2 = MeasurementItem(
            measurement_id=measurement.id,
            boq_item_id=boq2.id,
            description_snapshot="Structural steel",
            unit_snapshot="MT",
            previous_quantity=Decimal("0.000"),
            current_quantity=Decimal("20.000"),
            cumulative_quantity=Decimal("20.000"),
            rate=Decimal("1000.00"),
            amount=Decimal("20000.00"),
        )
        self.db.add_all([mi1, mi2])
        self.db.flush()

        wd1 = WorkDoneItem(
            contract_id=self.contract.id,
            measurement_id=measurement.id,
            measurement_item_id=mi1.id,
            boq_item_id=boq1.id,
            recorded_date=date.today() - timedelta(days=10),
            previous_quantity=Decimal("0.000"),
            current_quantity=Decimal("40.000"),
            cumulative_quantity=Decimal("40.000"),
            rate=Decimal("500.00"),
            amount=Decimal("20000.00"),
            approved_by=self.user.id,
        )
        wd2 = WorkDoneItem(
            contract_id=self.contract.id,
            measurement_id=measurement.id,
            measurement_item_id=mi2.id,
            boq_item_id=boq2.id,
            recorded_date=date.today() - timedelta(days=10),
            previous_quantity=Decimal("0.000"),
            current_quantity=Decimal("20.000"),
            cumulative_quantity=Decimal("20.000"),
            rate=Decimal("1000.00"),
            amount=Decimal("20000.00"),
            approved_by=self.user.id,
        )
        self.db.add_all([wd1, wd2])
        self.db.flush()

        # RA bill items for boq1 only
        bill = self.create_ra_bill(
            bill_no=100,
            status="approved",
            net_payable="18000.00",
            gross_amount="20000.00",
            total_deductions="2000.00",
        )
        rbi = RABillItem(
            ra_bill_id=bill.id,
            work_done_item_id=wd1.id,
            measurement_id=measurement.id,
            boq_item_id=boq1.id,
            item_code_snapshot="FW-001",
            description_snapshot="Foundation work",
            unit_snapshot="cum",
            prev_quantity=Decimal("0.000"),
            curr_quantity=Decimal("40.000"),
            cumulative_quantity=Decimal("40.000"),
            rate=Decimal("500.00"),
            amount=Decimal("20000.00"),
        )
        self.db.add(rbi)
        self.db.commit()

        return boq1, boq2, wd1, wd2

    def test_wbs_report_returns_items_with_completion(self):
        boq1, boq2, _, _ = self._seed_boq_and_work()

        report = get_wbs_report(
            self.db,
            current_user=self.user,
            pagination=PaginationParams(page=1, limit=50, skip=0),
        )

        summary = report["summary"]
        self.assertEqual(summary["total_items"], 2)
        self.assertEqual(summary["total_boq_amount"], 100000.0)
        self.assertEqual(summary["total_work_done_amount"], 40000.0)
        self.assertAlmostEqual(summary["overall_completion_pct"], 40.0, places=1)
        self.assertEqual(summary["categories_count"], 2)

        items_by_code = {i["item_code"]: i for i in report["items"]}
        fw = items_by_code["FW-001"]
        self.assertEqual(fw["boq_quantity"], 100.0)
        self.assertEqual(fw["work_done_quantity"], 40.0)
        self.assertAlmostEqual(fw["completion_pct"], 40.0, places=1)
        self.assertEqual(fw["remaining_quantity"], 60.0)

        sw = items_by_code["SW-001"]
        self.assertEqual(sw["work_done_quantity"], 20.0)
        self.assertAlmostEqual(sw["completion_pct"], 40.0, places=1)

    def test_wbs_category_rollup(self):
        self._seed_boq_and_work()

        report = get_wbs_report(
            self.db,
            current_user=self.user,
            pagination=PaginationParams(page=1, limit=50, skip=0),
        )

        rollup = {c["category"]: c for c in report["category_rollup"]}
        self.assertIn("Foundation", rollup)
        self.assertIn("Structural", rollup)
        self.assertEqual(rollup["Foundation"]["item_count"], 1)
        self.assertEqual(rollup["Foundation"]["boq_amount"], 50000.0)
        self.assertEqual(rollup["Foundation"]["work_done_amount"], 20000.0)
        self.assertAlmostEqual(rollup["Foundation"]["completion_pct"], 40.0, places=1)

    def test_wbs_search_filter(self):
        self._seed_boq_and_work()

        report = get_wbs_report(
            self.db,
            current_user=self.user,
            pagination=PaginationParams(page=1, limit=50, skip=0),
            search="foundation",
        )
        self.assertEqual(report["total"], 1)
        self.assertEqual(report["items"][0]["item_code"], "FW-001")

    def test_wbs_export_returns_all_rows(self):
        self._seed_boq_and_work()

        rows = list_wbs_report_for_export(
            self.db,
            current_user=self.user,
        )
        self.assertEqual(len(rows), 2)
        self.assertTrue(all("completion_pct" in r for r in rows))

    def test_wbs_pagination(self):
        self._seed_boq_and_work()

        report = get_wbs_report(
            self.db,
            current_user=self.user,
            pagination=PaginationParams(page=1, limit=1, skip=0),
        )
        self.assertEqual(len(report["items"]), 1)
        self.assertEqual(report["total"], 2)
        self.assertEqual(report["page"], 1)


class ExportEndpointServiceTests(FinanceDbTestCase):
    """Test that export helpers for ageing, cash-flow, MIS return data."""

    def test_ageing_export_returns_structured_data(self):
        self.create_ra_bill(
            bill_no=50,
            status="approved",
            net_payable="5000.00",
            bill_date=date.today() - timedelta(days=45),
        )

        data = get_ageing_analysis_for_export(
            self.db,
            current_user=self.user,
        )
        self.assertIsNotNone(data)
        self.assertIn("ra_bill_buckets", dir(data) if not isinstance(data, dict) else data)

    def test_cash_flow_export_returns_structured_data(self):
        self.create_ra_bill(
            bill_no=60,
            status="approved",
            net_payable="8000.00",
            bill_date=date.today() - timedelta(days=5),
        )

        data = get_cash_flow_forecast_for_export(
            self.db,
            current_user=self.user,
        )
        self.assertIsNotNone(data)
        self.assertTrue(hasattr(data, "summary") or "summary" in data)

    def test_mis_summary_export_returns_structured_data(self):
        self.create_ra_bill(
            bill_no=70,
            status="approved",
            net_payable="3000.00",
        )
        payment = Payment(
            contract_id=self.contract.id,
            payment_date=date.today(),
            amount=Decimal("2000.00"),
            status="released",
        )
        self.db.add(payment)
        self.db.commit()

        data = get_mis_summary_for_export(
            self.db,
            current_user=self.user,
        )
        self.assertIsNotNone(data)
        self.assertTrue(hasattr(data, "summary") or "summary" in data)


if __name__ == "__main__":
    unittest.main()
