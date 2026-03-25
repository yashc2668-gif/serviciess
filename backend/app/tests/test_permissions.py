"""Permission tests."""

import unittest

from app.core.permissions import has_permissions


class PermissionTests(unittest.TestCase):
    def test_contractor_is_blocked_from_finance_write_routes(self):
        self.assertFalse(has_permissions("contractor", ["payments:create"]))
        self.assertFalse(has_permissions("contractor", ["payments:approve"]))
        self.assertFalse(has_permissions("contractor", ["ra_bills:approve"]))
        self.assertFalse(has_permissions("contractor", ["secured_advances:create"]))

    def test_accountant_can_access_finance_routes(self):
        self.assertTrue(has_permissions("accountant", ["payments:create"]))
        self.assertTrue(has_permissions("accountant", ["payments:approve"]))
        self.assertTrue(has_permissions("accountant", ["ra_bills:approve"]))
        self.assertTrue(has_permissions("accountant", ["secured_advances:create"]))

    def test_viewer_can_read_dashboard_but_not_create_payment(self):
        self.assertTrue(has_permissions("viewer", ["dashboard:read"]))
        self.assertFalse(has_permissions("viewer", ["payments:create"]))


if __name__ == "__main__":
    unittest.main()
