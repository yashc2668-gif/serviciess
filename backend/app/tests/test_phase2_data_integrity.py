"""Phase 2 — Data Integrity & Multi-Tenancy tests.

Covers:
  2.1  Company-scoped queries (multi-tenancy isolation)
  2.3  Pagination response wrapper
  2.5  Cascade validation on deletes
  2.6  Data archival endpoint
"""

import unittest
from datetime import date
from decimal import Decimal

import app.db.base  # noqa: F401 — register all ORM models
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

import main
from app.core.security import hash_password
from app.db.session import Base, get_db
from app.models.boq import BOQItem
from app.models.company import Company
from app.models.contract import Contract
from app.models.labour import Labour
from app.models.labour_advance import LabourAdvance
from app.models.labour_attendance import LabourAttendance
from app.models.labour_bill import LabourBill
from app.models.labour_contractor import LabourContractor
from app.models.material import Material
from app.models.material_issue import MaterialIssue
from app.models.material_receipt import MaterialReceipt
from app.models.material_receipt_item import MaterialReceiptItem
from app.models.measurement import Measurement
from app.models.payment import Payment
from app.models.project import Project
from app.models.ra_bill import RABill
from app.models.secured_advance import SecuredAdvance
from app.models.user import User
from app.models.vendor import Vendor


