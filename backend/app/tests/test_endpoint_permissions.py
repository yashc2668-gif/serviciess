"""Route-level permission tests for Material, Labour, and Finance domains."""

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import app.db.base  # noqa: F401
import main
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import Base, get_db
from app.models.company import Company
from app.models.contract import Contract
from app.models.inventory_transaction import InventoryTransaction
from app.models.labour import Labour
from app.models.labour_contractor import LabourContractor
from app.models.material import Material
from app.models.project import Project
from app.models.user import User
from app.models.vendor import Vendor


class EndpointPermissionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.company = Company(name="Permission Test Company")
        self.admin_user = User(
            full_name="Permission Admin",
            email="permission-admin@example.com",
            hashed_password=hash_password("StrongPass123"),
            role="admin",
            is_active=True,
        )
        self.contractor_user = User(
            full_name="Permission Contractor",
            email="permission-contractor@example.com",
            hashed_password=hash_password("StrongPass123"),
            role="contractor",
            is_active=True,
        )
        self.accountant_user = User(
            full_name="Permission Accountant",
            email="permission-accountant@example.com",
            hashed_password=hash_password("StrongPass123"),
            role="accountant",
            is_active=True,
        )
        self.project_manager_user = User(
            full_name="Permission Project Manager",
            email="permission-pm@example.com",
            hashed_password=hash_password("StrongPass123"),
            role="project_manager",
            is_active=True,
        )
        self.viewer_user = User(
            full_name="Permission Viewer",
            email="permission-viewer@example.com",
            hashed_password=hash_password("StrongPass123"),
            role="viewer",
            is_active=True,
        )
        self.vendor = Vendor(
            name="Permission Vendor",
            code="PERM-VEN-001",
            vendor_type="contractor",
        )
        self.db.add_all(
            [
                self.company,
                self.admin_user,
                self.contractor_user,
                self.accountant_user,
                self.project_manager_user,
                self.viewer_user,
                self.vendor,
            ]
        )
        self.db.flush()

        # Assign company scope to all non-admin users.
        for user in (self.contractor_user, self.accountant_user,
                     self.project_manager_user, self.viewer_user):
            user.company_id = self.company.id
        self.vendor.company_id = self.company.id
        self.db.flush()

        self.project = Project(
            company_id=self.company.id,
            name="Permission Project",
            code="PERM-PRJ-001",
            original_value=Decimal("100000.00"),
            revised_value=Decimal("100000.00"),
            status="active",
        )
        self.db.add(self.project)
        self.db.flush()

        self.contract = Contract(
            project_id=self.project.id,
            vendor_id=self.vendor.id,
            contract_no="PERM-CTR-001",
            title="Permission Contract",
            original_value=Decimal("100000.00"),
            revised_value=Decimal("100000.00"),
            retention_percentage=Decimal("5.00"),
            status="active",
        )
        self.db.add(self.contract)
        self.db.flush()

        self.material = Material(
            item_code="PERM-MAT-001",
            item_name="Permission Cement",
            category="Cement",
            unit="bag",
            reorder_level=10,
            default_rate=350,
            current_stock=20,
            is_active=True,
            company_id=self.company.id,
            project_id=self.project.id,
        )
        self.labour_contractor = LabourContractor(
            contractor_code="PERM-LCTR-001",
            contractor_name="Permission Labour Contractor",
            contact_person="Lead Supervisor",
            gang_name="Lead Supervisor",
            is_active=True,
            company_id=self.company.id,
        )
        self.db.add_all([self.material, self.labour_contractor])
        self.db.flush()

        self.labour = Labour(
            labour_code="PERM-LBR-001",
            full_name="Permission Labour",
            trade="Mason",
            skill_level="Skilled",
            daily_rate=Decimal("700.00"),
            skill_type="Mason",
            default_wage_rate=Decimal("700.00"),
            unit="day",
            contractor_id=self.labour_contractor.id,
            is_active=True,
        )
        self.db.add(self.labour)
        self.db.flush()

        self.stock_entry = InventoryTransaction(
            material_id=self.material.id,
            project_id=self.project.id,
            transaction_type="material_opening_balance",
            qty_in=Decimal("20.000"),
            qty_out=Decimal("0.000"),
            balance_after=Decimal("20.000"),
            reference_type="material",
            reference_id=self.material.id,
            transaction_date=date(2026, 3, 26),
            remarks="Seeded opening stock",
        )
        self.db.add(self.stock_entry)
        self.db.commit()
        self.db.refresh(self.material)
        self.db.refresh(self.labour)
        self.db.refresh(self.stock_entry)

        self.seed_patch = patch("main.run_seed", lambda: None)
        self.seed_patch.start()
        self.health_patch = patch(
            "main._database_health_payload",
            lambda: {"status": "ok", "database": "test", "user": "test", "ping": 1},
        )
        self.health_patch.start()
        self.storage_root_patch = patch.object(settings, "LOCAL_STORAGE_ROOT", ".tmp-test")
        self.storage_root_patch.start()

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        main.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()
        main.app.dependency_overrides.clear()
        self.storage_root_patch.stop()
        self.health_patch.stop()
        self.seed_patch.stop()
        self.db.close()
        self.engine.dispose()

    def auth_headers(self, email: str, password: str = "StrongPass123") -> dict[str, str]:
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        self.assertEqual(response.status_code, 200, response.text)
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def admin_headers(self) -> dict[str, str]:
        return self.auth_headers(self.admin_user.email)

    def contractor_headers(self) -> dict[str, str]:
        return self.auth_headers(self.contractor_user.email)

    def accountant_headers(self) -> dict[str, str]:
        return self.auth_headers(self.accountant_user.email)

    def project_manager_headers(self) -> dict[str, str]:
        return self.auth_headers(self.project_manager_user.email)

    def viewer_headers(self) -> dict[str, str]:
        return self.auth_headers(self.viewer_user.email)

    def test_material_routes_enforce_read_and_adjust_permissions(self):
        unauthorized = self.client.get("/api/v1/materials/")
        self.assertEqual(unauthorized.status_code, 401)

        viewer_list = self.client.get("/api/v1/materials/", headers=self.viewer_headers())
        self.assertEqual(viewer_list.status_code, 200, viewer_list.text)
        self.assertEqual(len(viewer_list.json()["items"]), 1)

        contractor_create = self.client.post(
            "/api/v1/materials/",
            headers=self.contractor_headers(),
            json={
                "item_code": "PERM-MAT-NEW",
                "item_name": "Blocked Cement",
                "unit": "bag",
                "project_id": self.project.id,
            },
        )
        self.assertEqual(contractor_create.status_code, 403)

        accountant_adjust = self.client.post(
            "/api/v1/material-stock-adjustments/",
            headers=self.accountant_headers(),
            json={
                "adjustment_no": "PERM-ADJ-001",
                "project_id": self.project.id,
                "adjustment_date": "2026-03-26",
                "status": "posted",
                "items": [{"material_id": self.material.id, "qty_change": 2, "unit_rate": 350}],
            },
        )
        self.assertEqual(accountant_adjust.status_code, 403)

        admin_adjust = self.client.post(
            "/api/v1/material-stock-adjustments/",
            headers=self.admin_headers(),
            json={
                "adjustment_no": "PERM-ADJ-001",
                "project_id": self.project.id,
                "adjustment_date": "2026-03-26",
                "status": "posted",
                "items": [{"material_id": self.material.id, "qty_change": 2, "unit_rate": 350}],
            },
        )
        self.assertEqual(admin_adjust.status_code, 201, admin_adjust.text)
        self.assertEqual(admin_adjust.json()["adjustment_no"], "PERM-ADJ-001")

    def test_labour_routes_enforce_read_and_write_permissions(self):
        unauthorized = self.client.get("/api/v1/labour-productivities/")
        self.assertEqual(unauthorized.status_code, 401)

        contractor_read = self.client.get(
            "/api/v1/labour-productivities/",
            headers=self.contractor_headers(),
        )
        self.assertEqual(contractor_read.status_code, 200, contractor_read.text)

        contractor_create = self.client.post(
            "/api/v1/labour-productivities/",
            headers=self.contractor_headers(),
            json={
                "project_id": self.project.id,
                "labour_id": self.labour.id,
                "activity_name": "Brickwork",
                "quantity": 15,
                "unit": "sqm",
                "productivity_date": "2026-03-26",
            },
        )
        self.assertEqual(contractor_create.status_code, 403)

        viewer_contractor_create = self.client.post(
            "/api/v1/labour-contractors/",
            headers=self.viewer_headers(),
            json={"contractor_name": "Blocked Labour Contractor"},
        )
        self.assertEqual(viewer_contractor_create.status_code, 403)

        admin_create = self.client.post(
            "/api/v1/labour-productivities/",
            headers=self.admin_headers(),
            json={
                "project_id": self.project.id,
                "labour_id": self.labour.id,
                "activity_name": "Brickwork",
                "quantity": 15,
                "unit": "sqm",
                "productivity_date": "2026-03-26",
            },
        )
        self.assertEqual(admin_create.status_code, 201, admin_create.text)
        self.assertEqual(admin_create.json()["activity_name"], "Brickwork")

    def test_finance_routes_enforce_canonical_secured_advance_permissions(self):
        unauthorized = self.client.get("/api/v1/secured-advances/")
        self.assertEqual(unauthorized.status_code, 401)

        contractor_read = self.client.get(
            "/api/v1/secured-advances/",
            headers=self.contractor_headers(),
        )
        self.assertEqual(contractor_read.status_code, 200, contractor_read.text)

        contractor_issue = self.client.post(
            "/api/v1/secured-advances/issue",
            headers=self.contractor_headers(),
            json={
                "contract_id": self.contract.id,
                "advance_date": "2026-03-26",
                "description": "Blocked issue",
                "advance_amount": 1500,
            },
        )
        self.assertEqual(contractor_issue.status_code, 403)

        accountant_issue = self.client.post(
            "/api/v1/secured-advances/issue",
            headers=self.accountant_headers(),
            json={
                "contract_id": self.contract.id,
                "advance_date": "2026-03-26",
                "description": "Mobilization issue",
                "advance_amount": 1500,
            },
        )
        self.assertEqual(accountant_issue.status_code, 201, accountant_issue.text)
        self.assertEqual(accountant_issue.json()["status"], "active")

        ledger_read = self.client.get(
            f"/api/v1/stock-ledger?material_id={self.material.id}",
            headers=self.viewer_headers(),
        )
        self.assertEqual(ledger_read.status_code, 200, ledger_read.text)
        self.assertEqual(len(ledger_read.json()["items"]), 1)

    def test_payment_routes_allow_accountant_and_block_contractor_writes(self):
        contractor_create = self.client.post(
            "/api/v1/payments/",
            headers=self.contractor_headers(),
            json={
                "contract_id": self.contract.id,
                "payment_date": "2026-03-26",
                "amount": 500,
            },
        )
        self.assertEqual(contractor_create.status_code, 403)

        accountant_create = self.client.post(
            "/api/v1/payments/",
            headers=self.accountant_headers(),
            json={
                "contract_id": self.contract.id,
                "payment_date": "2026-03-26",
                "amount": 500,
                "remarks": "Permission test payment",
            },
        )
        self.assertEqual(accountant_create.status_code, 201, accountant_create.text)
        self.assertEqual(accountant_create.json()["amount"], 500.0)

    def test_project_manager_can_review_ra_bills_but_is_blocked_from_settlement_routes(self):
        pm_ra_bill = self.client.post(
            "/api/v1/ra-bills/",
            headers=self.project_manager_headers(),
            json={
                "contract_id": self.contract.id,
                "bill_date": "2026-03-26",
                "remarks": "PM review draft",
            },
        )
        self.assertEqual(pm_ra_bill.status_code, 201, pm_ra_bill.text)
        self.assertEqual(pm_ra_bill.json()["status"], "draft")

        pm_payment = self.client.post(
            "/api/v1/payments/",
            headers=self.project_manager_headers(),
            json={
                "contract_id": self.contract.id,
                "payment_date": "2026-03-26",
                "amount": 500,
            },
        )
        self.assertEqual(pm_payment.status_code, 403)

        pm_secured_advance = self.client.post(
            "/api/v1/secured-advances/issue",
            headers=self.project_manager_headers(),
            json={
                "contract_id": self.contract.id,
                "advance_date": "2026-03-26",
                "description": "Blocked PM secured advance issue",
                "advance_amount": 1500,
            },
        )
        self.assertEqual(pm_secured_advance.status_code, 403)

    def test_project_manager_is_blocked_from_hidden_master_admin_routes(self):
        pm_companies = self.client.get(
            "/api/v1/companies/",
            headers=self.project_manager_headers(),
        )
        self.assertEqual(pm_companies.status_code, 200, pm_companies.text)

        pm_create_company = self.client.post(
            "/api/v1/companies/",
            headers=self.project_manager_headers(),
            json={"name": "Blocked PM Company"},
        )
        self.assertEqual(pm_create_company.status_code, 403)

        pm_update_company = self.client.put(
            f"/api/v1/companies/{self.company.id}",
            headers=self.project_manager_headers(),
            json={"name": "Blocked PM Company Update"},
        )
        self.assertEqual(pm_update_company.status_code, 403)

        pm_delete_vendor = self.client.delete(
            f"/api/v1/vendors/{self.vendor.id}",
            headers=self.project_manager_headers(),
        )
        self.assertEqual(pm_delete_vendor.status_code, 403)

        admin_delete_vendor = self.client.delete(
            f"/api/v1/vendors/{self.vendor.id}",
            headers=self.admin_headers(),
        )
        self.assertEqual(admin_delete_vendor.status_code, 400, admin_delete_vendor.text)

    def test_ai_boundary_route_is_admin_only_and_suggestion_only(self):
        unauthorized = self.client.get("/api/v1/ai-boundary")
        self.assertEqual(unauthorized.status_code, 401)

        viewer_policy = self.client.get(
            "/api/v1/ai-boundary",
            headers=self.viewer_headers(),
        )
        self.assertEqual(viewer_policy.status_code, 403)

        admin_policy = self.client.get(
            "/api/v1/ai-boundary",
            headers=self.admin_headers(),
        )
        self.assertEqual(admin_policy.status_code, 200, admin_policy.text)
        policy_payload = admin_policy.json()
        self.assertFalse(policy_payload["ai_enabled"])
        self.assertEqual(policy_payload["ai_mode"], "disabled")
        self.assertFalse(policy_payload["allow_state_changing_execution"])

        admin_evaluation = self.client.post(
            "/api/v1/ai-boundary/evaluate",
            headers=self.admin_headers(),
            json={"operation_type": "approve", "affects_state": True},
        )
        self.assertEqual(admin_evaluation.status_code, 200, admin_evaluation.text)
        self.assertFalse(admin_evaluation.json()["allowed"])


if __name__ == "__main__":
    unittest.main()
