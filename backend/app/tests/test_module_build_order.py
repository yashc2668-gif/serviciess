"""Module build order and canonical router mapping tests."""

import unittest

from app.api.v1.api import api_router
from app.api.v1.endpoints import inventory, ra, ra_bills, secure_advance, secured_advances, stock_ledger


class ModuleBuildOrderTests(unittest.TestCase):
    def test_step5_material_labour_finance_router_order_is_explicit(self):
        prefixes_in_order = [
            "/materials",
            "/material-requisitions",
            "/stock-ledger",
            "/material-receipts",
            "/material-issues",
            "/material-stock-adjustments",
            "/labour-contractors",
            "/labours",
            "/labour-attendances",
            "/labour-bills",
            "/labour-advances",
            "/contracts/{contract_id}/boq-items",
            "/measurements",
            "/work-done",
            "/ra-bills",
            "/secured-advances",
            "/payments",
        ]

        first_occurrence: dict[str, int] = {}
        for index, route in enumerate(api_router.routes):
            route_path = getattr(route, "path", "")
            for prefix in prefixes_in_order:
                if prefix not in first_occurrence and route_path.startswith(prefix):
                    first_occurrence[prefix] = index

        self.assertEqual(set(first_occurrence), set(prefixes_in_order))

        indices = [first_occurrence[prefix] for prefix in prefixes_in_order]
        self.assertEqual(indices, sorted(indices))

    def test_step5_alias_modules_point_to_canonical_finance_and_stock_routers(self):
        self.assertIs(inventory.router, stock_ledger.router)
        self.assertIs(secure_advance.router, secured_advances.router)
        self.assertIs(ra.router, ra_bills.router)


if __name__ == "__main__":
    unittest.main()
