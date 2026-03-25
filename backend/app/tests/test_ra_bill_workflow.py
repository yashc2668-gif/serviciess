"""RA bill workflow rule tests."""

import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from app.models.ra_bill import RABill
from app.models.deduction import Deduction
from app.services.ra_bill_service import _ensure_draft_bill, validate_ra_bill_transition
from app.services.secured_advance_service import validate_secured_advance_recoveries_for_bill
from app.tests.helpers import FinanceDbTestCase


class RABillWorkflowTests(unittest.TestCase):
    def test_submitted_bill_can_be_verified(self):
        validate_ra_bill_transition("submitted", "verified")

    def test_submitted_bill_cannot_jump_directly_to_paid(self):
        with self.assertRaises(HTTPException) as ctx:
            validate_ra_bill_transition("submitted", "paid")

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Cannot move RA bill", ctx.exception.detail)

    def test_reject_requires_remarks(self):
        with self.assertRaises(HTTPException) as ctx:
            validate_ra_bill_transition("verified", "rejected")

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(
            ctx.exception.detail,
            "Remarks are mandatory when rejecting an RA bill",
        )

    def test_approved_bill_can_move_to_partially_paid(self):
        validate_ra_bill_transition("approved", "partially_paid")

    def test_approved_bill_is_immutable_for_draft_only_actions(self):
        approved_bill = RABill(status="approved")

        with self.assertRaises(HTTPException) as ctx:
            _ensure_draft_bill(approved_bill)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "Only draft RA bills can be modified")


class SecuredAdvanceValidationTests(FinanceDbTestCase):
    def test_secured_advance_over_recovery_is_rejected(self):
        bill = self.create_ra_bill(bill_no=21, status="draft", net_payable="500.00")
        advance = self.create_secured_advance(advance_amount="5000.00", balance="1000.00")
        bill.deductions = [
            Deduction(
                deduction_type="secured_advance_recovery",
                amount=1500,
                secured_advance_id=advance.id,
            )
        ]

        with self.assertRaises(HTTPException) as ctx:
            validate_secured_advance_recoveries_for_bill(self.db, bill)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("recovery exceeds available balance", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
