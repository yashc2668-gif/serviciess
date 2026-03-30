"""Targeted unit tests for admin and backoffice service modules."""

import unittest
from datetime import date
from decimal import Decimal

from fastapi import HTTPException

from app.core.security import verify_password
from app.models.audit_log import AuditLog
from app.models.company import Company
from app.models.contract import Contract
from app.models.labour_productivity import LabourProductivity
from app.models.project import Project
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.schemas.boq import BOQItemCreate, BOQItemUpdate
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.schemas.labour_productivity import LabourProductivityCreate, LabourProductivityUpdate
from app.schemas.user import UserUpdate
from app.services.boq_service import (
    create_boq_item,
    create_boq_item_with_audit,
    get_boq_item_or_404,
    list_boq_items_by_contract,
    update_boq_item,
)
from app.services.company_service import (
    create_company,
    get_company_or_404,
    list_companies,
    update_company,
)
from app.services.labour_productivity_service import (
    create_labour_productivity,
    get_labour_productivity_or_404,
    list_labour_productivities,
    update_labour_productivity,
)
from app.services.user_service import (
    create_user,
    delete_user,
    get_user_or_404,
    list_users,
    update_user,
)
from app.tests.helpers import OperationsDbTestCase
from app.utils.pagination import PaginationParams


class CompanyServiceTests(OperationsDbTestCase):
    def test_create_list_update_and_fetch_company_with_audit(self):
        created = create_company(
            self.db,
            CompanyCreate(
                name="BuildCo Infra",
                address="Mumbai",
                gst_number="27ABCDE1234F1Z5",
                phone="9876543210",
            ),
            self.user,
        )

        admin_page = list_companies(
            self.db,
            self.user,
            pagination=PaginationParams(page=1, limit=10, skip=0),
            search="BuildCo",
        )
        updated = update_company(
            self.db,
            created.id,
            CompanyUpdate(address="Navi Mumbai", email="ops@buildco.example"),
            self.user,
        )
        fetched = get_company_or_404(self.db, created.id, current_user=self.user)
        create_audit = (
            self.db.query(AuditLog)
            .filter(AuditLog.entity_type == "company", AuditLog.entity_id == created.id, AuditLog.action == "create")
            .one()
        )
        update_audit = (
            self.db.query(AuditLog)
            .filter(AuditLog.entity_type == "company", AuditLog.entity_id == created.id, AuditLog.action == "update")
            .one()
        )

        self.assertEqual(created.name, "BuildCo Infra")
        self.assertEqual(admin_page["total"], 1)
        self.assertEqual(admin_page["items"][0].id, created.id)
        self.assertEqual(updated.address, "Navi Mumbai")
        self.assertEqual(updated.email, "ops@buildco.example")
        self.assertEqual(fetched.id, created.id)
        self.assertEqual(create_audit.performed_by, self.user.id)
        self.assertEqual(update_audit.after_data["address"], "Navi Mumbai")

    def test_company_service_blocks_duplicates_and_cross_scope_access(self):
        other_company = Company(name="Other Scope Co")
        self.db.add(other_company)
        scoped_user = User(
            full_name="Scoped User",
            email="scoped-company@example.com",
            hashed_password="unused",
            role="project_manager",
            company_id=self.company.id,
            is_active=True,
        )
        self.db.add(scoped_user)
        self.db.commit()

        with self.assertRaises(HTTPException) as duplicate_create:
            create_company(self.db, CompanyCreate(name=self.company.name), self.user)

        with self.assertRaises(HTTPException) as duplicate_update:
            update_company(
                self.db,
                self.company.id,
                CompanyUpdate(name=other_company.name),
                self.user,
            )

        with self.assertRaises(HTTPException) as forbidden_scope:
            get_company_or_404(self.db, other_company.id, current_user=scoped_user)

        self.assertEqual(duplicate_create.exception.status_code, 400)
        self.assertEqual(duplicate_update.exception.status_code, 400)
        self.assertEqual(forbidden_scope.exception.status_code, 403)


