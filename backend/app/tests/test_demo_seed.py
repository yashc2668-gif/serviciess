"""Demo seed regression coverage."""

from datetime import date
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
from app.schemas.ra_bill import RABillCreate
from app.services.ra_bill_service import (
    create_ra_bill_draft,
    generate_ra_bill_items,
    submit_ra_bill,
    transition_ra_bill_status,
)


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

    def test_finance_flow_backfills_missing_payment_for_existing_bill(self):
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

        bill = create_ra_bill_draft(
            self.db,
            RABillCreate(
                contract_id=contract.id,
                bill_date=date(2026, 3, 24),
                remarks="Partial demo RA bill",
            ),
            admin,
        )
        bill = generate_ra_bill_items(self.db, bill.id, admin)
        bill = submit_ra_bill(self.db, bill.id, admin, remarks="Partial demo submit")
        bill = transition_ra_bill_status(self.db, bill.id, "verified", admin, remarks="Partial demo verify")
        bill = transition_ra_bill_status(self.db, bill.id, "approved", admin, remarks="Partial demo approve")

        recovered_bill, payment = _get_or_create_finance_flow(self.db, contract, admin)

        self.assertEqual(recovered_bill.id, bill.id)
        self.assertIsNotNone(payment)
        self.assertGreater(payment.amount, 0)
        self.assertGreaterEqual(len(payment.allocations), 1)


if __name__ == "__main__":
    unittest.main()
