"""Demo seed regression coverage."""

import unittest

import app.db.base  # noqa: F401
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.demo_seed import (
    _get_or_create_boq,
    _get_or_create_company,
    _get_or_create_contract,
    _get_or_create_finance_flow,
    _get_or_create_measurement_and_work_done,
    _get_or_create_project,
    _get_or_create_user,
    _get_or_create_vendor,
)
from app.db.session import Base


class DemoSeedFlowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_finance_flow_seed_is_idempotent(self):
        company = _get_or_create_company(self.db)
        admin = _get_or_create_user(
            self.db,
            email="demo-admin@example.com",
            full_name="Demo Admin",
            role="admin",
            company_id=company.id,
        )
        vendor = _get_or_create_vendor(self.db)
        project = _get_or_create_project(self.db, company)
        contract = _get_or_create_contract(self.db, project, vendor)
        boq_items = _get_or_create_boq(self.db, contract)
        _get_or_create_measurement_and_work_done(self.db, contract, boq_items, admin)

        bill, payment = _get_or_create_finance_flow(self.db, contract, admin)
        repeated_bill, repeated_payment = _get_or_create_finance_flow(self.db, contract, admin)

        self.assertEqual(bill.id, repeated_bill.id)
        self.assertIsNotNone(payment)
        self.assertEqual(payment.id, repeated_payment.id)
        self.assertIn(repeated_bill.status, {"approved", "partially_paid", "paid"})
        self.assertGreaterEqual(len(repeated_bill.items), 1)


if __name__ == "__main__":
    unittest.main()
