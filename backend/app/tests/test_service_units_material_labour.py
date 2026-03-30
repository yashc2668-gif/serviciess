"""Targeted service-layer unit tests for Material, Labour, and finance linkages."""

import unittest
from datetime import date
from decimal import Decimal

import app.db.base  # noqa: F401
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.audit_log import AuditLog
from app.models.company import Company
from app.models.contract import Contract
from app.models.inventory_transaction import InventoryTransaction
from app.models.labour import Labour
from app.models.labour_contractor import LabourContractor
from app.models.project import Project
from app.models.secured_advance_recovery import SecuredAdvanceRecovery
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.labour import LabourCreate, LabourUpdate
from app.schemas.labour_contractor import LabourContractorCreate, LabourContractorUpdate
from app.schemas.material import MaterialCreate, MaterialUpdate
from app.schemas.secured_advance import SecuredAdvanceIssueCreate, SecuredAdvanceUpdate
from app.services.labour_contractor_service import (
    create_labour_contractor,
    update_labour_contractor,
)
from app.services.labour_service import create_labour, update_labour
from app.services.material_service import (
    create_material,
    get_material_stock_summary,
    update_material,
)
from app.services.secured_advance_service import (
    apply_secured_advance_recoveries_for_bill,
    issue_secured_advance,
    update_secured_advance,
)
from app.tests.helpers import FinanceDbTestCase


class OperationsDbTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.company = Company(name="Ops Test Company")
        self.user = User(
            full_name="Ops Admin",
            email="ops-admin@example.com",
            hashed_password="not-used",
            role="project_manager",
            is_active=True,
        )
        self.vendor = Vendor(name="Ops Vendor", code="OPS-VEN-001", vendor_type="supplier")
        self.db.add_all([self.company, self.user, self.vendor])
        self.db.flush()
        self.user.company_id = self.company.id

        self.project = Project(
            company_id=self.company.id,
            name="Ops Test Project",
            code="OPS-PRJ-001",
            original_value=Decimal("50000.00"),
            revised_value=Decimal("50000.00"),
            status="active",
        )
        self.db.add(self.project)
        self.db.flush()

        self.contract = Contract(
            project_id=self.project.id,
            vendor_id=self.vendor.id,
            contract_no="OPS-CTR-001",
            title="Ops Contract",
            original_value=Decimal("50000.00"),
            revised_value=Decimal("50000.00"),
            retention_percentage=Decimal("5.00"),
            status="active",
        )
        self.db.add(self.contract)
        self.db.commit()
        self.db.refresh(self.company)
        self.db.refresh(self.user)
        self.db.refresh(self.project)
        self.db.refresh(self.contract)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def create_contractor(self, *, name: str, code: str | None = None) -> LabourContractor:
        payload = LabourContractorCreate(
            contractor_code=code,
            contractor_name=name,
            contact_person=f"{name} Contact",
            phone="9999999999",
        )
        return create_labour_contractor(self.db, payload, self.user)


