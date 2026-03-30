"""Workflow domain rule tests."""

import unittest

from fastapi import HTTPException

from app.services.labour_attendance_service import _validate_status_transition as validate_labour_attendance_transition
from app.services.labour_bill_service import _validate_status_transition as validate_labour_bill_transition
from app.services.material_issue_service import _validate_status_transition as validate_material_issue_transition
from app.services.material_receipt_service import _validate_status_transition as validate_material_receipt_transition
from app.services.material_requisition_service import _validate_status_transition as validate_material_requisition_transition
from app.services.material_stock_adjustment_service import _validate_status_transition as validate_stock_adjustment_transition


class WorkflowDomainRuleTests(unittest.TestCase):
    def test_material_requisition_cannot_jump_from_draft_to_approved(self):
        with self.assertRaises(HTTPException) as ctx:
            validate_material_requisition_transition(
                current_status="draft",
                target_status="approved",
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Invalid requisition status transition", ctx.exception.detail)

    def test_labour_attendance_requires_submit_before_approve(self):
        with self.assertRaises(HTTPException) as ctx:
            validate_labour_attendance_transition(
                current_status="draft",
                target_status="approved",
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Invalid labour attendance status transition", ctx.exception.detail)

    def test_labour_bill_requires_approval_before_paid(self):
        with self.assertRaises(HTTPException) as ctx:
            validate_labour_bill_transition(
                current_status="submitted",
                target_status="paid",
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Invalid labour bill status transition", ctx.exception.detail)

    def test_material_issue_cannot_reopen_issued_document(self):
        with self.assertRaises(HTTPException) as ctx:
            validate_material_issue_transition(
                current_status="issued",
                target_status="draft",
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Invalid material issue status transition", ctx.exception.detail)

    def test_material_receipt_cannot_reopen_received_document(self):
        with self.assertRaises(HTTPException) as ctx:
            validate_material_receipt_transition(
                current_status="received",
                target_status="draft",
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Invalid material receipt status transition", ctx.exception.detail)

    def test_stock_adjustment_cannot_reopen_posted_document(self):
        with self.assertRaises(HTTPException) as ctx:
            validate_stock_adjustment_transition(
                current_status="posted",
                target_status="draft",
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn(
            "Invalid material stock adjustment status transition",
            ctx.exception.detail,
        )


if __name__ == "__main__":
    unittest.main()