class UserServiceTests(OperationsDbTestCase):
    def test_user_service_lifecycle_hashes_passwords_updates_roles_and_deactivates(self):
        created = create_user(
            self.db,
            RegisterRequest(
                full_name="Quality Engineer",
                email="quality.engineer@example.com",
                password="StrongPass1!",
                role="project manager",
                company_id=self.company.id,
            ),
        )
        original_hash = created.hashed_password

        listed = list_users(self.db, pagination=PaginationParams(page=1, limit=20, skip=0))
        updated = update_user(
            self.db,
            created.id,
            UserUpdate(
                full_name="Senior Quality Engineer",
                role="viewer",
                password="EvenStronger2!",
                phone="9000000000",
            ),
        )
        fetched = get_user_or_404(self.db, created.id)
        delete_user(self.db, created.id, self.user)
        deactivation_audit = (
            self.db.query(AuditLog)
            .filter(AuditLog.entity_type == "user", AuditLog.entity_id == created.id, AuditLog.action == "deactivate")
            .one()
        )

        self.assertTrue(verify_password("StrongPass1!", original_hash))
        self.assertEqual(listed["total"], 2)
        self.assertEqual(updated.role, "viewer")
        self.assertEqual(updated.full_name, "Senior Quality Engineer")
        self.assertTrue(verify_password("EvenStronger2!", updated.hashed_password))
        self.assertIsNotNone(updated.password_changed_at)
        self.assertEqual(fetched.phone, "9000000000")
        self.assertFalse(get_user_or_404(self.db, created.id).is_active)
        self.assertEqual(deactivation_audit.performed_by, self.user.id)

        delete_user(self.db, created.id, self.user)
        self.assertFalse(get_user_or_404(self.db, created.id).is_active)

    def test_user_service_rejects_duplicate_email_missing_user_and_self_deactivation(self):
        create_user(
            self.db,
            RegisterRequest(
                full_name="Accounts Lead",
                email="accounts.lead@example.com",
                password="StrongPass1!",
                role="accountant",
                company_id=self.company.id,
            ),
        )

        with self.assertRaises(HTTPException) as duplicate_email:
            create_user(
                self.db,
                RegisterRequest(
                    full_name="Duplicate",
                    email="accounts.lead@example.com",
                    password="StrongPass1!",
                    role="viewer",
                    company_id=self.company.id,
                ),
            )

        with self.assertRaises(HTTPException) as missing_user:
            get_user_or_404(self.db, 99999)

        with self.assertRaises(HTTPException) as self_delete:
            delete_user(self.db, self.user.id, self.user)

        self.assertEqual(duplicate_email.exception.status_code, 400)
        self.assertEqual(missing_user.exception.status_code, 404)
        self.assertEqual(self_delete.exception.status_code, 400)


class BOQServiceTests(OperationsDbTestCase):
    def test_boq_item_lifecycle_calculates_amount_lists_items_and_logs_audit(self):
        created = create_boq_item_with_audit(
            self.db,
            self.contract.id,
            BOQItemCreate(
                item_code="BOQ-CIV-01",
                description="Excavation in all kinds of soil",
                unit="cum",
                quantity=12,
                rate=350,
                amount=0,
                category="Earthwork",
            ),
            self.user,
        )
        created_amount = float(created.amount)

        listing = list_boq_items_by_contract(
            self.db,
            self.contract.id,
            pagination=PaginationParams(page=1, limit=20, skip=0),
        )
        fetched = get_boq_item_or_404(self.db, self.contract.id, created.id)
        updated = update_boq_item(
            self.db,
            self.contract.id,
            created.id,
            BOQItemUpdate(quantity=15, rate=360),
            self.user,
        )
        audit_actions = (
            self.db.query(AuditLog.action)
            .filter(AuditLog.entity_type == "boq_item", AuditLog.entity_id == created.id)
            .all()
        )

        self.assertEqual(created_amount, 4200.0)
        self.assertEqual(listing["total"], 1)
        self.assertEqual(fetched.id, created.id)
        self.assertEqual(float(updated.amount), 5400.0)
        self.assertIn(("create",), audit_actions)
        self.assertIn(("update",), audit_actions)

    def test_boq_service_rejects_missing_contracts_and_items(self):
        with self.assertRaises(HTTPException) as missing_contract:
            create_boq_item(
                self.db,
                99999,
                BOQItemCreate(
                    item_code="BOQ-404",
                    description="Missing contract row",
                    unit="nos",
                    quantity=1,
                    rate=1,
                ),
            )

        with self.assertRaises(HTTPException) as missing_item:
            get_boq_item_or_404(self.db, self.contract.id, 99999)

        self.assertEqual(missing_contract.exception.status_code, 404)
        self.assertEqual(missing_item.exception.status_code, 404)


