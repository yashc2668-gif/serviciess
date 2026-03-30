"""Concurrency safety tests for optimistic locking and conflict translation."""

import os
import tempfile
import unittest
from datetime import date
from decimal import Decimal

import app.db.base  # noqa: F401
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.company import Company
from app.models.contract import Contract
from app.models.labour import Labour
from app.models.labour_advance import LabourAdvance
from app.models.labour_contractor import LabourContractor
from app.models.material import Material
from app.models.payment import Payment
from app.models.project import Project
from app.models.ra_bill import RABill
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.payment import PaymentAllocationCreate
from app.services.concurrency_service import commit_with_conflict_handling, touch_rows
from app.services.payment_service import allocate_payment


class ConcurrencySafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "concurrency_test.db")
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(self.engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(bind=self.engine)

        session = self.SessionLocal()
        company = Company(name="Concurrency Test Company")
        user = User(
            full_name="Concurrency Admin",
            email="concurrency-admin@example.com",
            hashed_password="not-used",
            role="admin",
            is_active=True,
        )
        vendor = Vendor(
            name="Concurrency Vendor",
            code="CON-VEN-001",
            vendor_type="contractor",
        )
        session.add_all([company, user, vendor])
        session.flush()

        project = Project(
            company_id=company.id,
            name="Concurrency Project",
            code="CON-PRJ-001",
            original_value=Decimal("100000.00"),
            revised_value=Decimal("100000.00"),
            status="active",
        )
        session.add(project)
        session.flush()

        contract = Contract(
            project_id=project.id,
            vendor_id=vendor.id,
            contract_no="CON-CTR-001",
            title="Concurrency Contract",
            original_value=Decimal("100000.00"),
            revised_value=Decimal("100000.00"),
            retention_percentage=Decimal("5.00"),
            status="active",
        )
        contractor = LabourContractor(
            contractor_code="CON-LC-001",
            contractor_name="Concurrency Labour Contractor",
            is_active=True,
        )
        material = Material(
            item_code="CON-MAT-001",
            item_name="Concurrency Cement",
            unit="bag",
            reorder_level=Decimal("5.000"),
            default_rate=Decimal("320.00"),
            current_stock=Decimal("10.000"),
            is_active=True,
            company_id=company.id,
            project_id=project.id,
        )
        session.add_all([contract, contractor, material])
        session.flush()

        labour = Labour(
            labour_code="CON-LAB-001",
            full_name="Concurrency Worker",
            trade="Mason",
            skill_level="Skilled",
            daily_rate=Decimal("850.00"),
            default_wage_rate=Decimal("850.00"),
            contractor_id=contractor.id,
            is_active=True,
        )
        ra_bill = RABill(
            contract_id=contract.id,
            bill_no=1,
            bill_date=date(2026, 3, 26),
            gross_amount=Decimal("80.00"),
            total_deductions=Decimal("0.00"),
            net_payable=Decimal("80.00"),
            status="approved",
        )
        payment = Payment(
            contract_id=contract.id,
            payment_date=date(2026, 3, 26),
            amount=Decimal("100.00"),
            status="released",
        )
        advance = LabourAdvance(
            advance_no="CON-ADV-001",
            project_id=project.id,
            contractor_id=contractor.id,
            advance_date=date(2026, 3, 26),
            amount=Decimal("50.00"),
            recovered_amount=Decimal("0.00"),
            balance_amount=Decimal("50.00"),
            status="active",
        )
        session.add_all([labour, ra_bill, payment, advance])
        session.commit()

        self.user_id = user.id
        self.material_id = material.id
        self.labour_id = labour.id
        self.payment_id = payment.id
        self.ra_bill_id = ra_bill.id
        self.advance_id = advance.id

        session.close()

    def tearDown(self):
        self.engine.dispose()
        self.temp_dir.cleanup()

    def _session(self):
        return self.SessionLocal()

    def test_material_stale_update_returns_http_409(self):
        session_one = self._session()
        session_two = self._session()
        try:
            material_one = session_one.query(Material).filter(Material.id == self.material_id).first()
            material_two = session_two.query(Material).filter(Material.id == self.material_id).first()

            material_one.current_stock = Decimal("15.000")
            session_one.commit()

            material_two.current_stock = Decimal("12.000")
            with self.assertRaises(HTTPException) as ctx:
                commit_with_conflict_handling(session_two, entity_name="Material")

            self.assertEqual(ctx.exception.status_code, 409)
            self.assertIn("modified concurrently", ctx.exception.detail)
        finally:
            session_one.close()
            session_two.close()

    def test_touch_rows_on_labour_detects_concurrent_attendance_claim(self):
        session_one = self._session()
        session_two = self._session()
        try:
            labour_one = session_one.query(Labour).filter(Labour.id == self.labour_id).first()
            labour_two = session_two.query(Labour).filter(Labour.id == self.labour_id).first()

            touch_rows(labour_one)
            commit_with_conflict_handling(session_one, entity_name="Labour attendance")

            touch_rows(labour_two)
            with self.assertRaises(HTTPException) as ctx:
                commit_with_conflict_handling(session_two, entity_name="Labour attendance")

            self.assertEqual(ctx.exception.status_code, 409)
            self.assertIn("Labour attendance", ctx.exception.detail)
        finally:
            session_one.close()
            session_two.close()

    def test_touch_rows_on_payment_and_bill_detect_concurrent_allocation_state(self):
        session_one = self._session()
        session_two = self._session()
        try:
            payment_one = session_one.query(Payment).filter(Payment.id == self.payment_id).first()
            bill_one = session_one.query(RABill).filter(RABill.id == self.ra_bill_id).first()
            payment_two = session_two.query(Payment).filter(Payment.id == self.payment_id).first()
            bill_two = session_two.query(RABill).filter(RABill.id == self.ra_bill_id).first()

            touch_rows(payment_one, bill_one)
            commit_with_conflict_handling(session_one, entity_name="Payment")

            touch_rows(payment_two, bill_two)
            with self.assertRaises(HTTPException) as ctx:
                commit_with_conflict_handling(session_two, entity_name="Payment")

            self.assertEqual(ctx.exception.status_code, 409)
            self.assertIn("Payment", ctx.exception.detail)
        finally:
            session_one.close()
            session_two.close()

    def test_labour_advance_stale_recovery_update_returns_http_409(self):
        session_one = self._session()
        session_two = self._session()
        try:
            advance_one = session_one.query(LabourAdvance).filter(
                LabourAdvance.id == self.advance_id
            ).first()
            advance_two = session_two.query(LabourAdvance).filter(
                LabourAdvance.id == self.advance_id
            ).first()

            advance_one.recovered_amount = Decimal("10.00")
            advance_one.balance_amount = Decimal("40.00")
            session_one.commit()

            advance_two.recovered_amount = Decimal("5.00")
            advance_two.balance_amount = Decimal("45.00")
            with self.assertRaises(HTTPException) as ctx:
                commit_with_conflict_handling(session_two, entity_name="Labour advance")

            self.assertEqual(ctx.exception.status_code, 409)
            self.assertIn("Labour advance", ctx.exception.detail)
        finally:
            session_one.close()
            session_two.close()

    def test_allocate_payment_blocks_combined_over_allocation_for_same_bill(self):
        session = self._session()
        try:
            current_user = session.query(User).filter(User.id == self.user_id).first()

            with self.assertRaises(HTTPException) as ctx:
                allocate_payment(
                    session,
                    self.payment_id,
                    [
                        PaymentAllocationCreate(ra_bill_id=self.ra_bill_id, amount=50, remarks="first"),
                        PaymentAllocationCreate(ra_bill_id=self.ra_bill_id, amount=40, remarks="second"),
                    ],
                    current_user,
                )

            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("Allocation exceeds outstanding amount", ctx.exception.detail)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