class MaterialServiceTests(OperationsDbTestCase):
    def test_create_material_normalizes_scope_and_records_opening_stock(self):
        material = create_material(
            self.db,
            MaterialCreate(
                item_code=" mat-001 ",
                item_name=" Cement OPC 53 ",
                category=" Cement ",
                unit=" bag ",
                reorder_level=20,
                default_rate=365,
                current_stock=25,
                project_id=self.project.id,
            ),
            self.user,
        )

        opening_entry = (
            self.db.query(InventoryTransaction)
            .filter(
                InventoryTransaction.material_id == material.id,
                InventoryTransaction.transaction_type == "material_opening_balance",
            )
            .one()
        )
        audit_log = (
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "material",
                AuditLog.entity_id == material.id,
                AuditLog.action == "create",
            )
            .one()
        )

        self.assertEqual(material.item_code, "MAT-001")
        self.assertEqual(material.item_name, "Cement OPC 53")
        self.assertEqual(material.category, "Cement")
        self.assertEqual(material.unit, "bag")
        self.assertEqual(material.company_id, self.company.id)
        self.assertEqual(float(material.current_stock), 25.0)
        self.assertEqual(float(opening_entry.qty_in), 25.0)
        self.assertEqual(float(opening_entry.balance_after), 25.0)
        self.assertEqual(audit_log.performed_by, self.user.id)
        self.assertEqual(audit_log.after_data["item_code"], "MAT-001")

    def test_update_material_records_manual_adjustment_and_summary(self):
        material = create_material(
            self.db,
            MaterialCreate(
                item_code="MAT-002",
                item_name="River Sand",
                category="Aggregate",
                unit="cum",
                reorder_level=5,
                default_rate=1500,
                current_stock=0,
                company_id=self.company.id,
                project_id=self.project.id,
            ),
            self.user,
        )

        updated = update_material(
            self.db,
            material.id,
            MaterialUpdate(
                current_stock=12,
                category="   ",
                default_rate=1550,
            ),
            self.user,
        )

        adjustment_entry = (
            self.db.query(InventoryTransaction)
            .filter(
                InventoryTransaction.material_id == material.id,
                InventoryTransaction.transaction_type == "material_manual_adjustment",
            )
            .one()
        )
        summary = get_material_stock_summary(
            self.db,
            self.user,
            group_by="project",
            project_id=self.project.id,
        )

        self.assertIsNone(updated.category)
        self.assertEqual(float(updated.current_stock), 12.0)
        self.assertEqual(float(adjustment_entry.qty_in), 12.0)
        self.assertEqual(float(adjustment_entry.balance_after), 12.0)
        self.assertEqual(summary[0]["scope_id"], self.project.id)
        self.assertEqual(summary[0]["material_count"], 1)
        self.assertEqual(summary[0]["total_stock"], 12.0)


class LabourServiceTests(OperationsDbTestCase):
    def test_create_labour_syncs_legacy_fields_and_logs_audit(self):
        contractor = self.create_contractor(name="Alpha Labour Supplier", code="LCTR-ALPHA")

        labour = create_labour(
            self.db,
            LabourCreate(
                labour_code=" lbr-001 ",
                full_name=" Ramesh Kumar ",
                trade=" Mason ",
                skill_level="Skilled",
                daily_rate=700,
                unit=" day ",
                contractor_id=contractor.id,
            ),
            self.user,
        )

        audit_log = (
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "labour",
                AuditLog.entity_id == labour.id,
                AuditLog.action == "create",
            )
            .one()
        )

        self.assertEqual(labour.labour_code, "LBR-001")
        self.assertEqual(labour.full_name, "Ramesh Kumar")
        self.assertEqual(labour.trade, "Mason")
        self.assertEqual(labour.skill_type, "Mason")
        self.assertEqual(float(labour.daily_rate), 700.0)
        self.assertEqual(float(labour.default_wage_rate), 700.0)
        self.assertEqual(labour.unit, "day")
        self.assertEqual(audit_log.after_data["skill_type"], "Mason")

    def test_update_labour_syncs_rate_and_rejects_missing_contractor(self):
        contractor = self.create_contractor(name="Alpha Labour Supplier", code="LCTR-001")
        labour = create_labour(
            self.db,
            LabourCreate(
                labour_code="LBR-002",
                full_name="Suresh Kumar",
                trade="Helper",
                skill_level="Semi-skilled",
                daily_rate=450,
                unit="day",
                contractor_id=contractor.id,
            ),
            self.user,
        )

        updated = update_labour(
            self.db,
            labour.id,
            LabourUpdate(
                trade=" Foreman ",
                daily_rate=850,
            ),
            self.user,
        )

        self.assertEqual(updated.trade, "Foreman")
        self.assertEqual(updated.skill_type, "Foreman")
        self.assertEqual(float(updated.daily_rate), 850.0)
        self.assertEqual(float(updated.default_wage_rate), 850.0)

        with self.assertRaises(HTTPException) as ctx:
            update_labour(
                self.db,
                labour.id,
                LabourUpdate(contractor_id=9999),
                self.user,
            )

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "Labour contractor not found")


