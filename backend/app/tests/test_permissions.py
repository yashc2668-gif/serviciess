"""Permission tests."""

import unittest

from app.core.permissions import has_permissions, validate_role


class PermissionTests(unittest.TestCase):
    def test_contractor_is_blocked_from_finance_write_routes(self):
        self.assertFalse(has_permissions("contractor", ["payments:create"]))
        self.assertFalse(has_permissions("contractor", ["payments:approve"]))
        self.assertFalse(has_permissions("contractor", ["ra_bills:approve"]))
        self.assertFalse(has_permissions("contractor", ["secured_advances:create"]))
        self.assertFalse(has_permissions("contractor", ["material_requisitions:create"]))
        self.assertFalse(has_permissions("contractor", ["material_receipts:create"]))
        self.assertFalse(has_permissions("contractor", ["material_issues:create"]))
        self.assertFalse(
            has_permissions("contractor", ["material_stock_adjustments:create"])
        )
        self.assertFalse(has_permissions("contractor", ["labours:create"]))
        self.assertTrue(has_permissions("contractor", ["stock_ledger:read"]))
        self.assertTrue(has_permissions("contractor", ["labours:read"]))
        self.assertTrue(has_permissions("contractor", ["labour_attendance:read"]))

    def test_accountant_can_access_finance_routes(self):
        self.assertTrue(has_permissions("accountant", ["payments:create"]))
        self.assertTrue(has_permissions("accountant", ["payments:approve"]))
        self.assertTrue(has_permissions("accountant", ["ra_bills:approve"]))
        self.assertTrue(has_permissions("accountant", ["secured_advances:create"]))
        self.assertTrue(has_permissions("accountant", ["materials:read"]))
        self.assertTrue(has_permissions("accountant", ["stock_ledger:read"]))
        self.assertTrue(has_permissions("accountant", ["material_requisitions:read"]))
        self.assertTrue(has_permissions("accountant", ["material_receipts:read"]))
        self.assertTrue(has_permissions("accountant", ["material_issues:read"]))
        self.assertTrue(has_permissions("accountant", ["material_stock_adjustments:read"]))
        self.assertTrue(has_permissions("accountant", ["labour_bills:create"]))
        self.assertTrue(has_permissions("accountant", ["labour_advances:update"]))

    def test_viewer_can_read_dashboard_but_not_create_payment(self):
        self.assertTrue(has_permissions("viewer", ["dashboard:read"]))
        self.assertFalse(has_permissions("viewer", ["payments:create"]))
        self.assertTrue(has_permissions("viewer", ["materials:read"]))
        self.assertTrue(has_permissions("viewer", ["stock_ledger:read"]))
        self.assertTrue(has_permissions("viewer", ["material_requisitions:read"]))
        self.assertTrue(has_permissions("viewer", ["material_receipts:read"]))
        self.assertTrue(has_permissions("viewer", ["material_issues:read"]))
        self.assertTrue(has_permissions("viewer", ["material_stock_adjustments:read"]))
        self.assertTrue(has_permissions("viewer", ["labour_productivity:read"]))

    def test_frontend_permission_aliases_are_supported_in_rbac(self):
        self.assertTrue(has_permissions("project_manager", ["requisitions:create"]))
        self.assertTrue(has_permissions("project_manager", ["requisitions:approve"]))
        self.assertTrue(has_permissions("project_manager", ["receipts:create"]))
        self.assertTrue(has_permissions("project_manager", ["stock:issue"]))
        self.assertTrue(has_permissions("project_manager", ["stock:adjust"]))
        self.assertTrue(has_permissions("project_manager", ["labour:read"]))
        self.assertTrue(has_permissions("project_manager", ["labour:create"]))
        self.assertTrue(has_permissions("project_manager", ["labour:update"]))
        self.assertTrue(has_permissions("project_manager", ["attendance:create"]))
        self.assertTrue(has_permissions("project_manager", ["attendance:approve"]))
        self.assertTrue(has_permissions("project_manager", ["labour_bills:create"]))
        self.assertTrue(has_permissions("project_manager", ["labour_bills:approve"]))
        self.assertTrue(has_permissions("project_manager", ["labour_advances:create"]))

        self.assertFalse(has_permissions("contractor", ["stock:issue"]))
        self.assertFalse(has_permissions("contractor", ["stock:adjust"]))
        self.assertFalse(has_permissions("contractor", ["requisitions:approve"]))
        self.assertFalse(has_permissions("contractor", ["labour_bills:approve"]))
        self.assertTrue(has_permissions("contractor", ["labour:read"]))

    def test_project_manager_keeps_ra_bill_review_but_loses_settlement_permissions(self):
        self.assertTrue(has_permissions("project_manager", ["ra_bills:create"]))
        self.assertTrue(has_permissions("project_manager", ["ra_bills:verify"]))
        self.assertTrue(has_permissions("project_manager", ["ra_bills:approve"]))
        self.assertFalse(has_permissions("project_manager", ["payments:create"]))
        self.assertFalse(has_permissions("project_manager", ["payments:approve"]))
        self.assertFalse(has_permissions("project_manager", ["payments:release"]))
        self.assertFalse(has_permissions("project_manager", ["payments:allocate"]))
        self.assertFalse(has_permissions("project_manager", ["ra_bills:partially_paid"]))
        self.assertFalse(has_permissions("project_manager", ["ra_bills:paid"]))
        self.assertFalse(has_permissions("project_manager", ["secured_advances:create"]))
        self.assertFalse(has_permissions("project_manager", ["secured_advances:update"]))

    def test_project_manager_loses_hidden_master_admin_powers(self):
        self.assertTrue(has_permissions("project_manager", ["companies:read"]))
        self.assertTrue(has_permissions("project_manager", ["vendors:read"]))
        self.assertTrue(has_permissions("project_manager", ["vendors:update"]))
        self.assertFalse(has_permissions("project_manager", ["companies:create"]))
        self.assertFalse(has_permissions("project_manager", ["companies:update"]))
        self.assertFalse(has_permissions("project_manager", ["vendors:delete"]))
        self.assertFalse(has_permissions("project_manager", ["users:read"]))

    def test_role_aliases_normalize_to_canonical_keys(self):
        self.assertEqual(validate_role("Project Manager"), "project_manager")
        self.assertEqual(validate_role("project-manager"), "project_manager")
        self.assertEqual(validate_role("ADMIN"), "admin")


if __name__ == "__main__":
    unittest.main()