def _login(client: TestClient, email: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


class Phase2BaseTest(unittest.TestCase):
    """Shared scaffold: two companies, each with a project + contract."""

    PASSWORD = "StrongPass123!"

    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(self.engine, "connect")
        def _enable_sqlite_fks(dbapi_conn, _rec):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(bind=self.engine)

        db = self.SessionLocal()

        # --- Two companies --------------------------------------------------
        self.company_a = Company(name="Company Alpha")
        self.company_b = Company(name="Company Beta")
        db.add_all([self.company_a, self.company_b])
        db.flush()

        # --- Users per company + one admin -----------------------------------
        hashed = hash_password(self.PASSWORD)
        self.admin_user = User(
            full_name="Super Admin",
            email="admin@test.com",
            hashed_password=hashed,
            role="admin",
            is_active=True,
        )
        self.user_a = User(
            full_name="User A",
            email="user_a@test.com",
            hashed_password=hashed,
            role="project_manager",
            is_active=True,
            company_id=self.company_a.id,
        )
        self.user_b = User(
            full_name="User B",
            email="user_b@test.com",
            hashed_password=hashed,
            role="project_manager",
            is_active=True,
            company_id=self.company_b.id,
        )
        db.add_all([self.admin_user, self.user_a, self.user_b])
        db.flush()

        # --- Vendors ---------------------------------------------------------
        self.vendor_a = Vendor(name="Vendor A", code="VEN-A-001", vendor_type="contractor")
        self.vendor_b = Vendor(name="Vendor B", code="VEN-B-001", vendor_type="contractor")
        db.add_all([self.vendor_a, self.vendor_b])
        db.flush()

        # --- Projects --------------------------------------------------------
        self.project_a = Project(
            company_id=self.company_a.id,
            name="Project Alpha",
            code="PRJ-A-001",
            original_value=Decimal("500000.00"),
            revised_value=Decimal("500000.00"),
            status="active",
        )
        self.project_b = Project(
            company_id=self.company_b.id,
            name="Project Beta",
            code="PRJ-B-001",
            original_value=Decimal("300000.00"),
            revised_value=Decimal("300000.00"),
            status="active",
        )
        db.add_all([self.project_a, self.project_b])
        db.flush()

        # --- Contracts -------------------------------------------------------
        self.contract_a = Contract(
            project_id=self.project_a.id,
            vendor_id=self.vendor_a.id,
            contract_no="CTR-A-001",
            title="Alpha Contract",
            original_value=Decimal("200000.00"),
            revised_value=Decimal("200000.00"),
            status="active",
        )
        self.contract_b = Contract(
            project_id=self.project_b.id,
            vendor_id=self.vendor_b.id,
            contract_no="CTR-B-001",
            title="Beta Contract",
            original_value=Decimal("150000.00"),
            revised_value=Decimal("150000.00"),
            status="active",
        )
        db.add_all([self.contract_a, self.contract_b])
        db.commit()

        self.db = db

        # --- TestClient with DI override -------------------------------------
        def override_get_db():
            session = self.SessionLocal()
            try:
                yield session
            finally:
                session.close()

        main.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()
        main.app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()


# ── 2.1  Company-scoped query isolation ─────────────────────────────────────


class TestCompanyScopedQueries(Phase2BaseTest):
    """Non-admin users must only see records belonging to their company."""

    def test_user_a_only_sees_company_a_projects(self):
        token = _login(self.client, "user_a@test.com", self.PASSWORD)
        resp = self.client.get(
            "/api/v1/projects/",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("items", data)
        names = [p["name"] for p in data["items"]]
        self.assertIn("Project Alpha", names)
        self.assertNotIn("Project Beta", names)

    def test_user_b_only_sees_company_b_projects(self):
        token = _login(self.client, "user_b@test.com", self.PASSWORD)
        resp = self.client.get(
            "/api/v1/projects/",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        names = [p["name"] for p in data["items"]]
        self.assertIn("Project Beta", names)
        self.assertNotIn("Project Alpha", names)

    def test_admin_sees_all_projects(self):
        token = _login(self.client, "admin@test.com", self.PASSWORD)
        resp = self.client.get(
            "/api/v1/projects/",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        names = [p["name"] for p in data["items"]]
        self.assertIn("Project Alpha", names)
        self.assertIn("Project Beta", names)

    def test_user_a_only_sees_company_a_contracts(self):
        token = _login(self.client, "user_a@test.com", self.PASSWORD)
        resp = self.client.get(
            "/api/v1/contracts/",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        titles = [c["title"] for c in data["items"]]
        self.assertIn("Alpha Contract", titles)
        self.assertNotIn("Beta Contract", titles)

    def test_user_a_only_sees_company_a_mis_summary(self):
        alpha_bill = RABill(
            contract_id=self.contract_a.id,
            bill_no=1,
            bill_date=date(2026, 3, 24),
            gross_amount=Decimal("1000.00"),
            total_deductions=Decimal("0.00"),
            net_payable=Decimal("1000.00"),
            status="approved",
        )
        beta_bill = RABill(
            contract_id=self.contract_b.id,
            bill_no=1,
            bill_date=date(2026, 3, 24),
            gross_amount=Decimal("2000.00"),
            total_deductions=Decimal("0.00"),
            net_payable=Decimal("2000.00"),
            status="approved",
        )
        self.db.add_all([alpha_bill, beta_bill])
        self.db.commit()

        token = _login(self.client, "user_a@test.com", self.PASSWORD)
        resp = self.client.get(
            "/api/v1/reports/mis-summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(data["summary"]["project_count"], 1)
        self.assertEqual(len(data["top_outstanding_projects"]), 1)
        self.assertEqual(data["top_outstanding_projects"][0]["project_name"], "Project Alpha")
        self.assertEqual(data["top_outstanding_projects"][0]["outstanding_amount"], 1000.0)


# ── 2.3  Pagination response wrapper ────────────────────────────────────────


class TestPaginationResponse(Phase2BaseTest):
    """All list endpoints must return {items, total, page, limit}."""

    def test_projects_list_returns_paginated_envelope(self):
        token = _login(self.client, "admin@test.com", self.PASSWORD)
        resp = self.client.get(
            "/api/v1/projects/?page=1&limit=10",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("items", data)
        self.assertIn("total", data)
        self.assertIn("page", data)
        self.assertIn("limit", data)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["limit"], 10)
        self.assertIsInstance(data["items"], list)
        self.assertGreaterEqual(data["total"], len(data["items"]))

    def test_contracts_pagination(self):
        token = _login(self.client, "admin@test.com", self.PASSWORD)
        resp = self.client.get(
            "/api/v1/contracts/?page=1&limit=1",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["limit"], 1)
        self.assertLessEqual(len(data["items"]), 1)
        self.assertGreaterEqual(data["total"], 2)  # We created 2 contracts

    def test_users_pagination(self):
        token = _login(self.client, "admin@test.com", self.PASSWORD)
        resp = self.client.get(
            "/api/v1/users/?page=1&limit=50",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("items", data)
        self.assertIn("total", data)
        self.assertGreaterEqual(data["total"], 3)  # admin + user_a + user_b


# ── 2.5  Cascade validation on deletes ──────────────────────────────────────


class TestCascadeDeleteValidation(Phase2BaseTest):
    """Deletes must be blocked when active children exist."""

    def _admin_headers(self):
        token = _login(self.client, "admin@test.com", self.PASSWORD)
        return {"Authorization": f"Bearer {token}"}

    def _assert_delete_blocked(self, resp, expected_keyword: str):
        """Assert a 400 response with the expected dependency in error message."""
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        msg = body.get("detail") or body.get("error", {}).get("message", "")
        self.assertIn(expected_keyword, msg)

    # -- Contract delete cascade --

    def test_contract_delete_blocked_with_active_ra_bill(self):
        """Cannot delete contract when non-cancelled RA bills exist."""
        ra = RABill(
            contract_id=self.contract_a.id,
            bill_no=1,
            bill_date=date(2026, 1, 15),
            status="draft",
        )
        self.db.add(ra)
        self.db.commit()

        resp = self.client.delete(
            f"/api/v1/contracts/{self.contract_a.id}",
            headers=self._admin_headers(),
        )
        self._assert_delete_blocked(resp, "active_ra_bills")

    def test_contract_delete_blocked_with_active_payment(self):
        """Cannot delete contract when non-cancelled payments exist."""
        pmt = Payment(
            contract_id=self.contract_a.id,
            amount=Decimal("5000.00"),
            payment_date=date(2026, 1, 15),
            status="approved",
        )
        self.db.add(pmt)
        self.db.commit()

        resp = self.client.delete(
            f"/api/v1/contracts/{self.contract_a.id}",
            headers=self._admin_headers(),
        )
        self._assert_delete_blocked(resp, "active_payments")

    def test_contract_delete_blocked_with_boq(self):
        """Cannot delete contract when BOQ items exist."""
        boq = BOQItem(
            contract_id=self.contract_a.id,
            item_code="BOQ-001",
            description="Test BOQ",
            unit="m3",
            quantity=Decimal("100.00"),
            rate=Decimal("500.00"),
            amount=Decimal("50000.00"),
        )
        self.db.add(boq)
        self.db.commit()

        resp = self.client.delete(
            f"/api/v1/contracts/{self.contract_a.id}",
            headers=self._admin_headers(),
        )
        self._assert_delete_blocked(resp, "boq_items")

    def test_contract_delete_succeeds_when_clean(self):
        """Contract B has no children and should delete cleanly."""
        resp = self.client.delete(
            f"/api/v1/contracts/{self.contract_b.id}",
            headers=self._admin_headers(),
        )
        self.assertEqual(resp.status_code, 204)

    # -- Labour contractor delete cascade --

    def test_labour_contractor_delete_blocked_with_active_labour(self):
        """Cannot deactivate contractor with active labour records."""
        contractor = LabourContractor(
            company_id=self.company_a.id,
            contractor_code="LCTR-TEST-001",
            contractor_name="Test Contractor",
        )
        self.db.add(contractor)
        self.db.flush()

        labour = Labour(
            contractor_id=contractor.id,
            company_id=self.company_a.id,
            full_name="Test Worker",
            labour_code="LAB-TEST-001",
            skill_type="mason",
        )
        self.db.add(labour)
        self.db.commit()

        resp = self.client.delete(
            f"/api/v1/labour-contractors/{contractor.id}",
            headers=self._admin_headers(),
        )
        self._assert_delete_blocked(resp, "active_labour")

    # -- Project delete cascade (pre-existing) --

    def test_project_delete_blocked_with_contracts(self):
        """Cannot delete a project with active contracts."""
        resp = self.client.delete(
            f"/api/v1/projects/{self.project_a.id}",
            headers=self._admin_headers(),
        )
        self._assert_delete_blocked(resp, "active_contracts")


# ── 2.6  Data archival endpoint ─────────────────────────────────────────────


class TestFinancialArchival(Phase2BaseTest):
    """Financial archival endpoint should archive terminal records."""

    def test_archive_fiscal_close_returns_summary(self):
        token = _login(self.client, "admin@test.com", self.PASSWORD)
        resp = self.client.post(
            "/api/v1/financial-archives/fiscal-close",
            json={"fiscal_year_end": "2025-03-31", "include_secured_advances": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("archive_batch_id", data)
        self.assertIn("archived_payments", data)
        self.assertIn("archived_ra_bills", data)
        self.assertIn("archived_secured_advances", data)
        self.assertTrue(data["archive_batch_id"].startswith("fy-close-"))


if __name__ == "__main__":
    unittest.main()
