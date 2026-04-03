"""Site expense service tests."""

import unittest

from fastapi import HTTPException

from app.schemas.site_expense import SiteExpenseCreate, SiteExpenseUpdate
from app.services.site_expense_service import (
    approve_site_expense,
    create_site_expense,
    get_site_expense_or_404,
    list_site_expenses,
    mark_site_expense_paid,
    update_site_expense,
)
from app.tests.helpers import OperationsDbTestCase
from app.utils.pagination import PaginationParams


class SiteExpenseServiceTests(OperationsDbTestCase):
    def test_site_expense_lifecycle(self):
        created = create_site_expense(
            self.db,
            SiteExpenseCreate(
                expense_no="SE-001",
                project_id=self.project.id,
                vendor_id=self.vendor.id,
                expense_date="2026-03-25",
                expense_head="Site Expenses",
                payee_name="Petty Cash Counter",
                amount=15000,
                payment_mode="cash",
                reference_no="CASH-001",
                remarks="Weekly source sheet capture",
            ),
            self.user,
        )
        created_status = created.status

        listing = list_site_expenses(
            self.db,
            current_user=self.user,
            pagination=PaginationParams(page=1, limit=20, skip=0),
            project_id=self.project.id,
            status_filter="draft",
            search="Site",
        )
        updated = update_site_expense(
            self.db,
            created.id,
            SiteExpenseUpdate(
                lock_version=created.lock_version,
                payee_name="Updated Counter",
                remarks="Updated remarks",
            ),
            self.user,
        )
        approved = approve_site_expense(
            self.db,
            created.id,
            self.user,
            expected_lock_version=updated.lock_version,
            remarks="Approved for posting",
        )
        approved_status = approved.status
        paid = mark_site_expense_paid(
            self.db,
            created.id,
            self.user,
            expected_lock_version=approved.lock_version,
            remarks="Cash settled",
        )
        fetched = get_site_expense_or_404(self.db, created.id, current_user=self.user)

        self.assertEqual(created_status, "draft")
        self.assertEqual(listing["total"], 1)
        self.assertEqual(updated.payee_name, "Updated Counter")
        self.assertEqual(approved_status, "approved")
        self.assertEqual(paid.status, "paid")
        self.assertEqual(fetched.status, "paid")

    def test_site_expense_rejects_duplicate_number_and_draft_only_update(self):
        created = create_site_expense(
            self.db,
            SiteExpenseCreate(
                expense_no="SE-002",
                project_id=self.project.id,
                expense_date="2026-03-25",
                expense_head="Fuel",
                amount=1200,
            ),
            self.user,
        )
        approve_site_expense(
            self.db,
            created.id,
            self.user,
            expected_lock_version=created.lock_version,
            remarks="Approved",
        )

        with self.assertRaises(HTTPException) as duplicate_number:
            create_site_expense(
                self.db,
                SiteExpenseCreate(
                    expense_no="SE-002",
                    project_id=self.project.id,
                    expense_date="2026-03-25",
                    expense_head="Fuel",
                    amount=2000,
                ),
                self.user,
            )

        with self.assertRaises(HTTPException) as non_draft_update:
            update_site_expense(
                self.db,
                created.id,
                SiteExpenseUpdate(lock_version=2, remarks="Should fail"),
                self.user,
            )

        self.assertEqual(duplicate_number.exception.status_code, 400)
        self.assertEqual(non_draft_update.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
