"""RA bill calculator tests."""

import unittest
from decimal import Decimal

from app.calculators.ra_bill_calculator import (
    calculate_bill_totals,
    calculate_deduction_amount,
    calculate_gross_amount,
)


class RABillCalculatorTests(unittest.TestCase):
    def test_calculate_gross_amount_sums_snapshot_items(self):
        items = [
            {"amount": 3000},
            {"amount": Decimal("21600.25")},
            {"amount": "499.75"},
        ]

        gross = calculate_gross_amount(items)

        self.assertEqual(gross, Decimal("25100.00"))

    def test_calculate_deduction_amount_uses_percentage_when_amount_missing(self):
        gross_amount = Decimal("100000.00")
        deduction = {"deduction_type": "retention", "percentage": 5, "amount": 0}

        resolved = calculate_deduction_amount(gross_amount, deduction)

        self.assertEqual(resolved, Decimal("5000.00"))

    def test_calculate_bill_totals_applies_fixed_and_percentage_deductions(self):
        items = [
            {"amount": 10000},
            {"amount": 15000},
        ]
        deductions = [
            {"deduction_type": "retention", "percentage": 5, "amount": 0},
            {"deduction_type": "tds", "amount": 1250},
        ]

        totals = calculate_bill_totals(items, deductions)

        self.assertEqual(totals["gross_amount"], Decimal("25000.00"))
        self.assertEqual(totals["total_deductions"], Decimal("2500.00"))
        self.assertEqual(totals["net_payable"], Decimal("22500.00"))


if __name__ == "__main__":
    unittest.main()