class LabourProductivityServiceTests(OperationsDbTestCase):
    def test_create_update_and_fetch_labour_productivity_normalizes_fields_and_audits(self):
        contractor = self.create_labour_contractor()
        labour = self.create_labour(contractor_id=contractor.id)

        created = create_labour_productivity(
            self.db,
            LabourProductivityCreate(
                project_id=self.project.id,
                contract_id=self.contract.id,
                date=date(2026, 3, 25),
                trade="  Mason  ",
                quantity_done=18,
                labour_count=3,
                labour_id=labour.id,
                unit="  sqm  ",
                remarks="  Daily output normalised  ",
            ),
            self.user,
        )
        self.assertEqual(created.trade, "Mason")
        self.assertEqual(created.activity_name, "Mason")
        self.assertEqual(float(created.quantity), 18.0)
        self.assertEqual(float(created.productivity_value), 6.0)
        self.assertEqual(created.unit, "sqm")
        self.assertEqual(created.remarks, "Daily output normalised")

        updated = update_labour_productivity(
            self.db,
            created.id,
            LabourProductivityUpdate(
                date=date(2026, 3, 26),
                trade="  Tile Fixing  ",
                quantity_done=20,
                labour_count=4,
                unit="  day  ",
                remarks="   ",
            ),
            self.user,
        )
        fetched = get_labour_productivity_or_404(self.db, created.id)
        audit_actions = (
            self.db.query(AuditLog.action)
            .filter(
                AuditLog.entity_type == "labour_productivity",
                AuditLog.entity_id == created.id,
            )
            .all()
        )

        self.assertEqual(updated.trade, "Tile Fixing")
        self.assertEqual(updated.activity_name, "Tile Fixing")
        self.assertEqual(updated.unit, "day")
        self.assertIsNone(updated.remarks)
        self.assertEqual(float(updated.productivity_value), 5.0)
        self.assertEqual(fetched.id, created.id)
        self.assertIn(("create",), audit_actions)
        self.assertIn(("update",), audit_actions)

    def test_list_labour_productivities_respects_scope_and_validates_references(self):
        create_labour_productivity(
            self.db,
            LabourProductivityCreate(
                project_id=self.project.id,
                contract_id=self.contract.id,
                date=date(2026, 3, 20),
                trade="Mason",
                quantity_done=12,
                labour_count=3,
                unit="sqm",
            ),
            self.user,
        )

        other_company = Company(name="Other Company")
        self.db.add(other_company)
        self.db.flush()
        other_project = Project(
            company_id=other_company.id,
            name="Other Project",
            code="OTHER-PRJ",
            original_value=Decimal("10000"),
            revised_value=Decimal("10000"),
            status="active",
        )
        self.db.add(other_project)
        self.db.flush()
        other_contract = Contract(
            project_id=other_project.id,
            vendor_id=self.vendor.id,
            contract_no="OTHER-CTR-001",
            title="Other Contract",
            original_value=Decimal("10000"),
            revised_value=Decimal("10000"),
            retention_percentage=Decimal("5.00"),
            status="active",
        )
        self.db.add(other_contract)
        self.db.flush()
        self.db.add(
            LabourProductivity(
                project_id=other_project.id,
                contract_id=other_contract.id,
                date=date(2026, 3, 21),
                trade="Painter",
                quantity_done=Decimal("10"),
                labour_count=2,
                productivity_value=Decimal("5"),
                labour_id=None,
                activity_name="Painter",
                quantity=Decimal("10"),
                unit="sqm",
                productivity_date=date(2026, 3, 21),
                remarks=None,
            )
        )
        scoped_user = User(
            full_name="Scoped Engineer",
            email="scoped.engineer@example.com",
            hashed_password="unused",
            role="engineer",
            company_id=self.company.id,
            is_active=True,
        )
        self.db.add(scoped_user)
        self.db.commit()

        filtered = list_labour_productivities(
            self.db,
            current_user=scoped_user,
            pagination=PaginationParams(page=1, limit=20, skip=0),
            trade=" mason ",
        )

        with self.assertRaises(HTTPException) as contract_mismatch:
            create_labour_productivity(
                self.db,
                LabourProductivityCreate(
                    project_id=self.project.id,
                    contract_id=other_contract.id,
                    date=date(2026, 3, 27),
                    trade="Mason",
                    quantity_done=10,
                    labour_count=2,
                    unit="sqm",
                ),
                self.user,
            )

        created = filtered["items"][0]
        with self.assertRaises(HTTPException) as blank_unit:
            update_labour_productivity(
                self.db,
                created.id,
                LabourProductivityUpdate(unit="   "),
                self.user,
            )

        with self.assertRaises(HTTPException) as missing_productivity:
            get_labour_productivity_or_404(self.db, 99999)

        self.assertEqual(filtered["total"], 1)
        self.assertEqual(created.trade, "Mason")
        self.assertEqual(contract_mismatch.exception.status_code, 400)
        self.assertEqual(blank_unit.exception.status_code, 400)
        self.assertEqual(missing_productivity.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