class LabourContractorServiceTests(OperationsDbTestCase):
    def test_create_labour_contractor_generates_code_and_syncs_contact_person(self):
        contractor = create_labour_contractor(
            self.db,
            LabourContractorCreate(
                contractor_name="Bravo Gangs",
                contact_person=" Manoj Supervisor ",
                phone="9876543210",
            ),
            self.user,
        )

        audit_log = (
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "labour_contractor",
                AuditLog.entity_id == contractor.id,
                AuditLog.action == "create",
            )
            .one()
        )

        self.assertTrue(contractor.contractor_code.startswith("LCTR-BRAV-"))
        self.assertEqual(contractor.contact_person, "Manoj Supervisor")
        self.assertEqual(contractor.gang_name, "Manoj Supervisor")
        self.assertEqual(audit_log.after_data["contractor_name"], "Bravo Gangs")

    def test_update_labour_contractor_rejects_duplicate_name(self):
        first = self.create_contractor(name="Alpha Crew", code="LCTR-A001")
        second = self.create_contractor(name="Beta Crew", code="LCTR-B001")

        updated = update_labour_contractor(
            self.db,
            second.id,
            LabourContractorUpdate(
                contact_person=" New Supervisor ",
                phone="8888888888",
            ),
            self.user,
        )
        self.assertEqual(updated.contact_person, "New Supervisor")
        self.assertEqual(updated.gang_name, "New Supervisor")

        with self.assertRaises(HTTPException) as ctx:
            update_labour_contractor(
                self.db,
                second.id,
                LabourContractorUpdate(contractor_name=first.contractor_name),
                self.user,
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "Contractor name already exists")


class SecuredAdvanceServiceTests(FinanceDbTestCase):
    def test_issue_secured_advance_sets_balance_and_writes_audit_log(self):
        advance = issue_secured_advance(
            self.db,
            SecuredAdvanceIssueCreate(
                contract_id=self.contract.id,
                advance_date=date(2026, 3, 26),
                description="Mobilization advance",
                advance_amount=2500,
            ),
            self.user,
        )

        updated = update_secured_advance(
            self.db,
            advance.id,
            SecuredAdvanceUpdate(description="Updated mobilization advance"),
            self.user,
        )

        audit_actions = (
            self.db.query(AuditLog.action)
            .filter(
                AuditLog.entity_type == "secured_advance",
                AuditLog.entity_id == advance.id,
            )
            .order_by(AuditLog.id.asc())
            .all()
        )

        self.assertEqual(float(updated.advance_amount), 2500.0)
        self.assertEqual(float(updated.recovered_amount), 0.0)
        self.assertEqual(float(updated.balance), 2500.0)
        self.assertEqual(updated.status, "active")
        self.assertEqual(updated.description, "Updated mobilization advance")
        self.assertEqual([row.action for row in audit_actions], ["issue", "update"])

    def test_apply_secured_advance_recoveries_is_idempotent_per_bill(self):
        advance = self.create_secured_advance(advance_amount="5000.00", balance="5000.00")
        bill = self.create_ra_bill(
            bill_no=21,
            net_payable="4000.00",
            gross_amount="5000.00",
            total_deductions="1000.00",
        )
        self.add_deduction(
            bill,
            deduction_type="secured_advance_recovery",
            amount="1000.00",
            description="Secured advance recovery",
            secured_advance_id=advance.id,
        )

        apply_secured_advance_recoveries_for_bill(self.db, bill, self.user)
        self.db.commit()
        self.db.refresh(advance)

        first_recovery_count = (
            self.db.query(SecuredAdvanceRecovery)
            .filter(SecuredAdvanceRecovery.ra_bill_id == bill.id)
            .count()
        )
        first_audit_count = (
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "secured_advance",
                AuditLog.entity_id == advance.id,
                AuditLog.action == "recovery",
            )
            .count()
        )

        apply_secured_advance_recoveries_for_bill(self.db, bill, self.user)
        self.db.commit()
        self.db.refresh(advance)

        second_recovery_count = (
            self.db.query(SecuredAdvanceRecovery)
            .filter(SecuredAdvanceRecovery.ra_bill_id == bill.id)
            .count()
        )
        second_audit_count = (
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "secured_advance",
                AuditLog.entity_id == advance.id,
                AuditLog.action == "recovery",
            )
            .count()
        )

        self.assertEqual(first_recovery_count, 1)
        self.assertEqual(second_recovery_count, 1)
        self.assertEqual(first_audit_count, 1)
        self.assertEqual(second_audit_count, 1)
        self.assertEqual(float(advance.recovered_amount), 1000.0)
        self.assertEqual(float(advance.balance), 4000.0)


if __name__ == "__main__":
    unittest.main()
