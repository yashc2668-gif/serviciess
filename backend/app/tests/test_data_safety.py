"""Database data-safety constraint tests."""

import unittest
from datetime import date
from decimal import Decimal

import app.db.base  # noqa: F401
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.models.company import Company
from app.models.contract import Contract
from app.models.inventory_transaction import InventoryTransaction
from app.models.labour import Labour
from app.models.labour_advance import LabourAdvance
from app.models.labour_attendance import LabourAttendance
from app.models.labour_attendance_item import LabourAttendanceItem
from app.models.labour_contractor import LabourContractor
from app.models.labour_productivity import LabourProductivity
from app.models.material import Material
from app.models.material_receipt import MaterialReceipt
from app.models.material_receipt_item import MaterialReceiptItem
from app.models.material_requisition import MaterialRequisition
from app.models.material_requisition_item import MaterialRequisitionItem
from app.models.project import Project
from app.models.user import User
from app.models.vendor import Vendor


class DataSafetyModelTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(self.engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.company = Company(name="Safety Test Company")
        self.user = User(
            full_name="Safety Admin",
            email="safety-admin@example.com",
            hashed_password="not-used",
            role="admin",
            is_active=True,
        )
        self.vendor = Vendor(name="Safety Vendor", code="SAFE-VEN-001", vendor_type="contractor")
        self.db.add_all([self.company, self.user, self.vendor])
        self.db.flush()

        self.project = Project(
            company_id=self.company.id,
            name="Safety Project",
            code="SAFE-PRJ-001",
            original_value=Decimal("100000.00"),
            revised_value=Decimal("100000.00"),
            status="active",
        )
        self.db.add(self.project)
        self.db.flush()

        self.contract = Contract(
            project_id=self.project.id,
            vendor_id=self.vendor.id,
            contract_no="SAFE-CTR-001",
            title="Safety Contract",
            original_value=Decimal("100000.00"),
            revised_value=Decimal("100000.00"),
            retention_percentage=Decimal("5.00"),
            status="active",
        )
        self.material = Material(
            item_code="SAFE-MAT-001",
            item_name="Safety Cement",
            unit="bag",
            reorder_level=Decimal("5.000"),
            default_rate=Decimal("320.00"),
            current_stock=Decimal("10.000"),
            is_active=True,
            company_id=self.company.id,
            project_id=self.project.id,
        )
        self.contractor = LabourContractor(
            contractor_code="SAFE-CON-001",
            contractor_name="Safety Contractor",
            is_active=True,
        )
        self.db.add_all([self.contract, self.material, self.contractor])
        self.db.flush()

        self.labour = Labour(
            labour_code="SAFE-LAB-001",
            full_name="Safety Worker",
            trade="Mason",
            skill_level="Skilled",
            daily_rate=Decimal("850.00"),
            default_wage_rate=Decimal("850.00"),
            contractor_id=self.contractor.id,
            is_active=True,
        )
        self.db.add(self.labour)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _create_requisition(self) -> MaterialRequisition:
        requisition = MaterialRequisition(
            requisition_no="SAFE-REQ-001",
            project_id=self.project.id,
            requested_by=self.user.id,
            status="draft",
        )
        self.db.add(requisition)
        self.db.commit()
        self.db.refresh(requisition)
        return requisition

    def _create_receipt(self) -> MaterialReceipt:
        receipt = MaterialReceipt(
            receipt_no="SAFE-RCV-001",
            vendor_id=self.vendor.id,
            project_id=self.project.id,
            received_by=self.user.id,
            receipt_date=date(2026, 3, 26),
            status="draft",
            total_amount=Decimal("0.00"),
        )
        self.db.add(receipt)
        self.db.commit()
        self.db.refresh(receipt)
        return receipt

    def _create_attendance(self, muster_no: str) -> LabourAttendance:
        attendance = LabourAttendance(
            muster_no=muster_no,
            project_id=self.project.id,
            contractor_id=self.contractor.id,
            date=date(2026, 3, 26),
            created_by=self.user.id,
            attendance_date=date(2026, 3, 26),
            marked_by=self.user.id,
            status="draft",
            total_wage=Decimal("0.00"),
        )
        self.db.add(attendance)
        self.db.commit()
        self.db.refresh(attendance)
        return attendance

    def test_material_requisition_items_require_unique_material_and_valid_quantities(self):
        requisition = self._create_requisition()

        first_item = MaterialRequisitionItem(
            requisition_id=requisition.id,
            material_id=self.material.id,
            requested_qty=Decimal("5.000"),
            approved_qty=Decimal("4.000"),
            issued_qty=Decimal("0.000"),
        )
        self.db.add(first_item)
        self.db.commit()

        duplicate_item = MaterialRequisitionItem(
            requisition_id=requisition.id,
            material_id=self.material.id,
            requested_qty=Decimal("1.000"),
            approved_qty=Decimal("0.000"),
            issued_qty=Decimal("0.000"),
        )
        self.db.add(duplicate_item)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

        another_requisition = MaterialRequisition(
            requisition_no="SAFE-REQ-002",
            project_id=self.project.id,
            requested_by=self.user.id,
            status="draft",
        )
        self.db.add(another_requisition)
        self.db.commit()
        self.db.refresh(another_requisition)

        invalid_item = MaterialRequisitionItem(
            requisition_id=another_requisition.id,
            material_id=self.material.id,
            requested_qty=Decimal("2.000"),
            approved_qty=Decimal("3.000"),
            issued_qty=Decimal("0.000"),
        )
        self.db.add(invalid_item)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_material_receipt_items_enforce_foreign_keys(self):
        receipt = self._create_receipt()
        invalid_item = MaterialReceiptItem(
            receipt_id=receipt.id,
            material_id=999999,
            received_qty=Decimal("1.000"),
            unit_rate=Decimal("100.00"),
            line_amount=Decimal("100.00"),
        )
        self.db.add(invalid_item)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_inventory_transactions_are_directional_and_append_only(self):
        invalid_transaction = InventoryTransaction(
            material_id=self.material.id,
            project_id=self.project.id,
            transaction_type="material_issue",
            qty_in=Decimal("1.000"),
            qty_out=Decimal("1.000"),
            balance_after=Decimal("10.000"),
            reference_type="material_issue",
            reference_id=1,
            transaction_date=date(2026, 3, 26),
        )
        self.db.add(invalid_transaction)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

        transaction = InventoryTransaction(
            material_id=self.material.id,
            project_id=self.project.id,
            transaction_type="material_receipt",
            qty_in=Decimal("2.000"),
            qty_out=Decimal("0.000"),
            balance_after=Decimal("12.000"),
            reference_type="material_receipt",
            reference_id=2,
            transaction_date=date(2026, 3, 26),
        )
        self.db.add(transaction)
        self.db.commit()

        transaction.balance_after = Decimal("999.000")
        with self.assertRaises(InvalidRequestError):
            self.db.commit()
        self.db.rollback()

        persisted = self.db.get(InventoryTransaction, transaction.id)
        with self.assertRaises(InvalidRequestError):
            self.db.delete(persisted)
            self.db.commit()
        self.db.rollback()

    def test_labour_attendance_items_require_unique_labour_and_valid_status(self):
        attendance = self._create_attendance("SAFE-MST-001")

        first_item = LabourAttendanceItem(
            attendance_id=attendance.id,
            labour_id=self.labour.id,
            attendance_status="present",
            present_days=Decimal("1.00"),
            overtime_hours=Decimal("0.00"),
            wage_rate=Decimal("850.00"),
            line_amount=Decimal("850.00"),
        )
        self.db.add(first_item)
        self.db.commit()

        duplicate_item = LabourAttendanceItem(
            attendance_id=attendance.id,
            labour_id=self.labour.id,
            attendance_status="present",
            present_days=Decimal("1.00"),
            overtime_hours=Decimal("0.00"),
            wage_rate=Decimal("850.00"),
            line_amount=Decimal("850.00"),
        )
        self.db.add(duplicate_item)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

        another_attendance = self._create_attendance("SAFE-MST-002")
        invalid_status_item = LabourAttendanceItem(
            attendance_id=another_attendance.id,
            labour_id=self.labour.id,
            attendance_status="late",
            present_days=Decimal("1.00"),
            overtime_hours=Decimal("0.00"),
            wage_rate=Decimal("850.00"),
            line_amount=Decimal("850.00"),
        )
        self.db.add(invalid_status_item)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_labour_advance_and_productivity_constraints_are_enforced(self):
        invalid_advance = LabourAdvance(
            advance_no="SAFE-ADV-001",
            project_id=self.project.id,
            contractor_id=self.contractor.id,
            advance_date=date(2026, 3, 26),
            amount=Decimal("1000.00"),
            recovered_amount=Decimal("700.00"),
            balance_amount=Decimal("400.00"),
            status="active",
        )
        self.db.add(invalid_advance)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

        invalid_productivity = LabourProductivity(
            project_id=self.project.id,
            contract_id=self.contract.id,
            date=date(2026, 3, 26),
            trade="Masonry",
            quantity_done=Decimal("10.000"),
            labour_count=0,
            productivity_value=Decimal("0.000"),
            labour_id=self.labour.id,
            activity_name="Masonry",
            quantity=Decimal("10.000"),
            unit="sqm",
            productivity_date=date(2026, 3, 26),
        )
        self.db.add(invalid_productivity)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()


if __name__ == "__main__":
    unittest.main()
