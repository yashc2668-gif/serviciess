"""API-level integration tests for finance-heavy routes."""

import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import app.db.base  # noqa: F401
import main
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.core.config import settings
from app.db.session import Base, get_db
from app.models.audit_log import AuditLog
from app.models.boq import BOQItem
from app.models.company import Company
from app.models.contract import Contract
from app.models.inventory_transaction import InventoryTransaction
from app.models.labour_advance import LabourAdvance
from app.models.labour_attendance import LabourAttendance
from app.models.labour_bill import LabourBill
from app.models.labour_contractor import LabourContractor
from app.models.material import Material
from app.models.measurement import Measurement
from app.models.measurement_item import MeasurementItem
from app.models.payment import Payment
from app.models.project import Project
from app.models.ra_bill import RABill
from app.models.user import User
from app.models.vendor import Vendor
from app.models.work_done import WorkDoneItem


class ApiIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.company = Company(name="API Test Company")
        self.admin_user = User(
            full_name="API Admin",
            email="api-admin@example.com",
            hashed_password=hash_password("StrongPass123"),
            role="admin",
            is_active=True,
        )
        self.contractor_user = User(
            full_name="API Contractor",
            email="api-contractor@example.com",
            hashed_password=hash_password("StrongPass123"),
            role="contractor",
            is_active=True,
        )
        self.accountant_user = User(
            full_name="API Accountant",
            email="api-accountant@example.com",
            hashed_password=hash_password("StrongPass123"),
            role="accountant",
            is_active=True,
        )
        self.vendor = Vendor(name="API Vendor", code="API-VEN-001", vendor_type="contractor")
        self.db.add_all([self.company, self.admin_user, self.contractor_user, self.accountant_user, self.vendor])
        self.db.flush()

        # Assign company scope to non-admin users and vendor.
        for user in (self.contractor_user, self.accountant_user):
            user.company_id = self.company.id
        self.vendor.company_id = self.company.id

        self.project = Project(
            company_id=self.company.id,
            name="API Baseline Project",
            code="API-PRJ-001",
            original_value=Decimal("100000.00"),
            revised_value=Decimal("100000.00"),
            status="active",
        )
        self.db.add(self.project)
        self.db.flush()

        self.contract = Contract(
            project_id=self.project.id,
            vendor_id=self.vendor.id,
            contract_no="API-CTR-001",
            title="API Baseline Contract",
            original_value=Decimal("100000.00"),
            revised_value=Decimal("100000.00"),
            retention_percentage=Decimal("5.00"),
            status="active",
        )
        self.db.add(self.contract)
        self.db.commit()
        self.db.refresh(self.project)
        self.db.refresh(self.contract)

        self.seed_patch = patch("main.run_seed", lambda: None)
        self.seed_patch.start()
        self.health_patch = patch(
            "main._database_health_payload",
            lambda: {"status": "ok", "database": "test", "user": "test", "ping": 1},
        )
        self.health_patch.start()
        self.upload_dir = tempfile.TemporaryDirectory()
        self.storage_root_patch = patch.object(settings, "LOCAL_STORAGE_ROOT", self.upload_dir.name)
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
        self.upload_dir.cleanup()
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

    def seed_boq_and_work_done(self):
        boq_item = BOQItem(
            contract_id=self.contract.id,
            item_code="BOQ-API-001",
            description="Concrete Work",
            unit="cum",
            quantity=Decimal("100.000"),
            rate=Decimal("1000.00"),
            amount=Decimal("100000.00"),
        )
        self.db.add(boq_item)
        self.db.flush()

        measurement = Measurement(
            contract_id=self.contract.id,
            measurement_no="MEAS-API-001",
            measurement_date=date(2026, 3, 24),
            status="approved",
            created_by=self.admin_user.id,
            approved_by=self.admin_user.id,
        )
        self.db.add(measurement)
        self.db.flush()

        measurement_item = MeasurementItem(
            measurement_id=measurement.id,
            boq_item_id=boq_item.id,
            description_snapshot=boq_item.description,
            unit_snapshot=boq_item.unit,
            previous_quantity=Decimal("0.000"),
            current_quantity=Decimal("10.000"),
            cumulative_quantity=Decimal("10.000"),
            rate=Decimal("1000.00"),
            amount=Decimal("10000.00"),
            allow_excess=False,
        )
        self.db.add(measurement_item)
        self.db.flush()

        work_done = WorkDoneItem(
            contract_id=self.contract.id,
            measurement_id=measurement.id,
            measurement_item_id=measurement_item.id,
            boq_item_id=boq_item.id,
            recorded_date=measurement.measurement_date,
            previous_quantity=Decimal("0.000"),
            current_quantity=Decimal("10.000"),
            cumulative_quantity=Decimal("10.000"),
            rate=Decimal("1000.00"),
            amount=Decimal("10000.00"),
            approved_by=self.admin_user.id,
        )
        self.db.add(work_done)
        self.db.commit()
        self.db.refresh(boq_item)
        self.db.refresh(measurement)
        self.db.refresh(work_done)
        return boq_item, measurement, work_done

    def seed_approved_bill(self, *, bill_no: int = 1, net_payable: str = "1000.00") -> RABill:
        bill = RABill(
            contract_id=self.contract.id,
            bill_no=bill_no,
            bill_date=date(2026, 3, 24),
            gross_amount=Decimal(net_payable),
            total_deductions=Decimal("0.00"),
            net_payable=Decimal(net_payable),
            status="approved",
            approved_by=self.admin_user.id,
        )
        self.db.add(bill)
        self.db.commit()
        self.db.refresh(bill)
        return bill

    def test_finance_endpoints_require_auth_and_role_checks(self):
        no_token = self.client.post(
            "/api/v1/payments/",
            json={
                "contract_id": self.contract.id,
                "payment_date": "2026-03-24",
                "amount": 500,
            },
        )
        self.assertEqual(no_token.status_code, 401)

        contractor = self.client.post(
            "/api/v1/payments/",
            headers=self.contractor_headers(),
            json={
                "contract_id": self.contract.id,
                "payment_date": "2026-03-24",
                "amount": 500,
            },
        )
        self.assertEqual(contractor.status_code, 403)

        validation_error = self.client.post(
            "/api/v1/payments/",
            headers=self.admin_headers(),
            json={
                "contract_id": self.contract.id,
                "payment_date": "2026-03-24",
                "amount": 0,
            },
        )
        self.assertEqual(validation_error.status_code, 422)

        success = self.client.post(
            "/api/v1/payments/",
            headers=self.admin_headers(),
            json={
                "contract_id": self.contract.id,
                "payment_date": "2026-03-24",
                "amount": 500,
                "remarks": "API create payment",
            },
        )
        self.assertEqual(success.status_code, 201, success.text)

    def test_foundation_idempotency_replays_successful_post_without_duplicate_side_effects(self):
        headers = self.admin_headers()
        headers["Idempotency-Key"] = "payment-create-001"
        payload = {
            "contract_id": self.contract.id,
            "payment_date": "2026-03-24",
            "amount": 750,
            "remarks": "Idempotent payment",
        }

        first_response = self.client.post(
            "/api/v1/payments/",
            headers=headers,
            json=payload,
        )
        self.assertEqual(first_response.status_code, 201, first_response.text)

        second_response = self.client.post(
            "/api/v1/payments/",
            headers=headers,
            json=payload,
        )
        self.assertEqual(second_response.status_code, 201, second_response.text)
        self.assertEqual(first_response.json()["id"], second_response.json()["id"])
        self.assertEqual(second_response.headers.get("X-Idempotency-Replayed"), "true")
        self.assertEqual(self.db.query(Payment).count(), 1)
        self.assertEqual(
            self.db.query(AuditLog)
            .filter(AuditLog.entity_type == "payment", AuditLog.action == "create")
            .count(),
            1,
        )

        changed_payload = dict(payload)
        changed_payload["amount"] = 900
        conflict_response = self.client.post(
            "/api/v1/payments/",
            headers=headers,
            json=changed_payload,
        )
        self.assertEqual(conflict_response.status_code, 409, conflict_response.text)
        self.assertEqual(conflict_response.json()["error"]["type"], "validation_error")

    def test_foundation_pagination_validates_and_limits_list_endpoints(self):
        headers = self.admin_headers()
        first = self.client.post(
            "/api/v1/payments/",
            headers=headers,
            json={
                "contract_id": self.contract.id,
                "payment_date": "2026-03-24",
                "amount": 500,
                "remarks": "First paged payment",
            },
        )
        second = self.client.post(
            "/api/v1/payments/",
            headers=headers,
            json={
                "contract_id": self.contract.id,
                "payment_date": "2026-03-25",
                "amount": 600,
                "remarks": "Second paged payment",
            },
        )
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(second.status_code, 201, second.text)

        paged_response = self.client.get(
            "/api/v1/payments/?limit=1&skip=0",
            headers=self.accountant_headers(),
        )
        self.assertEqual(paged_response.status_code, 200, paged_response.text)
        self.assertEqual(len(paged_response.json()["items"]), 1)
        self.assertEqual(paged_response.json()["items"][0]["id"], second.json()["id"])

        invalid_limit = self.client.get(
            "/api/v1/payments/?limit=0",
            headers=self.accountant_headers(),
        )
        self.assertEqual(invalid_limit.status_code, 422)
        self.assertEqual(invalid_limit.json()["error"]["type"], "validation_error")

    def test_project_contract_and_boq_endpoints_work_through_api(self):
        headers = self.admin_headers()

        project_response = self.client.post(
            "/api/v1/projects/",
            headers=headers,
            json={
                "company_id": self.company.id,
                "name": "API Created Project",
                "code": "API-PRJ-NEW",
            },
        )
        self.assertEqual(project_response.status_code, 201, project_response.text)
        project_id = project_response.json()["id"]

        vendor_response = self.client.post(
            "/api/v1/vendors/",
            headers=headers,
            json={
                "name": "API Created Vendor",
                "code": "API-VEN-NEW",
                "vendor_type": "supplier",
                "company_id": self.company.id,
            },
        )
        self.assertEqual(vendor_response.status_code, 201, vendor_response.text)
        vendor_id = vendor_response.json()["id"]

        contract_response = self.client.post(
            "/api/v1/contracts/",
            headers=headers,
            json={
                "project_id": project_id,
                "vendor_id": vendor_id,
                "contract_no": "API-CTR-NEW",
                "title": "API Created Contract",
                "original_value": 25000,
                "revised_value": 25000,
                "retention_percentage": 5,
            },
        )
        self.assertEqual(contract_response.status_code, 201, contract_response.text)
        contract_id = contract_response.json()["id"]

        boq_response = self.client.post(
            f"/api/v1/contracts/{contract_id}/boq-items/",
            headers=headers,
            json={
                "item_code": "API-BOQ-1",
                "description": "Steel work",
                "unit": "kg",
                "quantity": 100,
                "rate": 50,
            },
        )
        self.assertEqual(boq_response.status_code, 201, boq_response.text)
        self.assertEqual(boq_response.json()["amount"], 5000.0)

        invalid_boq = self.client.post(
            f"/api/v1/contracts/{contract_id}/boq-items/",
            headers=headers,
            json={"unit": "kg"},
        )
        self.assertEqual(invalid_boq.status_code, 422)

    def test_material_master_endpoints_support_crud_filters_and_permissions(self):
        unauthorized = self.client.post(
            "/api/v1/materials/",
            json={
                "item_code": "MAT-001",
                "item_name": "Cement OPC 53",
                "category": "Cement",
                "unit": "bag",
                "reorder_level": 50,
                "default_rate": 365,
                "current_stock": 120,
                "company_id": self.company.id,
                "project_id": self.project.id,
            },
        )
        self.assertEqual(unauthorized.status_code, 401)

        contractor_create = self.client.post(
            "/api/v1/materials/",
            headers=self.contractor_headers(),
            json={
                "item_code": "MAT-001",
                "item_name": "Cement OPC 53",
                "category": "Cement",
                "unit": "bag",
                "reorder_level": 50,
                "default_rate": 365,
                "current_stock": 120,
                "company_id": self.company.id,
                "project_id": self.project.id,
            },
        )
        self.assertEqual(contractor_create.status_code, 403)

        create_response = self.client.post(
            "/api/v1/materials/",
            headers=self.admin_headers(),
            json={
                "item_code": "mat-001",
                "item_name": "Cement OPC 53",
                "category": "Cement",
                "unit": "bag",
                "reorder_level": 50,
                "default_rate": 365,
                "current_stock": 120,
                "project_id": self.project.id,
            },
        )
        self.assertEqual(create_response.status_code, 201, create_response.text)
        payload = create_response.json()
        material_id = payload["id"]
        self.assertEqual(payload["item_code"], "MAT-001")
        self.assertEqual(payload["company_id"], self.company.id)
        self.assertTrue(payload["is_active"])

        duplicate_code = self.client.post(
            "/api/v1/materials/",
            headers=self.admin_headers(),
            json={
                "item_code": "MAT-001",
                "item_name": "Another Cement",
                "category": "Cement",
                "unit": "bag",
            },
        )
        self.assertEqual(duplicate_code.status_code, 400)

        list_response = self.client.get(
            "/api/v1/materials/?search=cement&is_active=true",
            headers=self.accountant_headers(),
        )
        self.assertEqual(list_response.status_code, 200, list_response.text)
        listed_materials = list_response.json()["items"]
        self.assertEqual(len(listed_materials), 1)
        self.assertEqual(listed_materials[0]["id"], material_id)

        update_response = self.client.put(
            f"/api/v1/materials/{material_id}",
            headers=self.admin_headers(),
            json={
                "current_stock": 75,
                "default_rate": 372.5,
                "is_active": False,
            },
        )
        self.assertEqual(update_response.status_code, 200, update_response.text)
        updated_payload = update_response.json()
        self.assertEqual(updated_payload["current_stock"], 75.0)
        self.assertEqual(updated_payload["default_rate"], 372.5)
        self.assertFalse(updated_payload["is_active"])

        patch_response = self.client.patch(
            f"/api/v1/materials/{material_id}",
            headers=self.admin_headers(),
            json={
                "item_name": "Cement OPC 53 - Updated",
                "is_active": True,
            },
        )
        self.assertEqual(patch_response.status_code, 200, patch_response.text)
        patched_payload = patch_response.json()
        self.assertEqual(patched_payload["item_name"], "Cement OPC 53 - Updated")
        self.assertTrue(patched_payload["is_active"])

        detail_response = self.client.get(
            f"/api/v1/materials/{material_id}",
            headers=self.contractor_headers(),
        )
        self.assertEqual(detail_response.status_code, 200, detail_response.text)
        self.assertEqual(detail_response.json()["id"], material_id)

    def test_material_requisition_endpoints_support_items_and_qty_workflow(self):
        material = Material(
            item_code="REQ-MAT-001",
            item_name="TMT Steel",
            category="Steel",
            unit="kg",
            reorder_level=100,
            default_rate=68,
            current_stock=500,
            is_active=True,
            company_id=self.company.id,
            project_id=self.project.id,
        )
        self.db.add(material)
        self.db.commit()
        self.db.refresh(material)

        unauthorized = self.client.post(
            "/api/v1/material-requisitions",
            json={
                "requisition_no": "MR-API-001",
                "project_id": self.project.id,
                "items": [
                    {
                        "material_id": material.id,
                        "requested_qty": 120,
                        "approved_qty": 0,
                        "issued_qty": 0,
                    }
                ],
            },
        )
        self.assertEqual(unauthorized.status_code, 401)

        contractor_create = self.client.post(
            "/api/v1/material-requisitions",
            headers=self.contractor_headers(),
            json={
                "requisition_no": "MR-API-001",
                "project_id": self.project.id,
                "items": [
                    {
                        "material_id": material.id,
                        "requested_qty": 120,
                    }
                ],
            },
        )
        self.assertEqual(contractor_create.status_code, 403)

        create_response = self.client.post(
            "/api/v1/material-requisitions",
            headers=self.admin_headers(),
            json={
                "requisition_no": "mr-api-001",
                "project_id": self.project.id,
                "remarks": "Site requirement",
                "items": [
                    {
                        "material_id": material.id,
                        "requested_qty": 120,
                        "approved_qty": 100,
                        "issued_qty": 40,
                    }
                ],
            },
        )
        self.assertEqual(create_response.status_code, 201, create_response.text)
        payload = create_response.json()
        requisition_id = payload["id"]
        requisition_item_id = payload["items"][0]["id"]
        self.assertEqual(payload["requisition_no"], "MR-API-001")
        self.assertEqual(payload["status"], "draft")
        self.assertEqual(payload["requested_by"], self.admin_user.id)

        duplicate_no = self.client.post(
            "/api/v1/material-requisitions",
            headers=self.admin_headers(),
            json={
                "requisition_no": "MR-API-001",
                "project_id": self.project.id,
                "items": [
                    {
                        "material_id": material.id,
                        "requested_qty": 10,
                    }
                ],
            },
        )
        self.assertEqual(duplicate_no.status_code, 400)

        contractor_submit = self.client.post(
            f"/api/v1/material-requisitions/{requisition_id}/submit",
            headers=self.contractor_headers(),
            json={"remarks": "Need urgent release"},
        )
        self.assertEqual(contractor_submit.status_code, 403)

        submit_response = self.client.post(
            f"/api/v1/material-requisitions/{requisition_id}/submit",
            headers=self.admin_headers(),
            json={"remarks": "Submitted for approval"},
        )
        self.assertEqual(submit_response.status_code, 200, submit_response.text)
        submitted = submit_response.json()
        self.assertEqual(submitted["status"], "submitted")
        self.assertEqual(submitted["remarks"], "Submitted for approval")

        list_response = self.client.get(
            f"/api/v1/material-requisitions/?project_id={self.project.id}&status=submitted",
            headers=self.accountant_headers(),
        )
        self.assertEqual(list_response.status_code, 200, list_response.text)
        listed = list_response.json()["items"]
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["id"], requisition_id)

        bad_qty = self.client.post(
            f"/api/v1/material-requisitions/{requisition_id}/approve",
            headers=self.admin_headers(),
            json={
                "items": [
                    {
                        "id": requisition_item_id,
                        "approved_qty": 50,
                        "issued_qty": 60,
                    }
                ],
            },
        )
        self.assertEqual(bad_qty.status_code, 400)

        approve_response = self.client.post(
            f"/api/v1/material-requisitions/{requisition_id}/approve",
            headers=self.admin_headers(),
            json={
                "remarks": "Approved by PM",
                "items": [
                    {
                        "id": requisition_item_id,
                        "approved_qty": 110,
                        "issued_qty": 90,
                    }
                ],
            },
        )
        self.assertEqual(approve_response.status_code, 200, approve_response.text)
        approved = approve_response.json()
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["remarks"], "Approved by PM")
        self.assertEqual(approved["items"][0]["approved_qty"], 110.0)
        self.assertEqual(approved["items"][0]["issued_qty"], 90.0)

        resubmit_after_approval = self.client.post(
            f"/api/v1/material-requisitions/{requisition_id}/submit",
            headers=self.admin_headers(),
            json={"remarks": "Resubmit"},
        )
        self.assertEqual(resubmit_after_approval.status_code, 400)

        second_requisition = self.client.post(
            "/api/v1/material-requisitions",
            headers=self.admin_headers(),
            json={
                "requisition_no": "MR-API-002",
                "project_id": self.project.id,
                "status": "submitted",
                "items": [
                    {
                        "material_id": material.id,
                        "requested_qty": 30,
                    }
                ],
            },
        )
        self.assertEqual(second_requisition.status_code, 201, second_requisition.text)
        second_requisition_id = second_requisition.json()["id"]

        reject_response = self.client.post(
            f"/api/v1/material-requisitions/{second_requisition_id}/reject",
            headers=self.admin_headers(),
            json={"remarks": "Quantity not justified"},
        )
        self.assertEqual(reject_response.status_code, 200, reject_response.text)
        rejected = reject_response.json()
        self.assertEqual(rejected["status"], "rejected")
        self.assertEqual(rejected["remarks"], "Quantity not justified")

        detail_response = self.client.get(
            f"/api/v1/material-requisitions/{requisition_id}",
            headers=self.contractor_headers(),
        )
        self.assertEqual(detail_response.status_code, 200, detail_response.text)
        self.assertEqual(detail_response.json()["id"], requisition_id)

    def test_material_receipt_endpoints_update_material_stock_from_vendor_receipts(self):
        material = Material(
            item_code="RCV-MAT-001",
            item_name="Cement OPC 43",
            category="Cement",
            unit="bag",
            reorder_level=80,
            default_rate=340,
            current_stock=200,
            is_active=True,
            company_id=self.company.id,
            project_id=self.project.id,
        )
        self.db.add(material)
        self.db.commit()
        self.db.refresh(material)

        unauthorized = self.client.post(
            "/api/v1/material-receipts",
            json={
                "receipt_no": "MRC-API-001",
                "vendor_id": self.vendor.id,
                "project_id": self.project.id,
                "receipt_date": "2026-03-26",
                "items": [{"material_id": material.id, "received_qty": 50, "unit_rate": 360}],
            },
        )
        self.assertEqual(unauthorized.status_code, 401)

        contractor_create = self.client.post(
            "/api/v1/material-receipts",
            headers=self.contractor_headers(),
            json={
                "receipt_no": "MRC-API-001",
                "vendor_id": self.vendor.id,
                "project_id": self.project.id,
                "receipt_date": "2026-03-26",
                "items": [{"material_id": material.id, "received_qty": 50, "unit_rate": 360}],
            },
        )
        self.assertEqual(contractor_create.status_code, 403)

        create_response = self.client.post(
            "/api/v1/material-receipts",
            headers=self.admin_headers(),
            json={
                "receipt_no": "mrc-api-001",
                "vendor_id": self.vendor.id,
                "project_id": self.project.id,
                "receipt_date": "2026-03-26",
                "status": "received",
                "remarks": "Vendor truck inward",
                "items": [{"material_id": material.id, "received_qty": 50, "unit_rate": 360}],
            },
        )
        self.assertEqual(create_response.status_code, 201, create_response.text)
        payload = create_response.json()
        receipt_id = payload["id"]
        receipt_item_id = payload["items"][0]["id"]
        self.assertEqual(payload["receipt_no"], "MRC-API-001")
        self.assertEqual(payload["total_amount"], 18000.0)

        material_after_create = self.client.get(
            f"/api/v1/materials/{material.id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(material_after_create.status_code, 200)
        self.assertEqual(material_after_create.json()["current_stock"], 250.0)

        update_response = self.client.put(
            f"/api/v1/material-receipts/{receipt_id}",
            headers=self.admin_headers(),
            json={
                "items": [{"id": receipt_item_id, "received_qty": 80, "unit_rate": 365}],
            },
        )
        self.assertEqual(update_response.status_code, 200, update_response.text)
        updated_payload = update_response.json()
        self.assertEqual(updated_payload["total_amount"], 29200.0)

        material_after_update = self.client.get(
            f"/api/v1/materials/{material.id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(material_after_update.status_code, 200)
        self.assertEqual(material_after_update.json()["current_stock"], 280.0)

        cancel_response = self.client.put(
            f"/api/v1/material-receipts/{receipt_id}",
            headers=self.admin_headers(),
            json={"status": "cancelled"},
        )
        self.assertEqual(cancel_response.status_code, 200, cancel_response.text)
        self.assertEqual(cancel_response.json()["status"], "cancelled")

        material_after_cancel = self.client.get(
            f"/api/v1/materials/{material.id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(material_after_cancel.status_code, 200)
        self.assertEqual(material_after_cancel.json()["current_stock"], 200.0)

        list_response = self.client.get(
            "/api/v1/material-receipts?status=cancelled",
            headers=self.accountant_headers(),
        )
        self.assertEqual(list_response.status_code, 200, list_response.text)
        self.assertEqual(len(list_response.json()["items"]), 1)
        self.assertEqual(list_response.json()["items"][0]["id"], receipt_id)

    def test_material_issue_endpoints_reduce_and_restore_stock_for_site_activity_issues(self):
        material = Material(
            item_code="ISS-MAT-001",
            item_name="TMT Bar 12mm",
            category="Steel",
            unit="kg",
            reorder_level=150,
            default_rate=68,
            current_stock=220,
            is_active=True,
            company_id=self.company.id,
            project_id=self.project.id,
        )
        self.db.add(material)
        self.db.commit()
        self.db.refresh(material)

        unauthorized = self.client.post(
            "/api/v1/material-issues",
            json={
                "issue_no": "MIS-API-001",
                "project_id": self.project.id,
                "issue_date": "2026-03-26",
                "items": [{"material_id": material.id, "issued_qty": 30, "unit_rate": 70}],
            },
        )
        self.assertEqual(unauthorized.status_code, 401)

        contractor_create = self.client.post(
            "/api/v1/material-issues",
            headers=self.contractor_headers(),
            json={
                "issue_no": "MIS-API-001",
                "project_id": self.project.id,
                "issue_date": "2026-03-26",
                "items": [{"material_id": material.id, "issued_qty": 30, "unit_rate": 70}],
            },
        )
        self.assertEqual(contractor_create.status_code, 403)

        create_response = self.client.post(
            "/api/v1/material-issues",
            headers=self.admin_headers(),
            json={
                "issue_no": "mis-api-001",
                "project_id": self.project.id,
                "issue_date": "2026-03-26",
                "status": "issued",
                "site_name": "Site Block A",
                "activity_name": "Column reinforcement",
                "remarks": "Issued for footing work",
                "items": [{"material_id": material.id, "issued_qty": 30, "unit_rate": 70}],
            },
        )
        self.assertEqual(create_response.status_code, 201, create_response.text)
        payload = create_response.json()
        issue_id = payload["id"]
        issue_item_id = payload["items"][0]["id"]
        self.assertEqual(payload["issue_no"], "MIS-API-001")
        self.assertEqual(payload["issued_by"], self.admin_user.id)
        self.assertEqual(payload["total_amount"], 2100.0)

        material_after_create = self.client.get(
            f"/api/v1/materials/{material.id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(material_after_create.status_code, 200)
        self.assertEqual(material_after_create.json()["current_stock"], 190.0)

        update_response = self.client.put(
            f"/api/v1/material-issues/{issue_id}",
            headers=self.admin_headers(),
            json={
                "items": [{"id": issue_item_id, "issued_qty": 50, "unit_rate": 72}],
            },
        )
        self.assertEqual(update_response.status_code, 200, update_response.text)
        updated_payload = update_response.json()
        self.assertEqual(updated_payload["items"][0]["issued_qty"], 50.0)
        self.assertEqual(updated_payload["total_amount"], 3600.0)

        material_after_update = self.client.get(
            f"/api/v1/materials/{material.id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(material_after_update.status_code, 200)
        self.assertEqual(material_after_update.json()["current_stock"], 170.0)

        cancel_response = self.client.put(
            f"/api/v1/material-issues/{issue_id}",
            headers=self.admin_headers(),
            json={"status": "cancelled"},
        )
        self.assertEqual(cancel_response.status_code, 200, cancel_response.text)
        self.assertEqual(cancel_response.json()["status"], "cancelled")

        material_after_cancel = self.client.get(
            f"/api/v1/materials/{material.id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(material_after_cancel.status_code, 200)
        self.assertEqual(material_after_cancel.json()["current_stock"], 220.0)

        list_response = self.client.get(
            "/api/v1/material-issues?status=cancelled",
            headers=self.accountant_headers(),
        )
        self.assertEqual(list_response.status_code, 200, list_response.text)
        self.assertEqual(len(list_response.json()["items"]), 1)
        self.assertEqual(list_response.json()["items"][0]["id"], issue_id)

    def test_stock_ledger_endpoint_tracks_receipts_issues_and_manual_adjustments(self):
        material = Material(
            item_code="LEDGER-MAT-001",
            item_name="PPC Cement",
            category="Cement",
            unit="bag",
            reorder_level=80,
            default_rate=345,
            current_stock=100,
            is_active=True,
            company_id=self.company.id,
            project_id=self.project.id,
        )
        self.db.add(material)
        self.db.commit()
        self.db.refresh(material)

        receipt_response = self.client.post(
            "/api/v1/material-receipts",
            headers=self.admin_headers(),
            json={
                "receipt_no": "LEDGER-RCV-001",
                "vendor_id": self.vendor.id,
                "project_id": self.project.id,
                "receipt_date": "2026-03-26",
                "status": "received",
                "items": [{"material_id": material.id, "received_qty": 20, "unit_rate": 350}],
            },
        )
        self.assertEqual(receipt_response.status_code, 201, receipt_response.text)
        receipt_id = receipt_response.json()["id"]

        issue_response = self.client.post(
            "/api/v1/material-issues",
            headers=self.admin_headers(),
            json={
                "issue_no": "LEDGER-ISS-001",
                "project_id": self.project.id,
                "issue_date": "2026-03-26",
                "status": "issued",
                "items": [{"material_id": material.id, "issued_qty": 15, "unit_rate": 350}],
            },
        )
        self.assertEqual(issue_response.status_code, 201, issue_response.text)
        issue_id = issue_response.json()["id"]

        manual_adjustment = self.client.put(
            f"/api/v1/materials/{material.id}",
            headers=self.admin_headers(),
            json={"current_stock": 108},
        )
        self.assertEqual(manual_adjustment.status_code, 200, manual_adjustment.text)
        self.assertEqual(manual_adjustment.json()["current_stock"], 108.0)

        unauthorized = self.client.get(f"/api/v1/stock-ledger?material_id={material.id}")
        self.assertEqual(unauthorized.status_code, 401)

        list_response = self.client.get(
            f"/api/v1/stock-ledger?material_id={material.id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(list_response.status_code, 200, list_response.text)
        entries = list_response.json()["items"]
        self.assertEqual(len(entries), 3)

        by_type = {entry["transaction_type"]: entry for entry in entries}
        self.assertIn("material_receipt", by_type)
        self.assertIn("material_issue", by_type)
        self.assertIn("material_manual_adjustment", by_type)

        self.assertEqual(by_type["material_receipt"]["qty_in"], 20.0)
        self.assertEqual(by_type["material_receipt"]["qty_out"], 0.0)
        self.assertEqual(by_type["material_receipt"]["balance_after"], 120.0)
        self.assertEqual(by_type["material_receipt"]["reference_type"], "material_receipt")
        self.assertEqual(by_type["material_receipt"]["reference_id"], receipt_id)
        self.assertEqual(by_type["material_receipt"]["transaction_date"], "2026-03-26")

        self.assertEqual(by_type["material_issue"]["qty_in"], 0.0)
        self.assertEqual(by_type["material_issue"]["qty_out"], 15.0)
        self.assertEqual(by_type["material_issue"]["balance_after"], 105.0)
        self.assertEqual(by_type["material_issue"]["reference_type"], "material_issue")
        self.assertEqual(by_type["material_issue"]["reference_id"], issue_id)

        self.assertEqual(by_type["material_manual_adjustment"]["qty_in"], 3.0)
        self.assertEqual(by_type["material_manual_adjustment"]["qty_out"], 0.0)
        self.assertEqual(by_type["material_manual_adjustment"]["balance_after"], 108.0)
        self.assertEqual(by_type["material_manual_adjustment"]["reference_type"], "material")
        self.assertEqual(by_type["material_manual_adjustment"]["reference_id"], material.id)

        detail_response = self.client.get(
            f"/api/v1/stock-ledger/{entries[0]['id']}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(detail_response.status_code, 200, detail_response.text)
        self.assertEqual(detail_response.json()["id"], entries[0]["id"])

        issue_filter = self.client.get(
            f"/api/v1/stock-ledger?reference_type=material_issue&reference_id={issue_id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(issue_filter.status_code, 200, issue_filter.text)
        filtered_entries = issue_filter.json()["items"]
        self.assertEqual(len(filtered_entries), 1)
        self.assertEqual(filtered_entries[0]["transaction_type"], "material_issue")

    def test_material_stock_adjustment_and_labour_domain_scaffold_endpoints(self):
        material = Material(
            item_code="MSA-MAT-001",
            item_name="River Sand",
            category="Aggregate",
            unit="cum",
            reorder_level=20,
            default_rate=1500,
            current_stock=50,
            is_active=True,
            company_id=self.company.id,
            project_id=self.project.id,
        )
        self.db.add(material)
        self.db.commit()
        self.db.refresh(material)

        unauthorized_contractor = self.client.post(
            "/api/v1/labour-contractors/",
            json={"contractor_code": "LCTR-001", "contractor_name": "Alpha Gang"},
        )
        self.assertEqual(unauthorized_contractor.status_code, 401)

        contractor_create = self.client.post(
            "/api/v1/labour-contractors/",
            headers=self.admin_headers(),
            json={
                "contractor_code": "LCTR-001",
                "contractor_name": "Alpha Labour Supplier",
                "company_id": self.company.id,
                "gang_name": "Gang A",
                "phone": "9999999999",
            },
        )
        self.assertEqual(contractor_create.status_code, 201, contractor_create.text)
        labour_contractor_id = contractor_create.json()["id"]

        labour_create = self.client.post(
            "/api/v1/labour",
            headers=self.admin_headers(),
            json={
                "labour_code": "LBR-001",
                "full_name": "Ramesh Kumar",
                "company_id": self.company.id,
                "skill_type": "Mason",
                "default_wage_rate": 700,
                "unit": "day",
                "contractor_id": labour_contractor_id,
            },
        )
        self.assertEqual(labour_create.status_code, 201, labour_create.text)
        labour_id = labour_create.json()["id"]

        attendance_create = self.client.post(
            "/api/v1/labour-attendance",
            headers=self.admin_headers(),
            json={
                "muster_no": "MUSTER-001",
                "project_id": self.project.id,
                "attendance_date": "2026-03-26",
                "status": "submitted",
                "items": [
                    {
                        "labour_id": labour_id,
                        "present_days": 1,
                        "overtime_hours": 2,
                        "wage_rate": 700,
                    }
                ],
            },
        )
        self.assertEqual(attendance_create.status_code, 201, attendance_create.text)
        self.assertGreater(attendance_create.json()["total_wage"], 0)

        attendance_list = self.client.get(
            f"/api/v1/labour-attendance?project_id={self.project.id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(attendance_list.status_code, 200, attendance_list.text)
        self.assertEqual(len(attendance_list.json()["items"]), 1)

        productivity_create = self.client.post(
            "/api/v1/labour-productivities/",
            headers=self.admin_headers(),
            json={
                "project_id": self.project.id,
                "labour_id": labour_id,
                "activity_name": "Plastering",
                "quantity": 25.5,
                "unit": "sqm",
                "productivity_date": "2026-03-26",
            },
        )
        self.assertEqual(productivity_create.status_code, 201, productivity_create.text)

        bill_create = self.client.post(
            "/api/v1/labour-bills",
            headers=self.admin_headers(),
            json={
                "bill_no": "LBILL-001",
                "project_id": self.project.id,
                "contractor_id": labour_contractor_id,
                "period_start": "2026-03-01",
                "period_end": "2026-03-15",
                "status": "submitted",
                "gross_amount": 50000,
                "deductions": 3000,
            },
        )
        self.assertEqual(bill_create.status_code, 201, bill_create.text)
        labour_bill_id = bill_create.json()["id"]
        self.assertEqual(bill_create.json()["net_amount"], 47000.0)

        labour_bills_list = self.client.get(
            f"/api/v1/labour-bills?project_id={self.project.id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(labour_bills_list.status_code, 200, labour_bills_list.text)
        self.assertEqual(len(labour_bills_list.json()["items"]), 1)

        advance_create = self.client.post(
            "/api/v1/labour-advances/",
            headers=self.admin_headers(),
            json={
                "advance_no": "LADV-001",
                "project_id": self.project.id,
                "contractor_id": labour_contractor_id,
                "advance_date": "2026-03-10",
                "amount": 10000,
            },
        )
        self.assertEqual(advance_create.status_code, 201, advance_create.text)
        advance_id = advance_create.json()["id"]
        self.assertEqual(advance_create.json()["balance_amount"], 10000.0)

        recovery_create = self.client.post(
            f"/api/v1/labour-advances/{advance_id}/recoveries",
            headers=self.admin_headers(),
            json={
                "labour_bill_id": labour_bill_id,
                "recovery_date": "2026-03-15",
                "amount": 2500,
                "remarks": "Recovered in bill cycle",
            },
        )
        self.assertEqual(recovery_create.status_code, 200, recovery_create.text)
        self.assertEqual(recovery_create.json()["recovered_amount"], 2500.0)
        self.assertEqual(recovery_create.json()["balance_amount"], 7500.0)

        stock_adjustment = self.client.post(
            "/api/v1/material-stock-adjustments/",
            headers=self.admin_headers(),
            json={
                "adjustment_no": "MSA-001",
                "project_id": self.project.id,
                "adjustment_date": "2026-03-26",
                "status": "posted",
                "reason": "Physical count increase",
                "items": [{"material_id": material.id, "qty_change": 5, "unit_rate": 1550}],
            },
        )
        self.assertEqual(stock_adjustment.status_code, 201, stock_adjustment.text)
        self.assertEqual(stock_adjustment.json()["adjustment_no"], "MSA-001")

        stock_adjustment_alias_list = self.client.get(
            f"/api/v1/stock-adjustments/?project_id={self.project.id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(
            stock_adjustment_alias_list.status_code,
            200,
            stock_adjustment_alias_list.text,
        )
        self.assertEqual(len(stock_adjustment_alias_list.json()["items"]), 1)
        self.assertEqual(stock_adjustment_alias_list.json()["items"][0]["adjustment_no"], "MSA-001")

        material_after_adjustment = self.client.get(
            f"/api/v1/materials/{material.id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(material_after_adjustment.status_code, 200, material_after_adjustment.text)
        self.assertEqual(material_after_adjustment.json()["current_stock"], 55.0)

        stock_ledger_entries = self.client.get(
            f"/api/v1/stock-ledger?reference_type=material_stock_adjustment&material_id={material.id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(stock_ledger_entries.status_code, 200, stock_ledger_entries.text)
        self.assertEqual(len(stock_ledger_entries.json()["items"]), 1)
        self.assertEqual(
            stock_ledger_entries.json()["items"][0]["transaction_type"],
            "material_stock_adjustment",
        )

        labour_list = self.client.get(
            "/api/v1/labour?search=ramesh",
            headers=self.accountant_headers(),
        )
        self.assertEqual(labour_list.status_code, 200, labour_list.text)
        self.assertEqual(len(labour_list.json()["items"]), 1)

    def test_labour_business_rules_enforced_for_attendance_bills_and_advances(self):
        contractor_one = self.client.post(
            "/api/v1/labour-contractors/",
            headers=self.admin_headers(),
            json={"contractor_name": "Scope Contractor One", "company_id": self.company.id, "phone": "9000000001"},
        )
        self.assertEqual(contractor_one.status_code, 201, contractor_one.text)
        contractor_one_id = contractor_one.json()["id"]

        contractor_two = self.client.post(
            "/api/v1/labour-contractors/",
            headers=self.admin_headers(),
            json={"contractor_name": "Scope Contractor Two", "company_id": self.company.id, "phone": "9000000002"},
        )
        self.assertEqual(contractor_two.status_code, 201, contractor_two.text)
        contractor_two_id = contractor_two.json()["id"]

        labour_one = self.client.post(
            "/api/v1/labour",
            headers=self.admin_headers(),
            json={
                "labour_code": "LAB-RULE-001",
                "full_name": "Labour One",
                "trade": "Mason",
                "skill_level": "Skilled",
                "daily_rate": 900,
                "company_id": self.company.id,
                "contractor_id": contractor_one_id,
            },
        )
        self.assertEqual(labour_one.status_code, 201, labour_one.text)
        labour_one_id = labour_one.json()["id"]

        labour_two = self.client.post(
            "/api/v1/labour",
            headers=self.admin_headers(),
            json={
                "labour_code": "LAB-RULE-002",
                "full_name": "Labour Two",
                "trade": "Helper",
                "skill_level": "Semi-skilled",
                "daily_rate": 600,
                "company_id": self.company.id,
                "contractor_id": contractor_two_id,
            },
        )
        self.assertEqual(labour_two.status_code, 201, labour_two.text)
        labour_two_id = labour_two.json()["id"]

        labour_detail = self.client.get(
            f"/api/v1/labour/{labour_one_id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(labour_detail.status_code, 200, labour_detail.text)
        self.assertEqual(labour_detail.json()["id"], labour_one_id)

        contractor_scope_mismatch = self.client.post(
            "/api/v1/labour-attendance",
            headers=self.admin_headers(),
            json={
                "project_id": self.project.id,
                "contractor_id": contractor_one_id,
                "date": "2026-03-26",
                "status": "submitted",
                "items": [{"labour_id": labour_two_id, "attendance_status": "present"}],
            },
        )
        self.assertEqual(contractor_scope_mismatch.status_code, 400)

        attendance_create = self.client.post(
            "/api/v1/labour-attendance",
            headers=self.admin_headers(),
            json={
                "project_id": self.project.id,
                "contractor_id": contractor_one_id,
                "date": "2026-03-26",
                "status": "draft",
                "items": [
                    {
                        "labour_id": labour_one_id,
                        "attendance_status": "present",
                        "overtime_hours": 2,
                    }
                ],
            },
        )
        self.assertEqual(attendance_create.status_code, 201, attendance_create.text)
        attendance_id = attendance_create.json()["id"]
        self.assertEqual(attendance_create.json()["contractor_id"], contractor_one_id)

        attendance_submit = self.client.post(
            f"/api/v1/labour-attendance/{attendance_id}/submit",
            headers=self.admin_headers(),
            json={"remarks": "Submitted for approval"},
        )
        self.assertEqual(attendance_submit.status_code, 200, attendance_submit.text)
        self.assertEqual(attendance_submit.json()["status"], "submitted")

        duplicate_attendance = self.client.post(
            "/api/v1/labour-attendance",
            headers=self.admin_headers(),
            json={
                "project_id": self.project.id,
                "contractor_id": contractor_one_id,
                "date": "2026-03-26",
                "status": "submitted",
                "items": [{"labour_id": labour_one_id, "attendance_status": "present"}],
            },
        )
        self.assertEqual(duplicate_attendance.status_code, 400)

        attendance_approve = self.client.post(
            f"/api/v1/labour-attendance/{attendance_id}/approve",
            headers=self.admin_headers(),
            json={"remarks": "Approved attendance"},
        )
        self.assertEqual(attendance_approve.status_code, 200, attendance_approve.text)
        self.assertEqual(attendance_approve.json()["status"], "approved")

        invalid_approved_bill = self.client.post(
            "/api/v1/labour-bills",
            headers=self.admin_headers(),
            json={
                "bill_no": "LB-RULE-001",
                "project_id": self.project.id,
                "contractor_id": contractor_one_id,
                "period_start": "2026-03-01",
                "period_end": "2026-03-31",
                "status": "approved",
                "gross_amount": 5000,
                "deductions": 500,
            },
        )
        self.assertEqual(invalid_approved_bill.status_code, 400)

        bill_create = self.client.post(
            "/api/v1/labour-bills",
            headers=self.admin_headers(),
            json={
                "bill_no": "LB-RULE-002",
                "project_id": self.project.id,
                "contractor_id": contractor_one_id,
                "period_start": "2026-03-01",
                "period_end": "2026-03-31",
                "status": "submitted",
                "deductions": 100,
                "attendance_ids": [attendance_id],
            },
        )
        self.assertEqual(bill_create.status_code, 201, bill_create.text)
        bill_payload = bill_create.json()
        bill_id = bill_payload["id"]
        self.assertGreater(len(bill_payload["items"]), 0)
        self.assertEqual(bill_payload["net_payable"], bill_payload["net_amount"])

        bill_approve = self.client.post(
            f"/api/v1/labour-bills/{bill_id}/approve",
            headers=self.admin_headers(),
            json={"remarks": "Approved bill"},
        )
        self.assertEqual(bill_approve.status_code, 200, bill_approve.text)
        self.assertEqual(bill_approve.json()["status"], "approved")

        bill_paid = self.client.post(
            f"/api/v1/labour-bills/{bill_id}/mark-paid",
            headers=self.admin_headers(),
            json={"remarks": "Paid via transfer"},
        )
        self.assertEqual(bill_paid.status_code, 200, bill_paid.text)
        self.assertEqual(bill_paid.json()["status"], "paid")

        paid_immutable = self.client.put(
            f"/api/v1/labour-bills/{bill_id}",
            headers=self.admin_headers(),
            json={"remarks": "cannot edit paid bill"},
        )
        self.assertEqual(paid_immutable.status_code, 400)

        attendance_transition_logs = (
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "labour_attendance",
                AuditLog.entity_id == attendance_id,
                AuditLog.action == "status_transition",
            )
            .count()
        )
        self.assertGreaterEqual(attendance_transition_logs, 1)

        bill_transition_logs = (
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "labour_bill",
                AuditLog.entity_id == bill_id,
                AuditLog.action == "status_transition",
            )
            .count()
        )
        self.assertGreaterEqual(bill_transition_logs, 1)

        advance_create = self.client.post(
            "/api/v1/labour-advances/",
            headers=self.admin_headers(),
            json={
                "advance_no": "LADV-RULE-001",
                "project_id": self.project.id,
                "contractor_id": contractor_one_id,
                "advance_date": "2026-03-20",
                "amount": 1000,
            },
        )
        self.assertEqual(advance_create.status_code, 201, advance_create.text)
        advance_id = advance_create.json()["id"]

        over_recovery = self.client.post(
            f"/api/v1/labour-advances/{advance_id}/recoveries",
            headers=self.admin_headers(),
            json={
                "labour_bill_id": bill_id,
                "recovery_date": "2026-03-31",
                "amount": 1200,
            },
        )
        self.assertEqual(over_recovery.status_code, 400)

    def test_step2_material_domain_rules_block_invalid_transitions_and_negative_stock(self):
        material = Material(
            item_code="STEP2-MAT-001",
            item_name="River Sand",
            category="Aggregate",
            unit="cum",
            reorder_level=5,
            default_rate=1200,
            current_stock=10,
            is_active=True,
            company_id=self.company.id,
            project_id=self.project.id,
        )
        self.db.add(material)
        self.db.commit()
        self.db.refresh(material)

        requisition_create = self.client.post(
            "/api/v1/material-requisitions",
            headers=self.admin_headers(),
            json={
                "requisition_no": "STEP2-MR-001",
                "project_id": self.project.id,
                "items": [{"material_id": material.id, "requested_qty": 4}],
            },
        )
        self.assertEqual(requisition_create.status_code, 201, requisition_create.text)
        requisition_id = requisition_create.json()["id"]

        requisition_jump = self.client.put(
            f"/api/v1/material-requisitions/{requisition_id}",
            headers=self.admin_headers(),
            json={"status": "approved"},
        )
        self.assertEqual(requisition_jump.status_code, 400, requisition_jump.text)

        requisition_submit = self.client.post(
            f"/api/v1/material-requisitions/{requisition_id}/submit",
            headers=self.admin_headers(),
            json={"remarks": "Submitted for review"},
        )
        self.assertEqual(requisition_submit.status_code, 200, requisition_submit.text)

        requisition_approve = self.client.post(
            f"/api/v1/material-requisitions/{requisition_id}/approve",
            headers=self.admin_headers(),
            json={"remarks": "Approved for issue"},
        )
        self.assertEqual(requisition_approve.status_code, 200, requisition_approve.text)

        issue_create = self.client.post(
            "/api/v1/material-issues",
            headers=self.admin_headers(),
            json={
                "issue_no": "STEP2-ISS-001",
                "project_id": self.project.id,
                "issue_date": "2026-03-26",
                "status": "issued",
                "items": [{"material_id": material.id, "issued_qty": 9, "unit_rate": 1250}],
            },
        )
        self.assertEqual(issue_create.status_code, 201, issue_create.text)
        issue_id = issue_create.json()["id"]

        ledger_count_before = (
            self.db.query(InventoryTransaction)
            .filter(InventoryTransaction.reference_type == "material_issue")
            .count()
        )

        over_issue = self.client.post(
            "/api/v1/material-issues",
            headers=self.admin_headers(),
            json={
                "issue_no": "STEP2-ISS-002",
                "project_id": self.project.id,
                "issue_date": "2026-03-26",
                "status": "issued",
                "items": [{"material_id": material.id, "issued_qty": 2, "unit_rate": 1250}],
            },
        )
        self.assertEqual(over_issue.status_code, 400, over_issue.text)

        material_after_over_issue = self.client.get(
            f"/api/v1/materials/{material.id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(material_after_over_issue.status_code, 200, material_after_over_issue.text)
        self.assertEqual(material_after_over_issue.json()["current_stock"], 1.0)

        ledger_count_after = (
            self.db.query(InventoryTransaction)
            .filter(InventoryTransaction.reference_type == "material_issue")
            .count()
        )
        self.assertEqual(ledger_count_after, ledger_count_before)

        issue_reopen = self.client.put(
            f"/api/v1/material-issues/{issue_id}",
            headers=self.admin_headers(),
            json={"status": "draft"},
        )
        self.assertEqual(issue_reopen.status_code, 400, issue_reopen.text)

        receipt_create = self.client.post(
            "/api/v1/material-receipts",
            headers=self.admin_headers(),
            json={
                "receipt_no": "STEP2-RCV-001",
                "vendor_id": self.vendor.id,
                "project_id": self.project.id,
                "receipt_date": "2026-03-26",
                "status": "received",
                "items": [{"material_id": material.id, "received_qty": 4, "unit_rate": 1190}],
            },
        )
        self.assertEqual(receipt_create.status_code, 201, receipt_create.text)
        receipt_id = receipt_create.json()["id"]

        receipt_reopen = self.client.put(
            f"/api/v1/material-receipts/{receipt_id}",
            headers=self.admin_headers(),
            json={"status": "draft"},
        )
        self.assertEqual(receipt_reopen.status_code, 400, receipt_reopen.text)

        adjustment_create = self.client.post(
            "/api/v1/material-stock-adjustments/",
            headers=self.admin_headers(),
            json={
                "adjustment_no": "STEP2-ADJ-001",
                "project_id": self.project.id,
                "adjustment_date": "2026-03-26",
                "status": "posted",
                "reason": "Cycle count correction",
                "items": [{"material_id": material.id, "qty_change": 1, "unit_rate": 1200}],
            },
        )
        self.assertEqual(adjustment_create.status_code, 201, adjustment_create.text)
        adjustment_id = adjustment_create.json()["id"]

        adjustment_reopen = self.client.put(
            f"/api/v1/material-stock-adjustments/{adjustment_id}",
            headers=self.admin_headers(),
            json={"status": "draft"},
        )
        self.assertEqual(adjustment_reopen.status_code, 400, adjustment_reopen.text)

    def test_step2_labour_domain_rules_block_invalid_transitions_and_billed_attendance_edits(self):
        contractor = self.client.post(
            "/api/v1/labour-contractors/",
            headers=self.admin_headers(),
            json={"contractor_name": "Step2 Labour Contractor", "company_id": self.company.id, "phone": "9876543210"},
        )
        self.assertEqual(contractor.status_code, 201, contractor.text)
        contractor_id = contractor.json()["id"]

        labour = self.client.post(
            "/api/v1/labour",
            headers=self.admin_headers(),
            json={
                "labour_code": "STEP2-LAB-001",
                "full_name": "Step2 Worker",
                "trade": "Mason",
                "skill_level": "Skilled",
                "daily_rate": 850,
                "company_id": self.company.id,
                "contractor_id": contractor_id,
            },
        )
        self.assertEqual(labour.status_code, 201, labour.text)
        labour_id = labour.json()["id"]

        attendance_create = self.client.post(
            "/api/v1/labour-attendance",
            headers=self.admin_headers(),
            json={
                "project_id": self.project.id,
                "contractor_id": contractor_id,
                "date": "2026-03-26",
                "status": "draft",
                "items": [{"labour_id": labour_id, "attendance_status": "present"}],
            },
        )
        self.assertEqual(attendance_create.status_code, 201, attendance_create.text)
        attendance_id = attendance_create.json()["id"]

        direct_attendance_approve = self.client.post(
            f"/api/v1/labour-attendance/{attendance_id}/approve",
            headers=self.admin_headers(),
            json={"remarks": "Should fail"},
        )
        self.assertEqual(direct_attendance_approve.status_code, 400, direct_attendance_approve.text)

        attendance_submit = self.client.post(
            f"/api/v1/labour-attendance/{attendance_id}/submit",
            headers=self.admin_headers(),
            json={"remarks": "Submitted"},
        )
        self.assertEqual(attendance_submit.status_code, 200, attendance_submit.text)

        attendance_approve = self.client.post(
            f"/api/v1/labour-attendance/{attendance_id}/approve",
            headers=self.admin_headers(),
            json={"remarks": "Approved"},
        )
        self.assertEqual(attendance_approve.status_code, 200, attendance_approve.text)

        paid_on_create = self.client.post(
            "/api/v1/labour-bills",
            headers=self.admin_headers(),
            json={
                "bill_no": "STEP2-LB-001",
                "project_id": self.project.id,
                "contractor_id": contractor_id,
                "period_start": "2026-03-01",
                "period_end": "2026-03-31",
                "status": "paid",
                "attendance_ids": [attendance_id],
            },
        )
        self.assertEqual(paid_on_create.status_code, 400, paid_on_create.text)

        bill_create = self.client.post(
            "/api/v1/labour-bills",
            headers=self.admin_headers(),
            json={
                "bill_no": "STEP2-LB-002",
                "project_id": self.project.id,
                "contractor_id": contractor_id,
                "period_start": "2026-03-01",
                "period_end": "2026-03-31",
                "status": "submitted",
                "attendance_ids": [attendance_id],
            },
        )
        self.assertEqual(bill_create.status_code, 201, bill_create.text)
        bill_id = bill_create.json()["id"]

        direct_mark_paid = self.client.post(
            f"/api/v1/labour-bills/{bill_id}/mark-paid",
            headers=self.admin_headers(),
            json={"remarks": "Should fail"},
        )
        self.assertEqual(direct_mark_paid.status_code, 400, direct_mark_paid.text)

        bill_approve = self.client.post(
            f"/api/v1/labour-bills/{bill_id}/approve",
            headers=self.admin_headers(),
            json={"remarks": "Approved"},
        )
        self.assertEqual(bill_approve.status_code, 200, bill_approve.text)

        billed_attendance_edit = self.client.put(
            f"/api/v1/labour-attendance/{attendance_id}",
            headers=self.admin_headers(),
            json={"remarks": "Edit after billing should fail"},
        )
        self.assertEqual(billed_attendance_edit.status_code, 400, billed_attendance_edit.text)

    def test_material_build_order_sequence_records_audit_and_ledger(self):
        material_response = self.client.post(
            "/api/v1/materials",
            headers=self.admin_headers(),
            json={
                "item_code": "ORD-MAT-001",
                "item_name": "PPC Cement 43",
                "category": "Cement",
                "unit": "bag",
                "reorder_level": 50,
                "default_rate": 335,
                "current_stock": 50,
                "company_id": self.company.id,
                "project_id": self.project.id,
            },
        )
        self.assertEqual(material_response.status_code, 201, material_response.text)
        material_id = material_response.json()["id"]

        requisition_response = self.client.post(
            "/api/v1/material-requisitions",
            headers=self.admin_headers(),
            json={
                "requisition_no": "ORD-MR-001",
                "project_id": self.project.id,
                "items": [{"material_id": material_id, "requested_qty": 30}],
            },
        )
        self.assertEqual(requisition_response.status_code, 201, requisition_response.text)
        requisition_id = requisition_response.json()["id"]
        requisition_item_id = requisition_response.json()["items"][0]["id"]

        requisition_submit = self.client.post(
            f"/api/v1/material-requisitions/{requisition_id}/submit",
            headers=self.admin_headers(),
            json={"remarks": "Submitted in build-order flow"},
        )
        self.assertEqual(requisition_submit.status_code, 200, requisition_submit.text)
        self.assertEqual(requisition_submit.json()["status"], "submitted")

        requisition_approve = self.client.post(
            f"/api/v1/material-requisitions/{requisition_id}/approve",
            headers=self.admin_headers(),
            json={
                "remarks": "Approved in build-order flow",
                "items": [
                    {
                        "id": requisition_item_id,
                        "approved_qty": 30,
                        "issued_qty": 0,
                    }
                ],
            },
        )
        self.assertEqual(requisition_approve.status_code, 200, requisition_approve.text)
        self.assertEqual(requisition_approve.json()["status"], "approved")

        receipt_response = self.client.post(
            "/api/v1/material-receipts",
            headers=self.admin_headers(),
            json={
                "receipt_no": "ORD-RCV-001",
                "vendor_id": self.vendor.id,
                "project_id": self.project.id,
                "receipt_date": "2026-03-26",
                "status": "received",
                "items": [{"material_id": material_id, "received_qty": 40, "unit_rate": 340}],
            },
        )
        self.assertEqual(receipt_response.status_code, 201, receipt_response.text)
        receipt_id = receipt_response.json()["id"]

        issue_response = self.client.post(
            "/api/v1/material-issues",
            headers=self.admin_headers(),
            json={
                "issue_no": "ORD-ISS-001",
                "project_id": self.project.id,
                "issue_date": "2026-03-26",
                "status": "issued",
                "items": [{"material_id": material_id, "issued_qty": 25, "unit_rate": 342}],
            },
        )
        self.assertEqual(issue_response.status_code, 201, issue_response.text)
        issue_id = issue_response.json()["id"]

        adjustment_response = self.client.post(
            "/api/v1/material-stock-adjustments/",
            headers=self.admin_headers(),
            json={
                "adjustment_no": "ORD-MSA-001",
                "project_id": self.project.id,
                "adjustment_date": "2026-03-26",
                "status": "posted",
                "reason": "Physical verification excess",
                "items": [{"material_id": material_id, "qty_change": 5, "unit_rate": 338}],
            },
        )
        self.assertEqual(adjustment_response.status_code, 201, adjustment_response.text)
        adjustment_id = adjustment_response.json()["id"]

        ledger_response = self.client.get(
            f"/api/v1/stock-ledger?material_id={material_id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(ledger_response.status_code, 200, ledger_response.text)
        ledger_types = {entry["transaction_type"] for entry in ledger_response.json()["items"]}
        self.assertIn("material_receipt", ledger_types)
        self.assertIn("material_issue", ledger_types)
        self.assertIn("material_stock_adjustment", ledger_types)

        material_after_flow = self.client.get(
            f"/api/v1/materials/{material_id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(material_after_flow.status_code, 200, material_after_flow.text)
        self.assertEqual(material_after_flow.json()["current_stock"], 70.0)

        self.assertGreaterEqual(
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "material",
                AuditLog.entity_id == material_id,
                AuditLog.action == "create",
            )
            .count(),
            1,
        )
        self.assertGreaterEqual(
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "material_requisition",
                AuditLog.entity_id == requisition_id,
                AuditLog.action == "submit",
            )
            .count(),
            1,
        )
        self.assertGreaterEqual(
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "material_requisition",
                AuditLog.entity_id == requisition_id,
                AuditLog.action == "approve",
            )
            .count(),
            1,
        )
        self.assertGreaterEqual(
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "material_receipt",
                AuditLog.entity_id == receipt_id,
                AuditLog.action == "create",
            )
            .count(),
            1,
        )
        self.assertGreaterEqual(
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "material_issue",
                AuditLog.entity_id == issue_id,
                AuditLog.action == "create",
            )
            .count(),
            1,
        )
        self.assertGreaterEqual(
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "material_stock_adjustment",
                AuditLog.entity_id == adjustment_id,
                AuditLog.action == "create",
            )
            .count(),
            1,
        )

    def test_labour_build_order_sequence_records_audit(self):
        contractor_response = self.client.post(
            "/api/v1/labour-contractors/",
            headers=self.admin_headers(),
            json={
                "contractor_code": "ORD-LCTR-001",
                "contractor_name": "Order Flow Contractor",
                "company_id": self.company.id,
                "phone": "9000000011",
            },
        )
        self.assertEqual(contractor_response.status_code, 201, contractor_response.text)
        contractor_id = contractor_response.json()["id"]

        labour_response = self.client.post(
            "/api/v1/labour",
            headers=self.admin_headers(),
            json={
                "labour_code": "ORD-LAB-001",
                "full_name": "Order Flow Labour",
                "trade": "Mason",
                "skill_level": "Skilled",
                "daily_rate": 850,
                "company_id": self.company.id,
                "contractor_id": contractor_id,
            },
        )
        self.assertEqual(labour_response.status_code, 201, labour_response.text)
        labour_id = labour_response.json()["id"]

        attendance_response = self.client.post(
            "/api/v1/labour-attendance",
            headers=self.admin_headers(),
            json={
                "project_id": self.project.id,
                "contractor_id": contractor_id,
                "date": "2026-03-26",
                "status": "draft",
                "items": [{"labour_id": labour_id, "attendance_status": "present"}],
            },
        )
        self.assertEqual(attendance_response.status_code, 201, attendance_response.text)
        attendance_id = attendance_response.json()["id"]

        attendance_submit = self.client.post(
            f"/api/v1/labour-attendance/{attendance_id}/submit",
            headers=self.admin_headers(),
            json={"remarks": "Submitted in labour order flow"},
        )
        self.assertEqual(attendance_submit.status_code, 200, attendance_submit.text)
        self.assertEqual(attendance_submit.json()["status"], "submitted")

        attendance_approve = self.client.post(
            f"/api/v1/labour-attendance/{attendance_id}/approve",
            headers=self.admin_headers(),
            json={"remarks": "Approved in labour order flow"},
        )
        self.assertEqual(attendance_approve.status_code, 200, attendance_approve.text)
        self.assertEqual(attendance_approve.json()["status"], "approved")

        productivity_response = self.client.post(
            "/api/v1/labour-productivities/",
            headers=self.admin_headers(),
            json={
                "project_id": self.project.id,
                "labour_id": labour_id,
                "date": "2026-03-26",
                "trade": "Block Work",
                "quantity_done": 24,
                "labour_count": 2,
                "unit": "sqm",
            },
        )
        self.assertEqual(productivity_response.status_code, 201, productivity_response.text)
        productivity_id = productivity_response.json()["id"]

        bill_response = self.client.post(
            "/api/v1/labour-bills",
            headers=self.admin_headers(),
            json={
                "bill_no": "ORD-LB-001",
                "project_id": self.project.id,
                "contractor_id": contractor_id,
                "period_start": "2026-03-01",
                "period_end": "2026-03-31",
                "status": "submitted",
                "deductions": 50,
                "attendance_ids": [attendance_id],
            },
        )
        self.assertEqual(bill_response.status_code, 201, bill_response.text)
        bill_id = bill_response.json()["id"]

        bill_approve = self.client.post(
            f"/api/v1/labour-bills/{bill_id}/approve",
            headers=self.admin_headers(),
            json={"remarks": "Approved in labour order flow"},
        )
        self.assertEqual(bill_approve.status_code, 200, bill_approve.text)
        self.assertEqual(bill_approve.json()["status"], "approved")

        bill_paid = self.client.post(
            f"/api/v1/labour-bills/{bill_id}/mark-paid",
            headers=self.admin_headers(),
            json={"remarks": "Marked paid in labour order flow"},
        )
        self.assertEqual(bill_paid.status_code, 200, bill_paid.text)
        self.assertEqual(bill_paid.json()["status"], "paid")

        advance_response = self.client.post(
            "/api/v1/labour-advances/",
            headers=self.admin_headers(),
            json={
                "advance_no": "ORD-ADV-001",
                "project_id": self.project.id,
                "contractor_id": contractor_id,
                "advance_date": "2026-03-20",
                "amount": 500,
            },
        )
        self.assertEqual(advance_response.status_code, 201, advance_response.text)
        advance_id = advance_response.json()["id"]

        recovery_response = self.client.post(
            f"/api/v1/labour-advances/{advance_id}/recoveries",
            headers=self.admin_headers(),
            json={
                "labour_bill_id": bill_id,
                "recovery_date": "2026-03-31",
                "amount": 200,
                "remarks": "Order-flow recovery",
            },
        )
        self.assertEqual(recovery_response.status_code, 200, recovery_response.text)
        self.assertEqual(recovery_response.json()["balance_amount"], 300.0)

        self.assertGreaterEqual(
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "labour_contractor",
                AuditLog.entity_id == contractor_id,
                AuditLog.action == "create",
            )
            .count(),
            1,
        )
        self.assertGreaterEqual(
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "labour",
                AuditLog.entity_id == labour_id,
                AuditLog.action == "create",
            )
            .count(),
            1,
        )
        self.assertGreaterEqual(
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "labour_attendance",
                AuditLog.entity_id == attendance_id,
                AuditLog.action == "status_transition",
            )
            .count(),
            2,
        )
        self.assertGreaterEqual(
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "labour_productivity",
                AuditLog.entity_id == productivity_id,
                AuditLog.action == "create",
            )
            .count(),
            1,
        )
        self.assertGreaterEqual(
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "labour_bill",
                AuditLog.entity_id == bill_id,
                AuditLog.action == "status_transition",
            )
            .count(),
            2,
        )
        self.assertGreaterEqual(
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "labour_advance",
                AuditLog.entity_id == advance_id,
                AuditLog.action == "create",
            )
            .count(),
            1,
        )
        self.assertGreaterEqual(
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "labour_advance",
                AuditLog.entity_id == advance_id,
                AuditLog.action == "recovery",
            )
            .count(),
            1,
        )

    def test_project_contract_cross_links_enforced_for_material_and_labour(self):
        other_project = Project(
            company_id=self.company.id,
            name="Cross Link Project Two",
            code="API-PRJ-002",
            original_value=Decimal("50000.00"),
            revised_value=Decimal("50000.00"),
            status="active",
        )
        self.db.add(other_project)
        self.db.flush()
        other_contract = Contract(
            project_id=other_project.id,
            vendor_id=self.vendor.id,
            contract_no="API-CTR-002",
            title="Cross Link Contract Two",
            original_value=Decimal("50000.00"),
            revised_value=Decimal("50000.00"),
            retention_percentage=Decimal("5.00"),
            status="active",
        )
        self.db.add(other_contract)
        self.db.commit()
        self.db.refresh(other_project)
        self.db.refresh(other_contract)

        material_response = self.client.post(
            "/api/v1/materials",
            headers=self.admin_headers(),
            json={
                "item_code": "REL-MAT-001",
                "item_name": "Fly Ash",
                "category": "Cement",
                "unit": "bag",
                "reorder_level": 25,
                "default_rate": 310,
                "current_stock": 80,
                "company_id": self.company.id,
                "project_id": self.project.id,
            },
        )
        self.assertEqual(material_response.status_code, 201, material_response.text)
        material_id = material_response.json()["id"]

        requisition_ok = self.client.post(
            "/api/v1/material-requisitions",
            headers=self.admin_headers(),
            json={
                "requisition_no": "REL-MR-001",
                "project_id": self.project.id,
                "contract_id": self.contract.id,
                "items": [{"material_id": material_id, "requested_qty": 20}],
            },
        )
        self.assertEqual(requisition_ok.status_code, 201, requisition_ok.text)
        self.assertEqual(requisition_ok.json()["contract_id"], self.contract.id)

        requisition_bad_contract = self.client.post(
            "/api/v1/material-requisitions",
            headers=self.admin_headers(),
            json={
                "requisition_no": "REL-MR-002",
                "project_id": self.project.id,
                "contract_id": other_contract.id,
                "items": [{"material_id": material_id, "requested_qty": 10}],
            },
        )
        self.assertEqual(requisition_bad_contract.status_code, 400)

        requisition_filter = self.client.get(
            f"/api/v1/material-requisitions?contract_id={self.contract.id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(requisition_filter.status_code, 200, requisition_filter.text)
        self.assertEqual(len(requisition_filter.json()["items"]), 1)
        self.assertEqual(requisition_filter.json()["items"][0]["contract_id"], self.contract.id)

        issue_ok = self.client.post(
            "/api/v1/material-issues",
            headers=self.admin_headers(),
            json={
                "issue_no": "REL-ISS-001",
                "project_id": self.project.id,
                "contract_id": self.contract.id,
                "issue_date": "2026-03-26",
                "status": "issued",
                "items": [{"material_id": material_id, "issued_qty": 15, "unit_rate": 315}],
            },
        )
        self.assertEqual(issue_ok.status_code, 201, issue_ok.text)
        self.assertEqual(issue_ok.json()["contract_id"], self.contract.id)

        issue_bad_contract = self.client.post(
            "/api/v1/material-issues",
            headers=self.admin_headers(),
            json={
                "issue_no": "REL-ISS-002",
                "project_id": self.project.id,
                "contract_id": other_contract.id,
                "issue_date": "2026-03-26",
                "status": "issued",
                "items": [{"material_id": material_id, "issued_qty": 5, "unit_rate": 315}],
            },
        )
        self.assertEqual(issue_bad_contract.status_code, 400)

        issue_filter = self.client.get(
            f"/api/v1/material-issues?contract_id={self.contract.id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(issue_filter.status_code, 200, issue_filter.text)
        self.assertEqual(len(issue_filter.json()["items"]), 1)
        self.assertEqual(issue_filter.json()["items"][0]["contract_id"], self.contract.id)

        stock_summary_project = self.client.get(
            f"/api/v1/materials/stock-summary?group_by=project&project_id={self.project.id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(stock_summary_project.status_code, 200, stock_summary_project.text)
        self.assertEqual(stock_summary_project.json()[0]["scope_type"], "project")
        self.assertEqual(stock_summary_project.json()[0]["scope_id"], self.project.id)

        stock_summary_company = self.client.get(
            f"/api/v1/materials/stock-summary?group_by=company&company_id={self.company.id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(stock_summary_company.status_code, 200, stock_summary_company.text)
        self.assertEqual(stock_summary_company.json()[0]["scope_type"], "company")
        self.assertEqual(stock_summary_company.json()[0]["scope_id"], self.company.id)

        labour_contractor = self.client.post(
            "/api/v1/labour-contractors/",
            headers=self.admin_headers(),
            json={"contractor_code": "REL-LCTR-001", "contractor_name": "Cross Link Gang", "company_id": self.company.id},
        )
        self.assertEqual(labour_contractor.status_code, 201, labour_contractor.text)
        labour_contractor_id = labour_contractor.json()["id"]

        labour = self.client.post(
            "/api/v1/labour",
            headers=self.admin_headers(),
            json={
                "labour_code": "REL-LAB-001",
                "full_name": "Cross Link Labour",
                "trade": "Mason",
                "skill_level": "Skilled",
                "daily_rate": 900,
                "company_id": self.company.id,
                "contractor_id": labour_contractor_id,
            },
        )
        self.assertEqual(labour.status_code, 201, labour.text)
        labour_id = labour.json()["id"]

        attendance = self.client.post(
            "/api/v1/labour-attendance",
            headers=self.admin_headers(),
            json={
                "project_id": self.project.id,
                "contractor_id": labour_contractor_id,
                "date": "2026-03-26",
                "status": "draft",
                "items": [{"labour_id": labour_id, "attendance_status": "present"}],
            },
        )
        self.assertEqual(attendance.status_code, 201, attendance.text)
        attendance_id = attendance.json()["id"]

        attendance_submit = self.client.post(
            f"/api/v1/labour-attendance/{attendance_id}/submit",
            headers=self.admin_headers(),
        )
        self.assertEqual(attendance_submit.status_code, 200, attendance_submit.text)

        attendance_approve = self.client.post(
            f"/api/v1/labour-attendance/{attendance_id}/approve",
            headers=self.admin_headers(),
        )
        self.assertEqual(attendance_approve.status_code, 200, attendance_approve.text)

        labour_bill_ok = self.client.post(
            "/api/v1/labour-bills",
            headers=self.admin_headers(),
            json={
                "bill_no": "REL-LB-001",
                "project_id": self.project.id,
                "contract_id": self.contract.id,
                "contractor_id": labour_contractor_id,
                "period_start": "2026-03-01",
                "period_end": "2026-03-31",
                "status": "submitted",
                "attendance_ids": [attendance_id],
            },
        )
        self.assertEqual(labour_bill_ok.status_code, 201, labour_bill_ok.text)
        bill_id = labour_bill_ok.json()["id"]
        self.assertEqual(labour_bill_ok.json()["contract_id"], self.contract.id)

        labour_bill_bad_contract = self.client.post(
            "/api/v1/labour-bills",
            headers=self.admin_headers(),
            json={
                "bill_no": "REL-LB-002",
                "project_id": self.project.id,
                "contract_id": other_contract.id,
                "contractor_id": labour_contractor_id,
                "period_start": "2026-03-01",
                "period_end": "2026-03-31",
                "status": "submitted",
                "attendance_ids": [attendance_id],
            },
        )
        self.assertEqual(labour_bill_bad_contract.status_code, 400)

        labour_bill_filter = self.client.get(
            f"/api/v1/labour-bills?contract_id={self.contract.id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(labour_bill_filter.status_code, 200, labour_bill_filter.text)
        self.assertEqual(len(labour_bill_filter.json()["items"]), 1)
        self.assertEqual(labour_bill_filter.json()["items"][0]["id"], bill_id)
        self.assertEqual(labour_bill_filter.json()["items"][0]["contract_id"], self.contract.id)

    def test_ra_bill_workflow_endpoints_follow_api_transitions(self):
        self.seed_boq_and_work_done()
        headers = self.admin_headers()

        bill_response = self.client.post(
            "/api/v1/ra-bills/",
            headers=headers,
            json={
                "contract_id": self.contract.id,
                "bill_date": "2026-03-24",
                "remarks": "API workflow bill",
            },
        )
        self.assertEqual(bill_response.status_code, 201, bill_response.text)
        bill_id = bill_response.json()["id"]

        generate_response = self.client.post(
            f"/api/v1/ra-bills/{bill_id}/generate",
            headers=headers,
        )
        self.assertEqual(generate_response.status_code, 200, generate_response.text)
        self.assertGreater(len(generate_response.json()["items"]), 0)

        submit_response = self.client.post(
            f"/api/v1/ra-bills/{bill_id}/submit",
            headers=headers,
        )
        self.assertEqual(submit_response.status_code, 200, submit_response.text)
        self.assertEqual(submit_response.json()["status"], "submitted")

        reject_without_remarks = self.client.post(
            f"/api/v1/ra-bills/{bill_id}/reject",
            headers=headers,
            json={},
        )
        self.assertEqual(reject_without_remarks.status_code, 400)

        verify_response = self.client.post(
            f"/api/v1/ra-bills/{bill_id}/verify",
            headers=headers,
        )
        self.assertEqual(verify_response.status_code, 200, verify_response.text)
        self.assertEqual(verify_response.json()["status"], "verified")

        approve_response = self.client.post(
            f"/api/v1/ra-bills/{bill_id}/approve",
            headers=headers,
        )
        self.assertEqual(approve_response.status_code, 200, approve_response.text)
        self.assertEqual(approve_response.json()["status"], "approved")

        regenerate_response = self.client.post(
            f"/api/v1/ra-bills/{bill_id}/generate",
            headers=headers,
        )
        self.assertEqual(regenerate_response.status_code, 400)

    def test_payments_documents_audit_and_dashboard_endpoints_work(self):
        headers = self.admin_headers()
        bill = self.seed_approved_bill(bill_no=10, net_payable="1200.00")

        payment_create = self.client.post(
            "/api/v1/payments/",
            headers=headers,
            json={
                "contract_id": self.contract.id,
                "payment_date": "2026-03-24",
                "amount": 1200,
                "remarks": "API payment",
            },
        )
        self.assertEqual(payment_create.status_code, 201, payment_create.text)
        payment_id = payment_create.json()["id"]

        self.assertEqual(
            self.client.post(f"/api/v1/payments/{payment_id}/approve", headers=headers).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(f"/api/v1/payments/{payment_id}/release", headers=headers).status_code,
            200,
        )
        allocation_response = self.client.post(
            f"/api/v1/payments/{payment_id}/allocate",
            headers=headers,
            json=[{"ra_bill_id": bill.id, "amount": 600}],
        )
        self.assertEqual(allocation_response.status_code, 200, allocation_response.text)

        bill_response = self.client.get(f"/api/v1/ra-bills/{bill.id}", headers=headers)
        self.assertEqual(bill_response.status_code, 200)
        self.assertEqual(bill_response.json()["status"], "partially_paid")

        document_create = self.client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={
                "entity_type": "payment",
                "entity_id": payment_id,
                "title": "Payment Advice",
            },
            files={"file": ("payment advice.pdf", b"payment advice v1", "application/pdf")},
        )
        self.assertEqual(document_create.status_code, 201, document_create.text)
        document_id = document_create.json()["id"]
        document_payload = document_create.json()
        self.assertEqual(document_payload["latest_file_name"], "payment_advice.pdf")
        self.assertNotEqual(document_payload["latest_file_path"], "payment advice.pdf")
        self.assertRegex(
            document_payload["latest_file_path"],
            r"^documents/payment/\d+/[0-9a-f-]{36}/v1/\d{14}_[0-9a-f]{32}\.pdf$",
        )
        stored_path = Path(self.upload_dir.name) / Path(document_payload["latest_file_path"])
        self.assertTrue(stored_path.exists())
        self.assertEqual(stored_path.read_bytes(), b"payment advice v1")

        version_response = self.client.post(
            f"/api/v1/documents/{document_id}/versions/upload",
            headers=headers,
            data={
                "remarks": "Updated attachment",
            },
            files={"file": ("payment advice v2.pdf", b"payment advice v2", "application/pdf")},
        )
        self.assertEqual(version_response.status_code, 200, version_response.text)
        self.assertEqual(version_response.json()["current_version_number"], 2)
        self.assertEqual(len(version_response.json()["versions"]), 2)
        self.assertEqual(version_response.json()["latest_file_name"], "payment_advice_v2.pdf")
        self.assertRegex(
            version_response.json()["latest_file_path"],
            rf"^documents/payment/{payment_id}/{document_payload['storage_key']}/v2/\d{{14}}_[0-9a-f]{{32}}\.pdf$",
        )
        versioned_path = Path(self.upload_dir.name) / Path(version_response.json()["latest_file_path"])
        self.assertTrue(versioned_path.exists())
        self.assertEqual(versioned_path.read_bytes(), b"payment advice v2")

        document_audit_create = self.client.get(
            f"/api/v1/audit-logs/?entity_type=document&entity_id={document_id}&action=create",
            headers=self.accountant_headers(),
        )
        self.assertEqual(document_audit_create.status_code, 200, document_audit_create.text)
        create_audit_payload = document_audit_create.json()["items"]
        self.assertEqual(len(create_audit_payload), 1)
        self.assertEqual(create_audit_payload[0]["after_data"]["document"]["id"], document_id)
        self.assertEqual(
            create_audit_payload[0]["after_data"]["latest_version"]["version_number"],
            1,
        )

        document_audit_version = self.client.get(
            f"/api/v1/audit-logs/?entity_type=document&entity_id={document_id}&action=version_upload",
            headers=self.accountant_headers(),
        )
        self.assertEqual(document_audit_version.status_code, 200, document_audit_version.text)
        version_audit_payload = document_audit_version.json()["items"]
        self.assertEqual(len(version_audit_payload), 1)
        self.assertEqual(
            version_audit_payload[0]["before_data"]["latest_version"]["version_number"],
            1,
        )
        self.assertEqual(
            version_audit_payload[0]["after_data"]["latest_version"]["version_number"],
            2,
        )

        download_unauthorized = self.client.get(f"/api/v1/documents/{document_id}/download")
        self.assertEqual(download_unauthorized.status_code, 401)

        download_response = self.client.get(
            f"/api/v1/documents/{document_id}/download",
            headers=headers,
        )
        self.assertEqual(download_response.status_code, 200, download_response.text)
        self.assertEqual(download_response.content, b"payment advice v2")
        self.assertEqual(
            download_response.headers["content-disposition"],
            'attachment; filename="payment_advice_v2.pdf"',
        )
        self.assertEqual(download_response.headers["content-type"], "application/pdf")

        bad_link = self.client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={
                "entity_type": "payment",
                "entity_id": 999999,
                "title": "Bad Link",
            },
            files={"file": ("bad.pdf", b"bad data", "application/pdf")},
        )
        self.assertEqual(bad_link.status_code, 404)

        bad_type = self.client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={
                "entity_type": "payment",
                "entity_id": payment_id,
                "title": "Bad Type",
            },
            files={"file": ("bad-type.pdf", b"bad", "application/x-msdownload")},
        )
        self.assertEqual(bad_type.status_code, 400)
        self.assertIn("Unsupported file type", bad_type.text)

        audit_unauthorized = self.client.get("/api/v1/audit-logs/")
        self.assertEqual(audit_unauthorized.status_code, 401)

        audit_forbidden = self.client.get(
            "/api/v1/audit-logs/",
            headers=self.contractor_headers(),
        )
        self.assertEqual(audit_forbidden.status_code, 403)

        audit_success = self.client.get(
            f"/api/v1/audit-logs/?entity_type=payment&entity_id={payment_id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(audit_success.status_code, 200, audit_success.text)
        self.assertGreaterEqual(len(audit_success.json()["items"]), 3)

        dashboard_summary = self.client.get("/api/v1/dashboard/summary", headers=headers)
        dashboard_finance = self.client.get("/api/v1/dashboard/finance", headers=headers)
        dashboard_project = self.client.get(
            f"/api/v1/dashboard/projects/{self.project.id}",
            headers=headers,
        )
        dashboard_contract = self.client.get(
            f"/api/v1/dashboard/contracts/{self.contract.id}",
            headers=headers,
        )
        self.assertEqual(dashboard_summary.status_code, 200)
        self.assertEqual(dashboard_finance.status_code, 200)
        self.assertEqual(dashboard_project.status_code, 200)
        self.assertEqual(dashboard_contract.status_code, 200)
        summary_payload = dashboard_summary.json()
        finance_payload = dashboard_finance.json()
        project_payload = dashboard_project.json()
        contract_payload = dashboard_contract.json()
        self.assertIn("total_billed_amount", summary_payload)
        self.assertIn("total_paid_amount", summary_payload)
        self.assertIn("outstanding_payable", summary_payload)
        self.assertIn("secured_advance_outstanding", summary_payload)
        self.assertIn("pending_ra_bills_by_status", summary_payload)
        self.assertIn("pending_payments_by_status", summary_payload)
        self.assertIn("project_wise_finance_summary", finance_payload)
        self.assertIn("contract_wise_finance_summary", finance_payload)
        self.assertIn("contract_wise_finance_summary", project_payload)
        self.assertIn("outstanding_payable", contract_payload)

    def test_audit_logs_endpoints_support_filters_and_detail_read(self):
        headers = self.admin_headers()

        payment_create = self.client.post(
            "/api/v1/payments/",
            headers=headers,
            json={
                "contract_id": self.contract.id,
                "payment_date": "2026-03-25",
                "amount": 750,
                "remarks": "Audit filter payment",
            },
        )
        self.assertEqual(payment_create.status_code, 201, payment_create.text)
        payment_id = payment_create.json()["id"]

        filtered_logs = self.client.get(
            (
                "/api/v1/audit-logs/"
                f"?entity_type=payment&entity_id={payment_id}&action=create"
                f"&performed_by={self.admin_user.id}"
            ),
            headers=self.accountant_headers(),
        )
        self.assertEqual(filtered_logs.status_code, 200, filtered_logs.text)
        payload = filtered_logs.json()["items"]
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["entity_type"], "payment")
        self.assertEqual(payload[0]["entity_id"], payment_id)
        self.assertEqual(payload[0]["action"], "create")
        self.assertEqual(payload[0]["performed_by"], self.admin_user.id)
        performed_date = payload[0]["performed_at"][:10]

        ranged_logs = self.client.get(
            (
                "/api/v1/audit-logs/"
                f"?entity_type=payment&entity_id={payment_id}&action=create"
                f"&performed_by={self.admin_user.id}&date_from={performed_date}&date_to={performed_date}"
            ),
            headers=self.accountant_headers(),
        )
        self.assertEqual(ranged_logs.status_code, 200, ranged_logs.text)
        self.assertEqual(len(ranged_logs.json()["items"]), 1)

        detail = self.client.get(
            f"/api/v1/audit-logs/{payload[0]['id']}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["id"], payload[0]["id"])
        self.assertEqual(detail.json()["after_data"]["status"], "draft")

        bad_range = self.client.get(
            "/api/v1/audit-logs/?date_from=2026-03-26&date_to=2026-03-25",
            headers=self.accountant_headers(),
        )
        self.assertEqual(bad_range.status_code, 400)

    def test_document_upload_rejects_unauthorized_bad_extension_and_oversize(self):
        payment = Payment(
            contract_id=self.contract.id,
            payment_date=date(2026, 3, 24),
            amount=Decimal("250.00"),
            status="draft",
        )
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)

        unauthorized_upload = self.client.post(
            "/api/v1/documents/upload",
            data={
                "entity_type": "payment",
                "entity_id": payment.id,
                "title": "No Auth Upload",
            },
            files={"file": ("payment.pdf", b"no auth", "application/pdf")},
        )
        self.assertEqual(unauthorized_upload.status_code, 401)
        self.assertIn("X-Request-ID", unauthorized_upload.headers)
        self.assertEqual(
            unauthorized_upload.json()["error"]["type"],
            "authentication_error",
        )

        bad_extension = self.client.post(
            "/api/v1/documents/upload",
            headers=self.admin_headers(),
            data={
                "entity_type": "payment",
                "entity_id": payment.id,
                "title": "Bad Extension",
            },
            files={"file": ("payload.exe", b"bad extension", "application/pdf")},
        )
        self.assertEqual(bad_extension.status_code, 400)
        self.assertIn("Unsupported file extension", bad_extension.text)
        self.assertIn("X-Request-ID", bad_extension.headers)
        self.assertEqual(bad_extension.json()["error"]["type"], "validation_error")

        with patch.object(settings, "MAX_UPLOAD_SIZE_MB", 1):
            oversize = self.client.post(
                "/api/v1/documents/upload",
                headers=self.admin_headers(),
                data={
                    "entity_type": "payment",
                    "entity_id": payment.id,
                    "title": "Too Large",
                },
                files={
                    "file": (
                        "oversize.pdf",
                        b"x" * (1024 * 1024 + 1),
                        "application/pdf",
                    )
                },
            )
        self.assertEqual(oversize.status_code, 413)
        self.assertIn("File size exceeds", oversize.text)
        self.assertIn("X-Request-ID", oversize.headers)
        self.assertEqual(oversize.json()["error"]["type"], "validation_error")

    def test_vendor_and_company_quotations_work_through_documents_api(self):
        headers = self.admin_headers()

        vendor_upload = self.client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={
                "entity_type": "vendor",
                "entity_id": self.vendor.id,
                "title": "Marco Vendor Quotation",
                "document_type": "quotation",
                "remarks": "Initial vendor quote",
            },
            files={"file": ("vendor quotation.pdf", b"vendor quote v1", "application/pdf")},
        )
        self.assertEqual(vendor_upload.status_code, 201, vendor_upload.text)
        vendor_document = vendor_upload.json()
        self.assertEqual(vendor_document["entity_type"], "vendor")
        self.assertEqual(vendor_document["document_type"], "quotation")
        self.assertRegex(
            vendor_document["latest_file_path"],
            r"^documents/vendor/\d+/[0-9a-f-]{36}/v1/\d{14}_[0-9a-f]{32}\.pdf$",
        )

        vendor_version = self.client.post(
            f"/api/v1/documents/{vendor_document['id']}/versions/upload",
            headers=headers,
            data={"remarks": "Revision A"},
            files={"file": ("vendor quotation rev-a.pdf", b"vendor quote v2", "application/pdf")},
        )
        self.assertEqual(vendor_version.status_code, 200, vendor_version.text)
        self.assertEqual(vendor_version.json()["current_version_number"], 2)
        self.assertEqual(vendor_version.json()["versions"][-1]["remarks"], "Revision A")

        company_upload = self.client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={
                "entity_type": "company",
                "entity_id": self.company.id,
                "title": "Marco Company Quotation",
                "document_type": "quotation",
                "remarks": "Company-level pricing note",
            },
            files={"file": ("company quotation.pdf", b"company quote v1", "application/pdf")},
        )
        self.assertEqual(company_upload.status_code, 201, company_upload.text)
        company_document = company_upload.json()
        self.assertEqual(company_document["entity_type"], "company")
        self.assertEqual(company_document["document_type"], "quotation")
        self.assertRegex(
            company_document["latest_file_path"],
            r"^documents/company/\d+/[0-9a-f-]{36}/v1/\d{14}_[0-9a-f]{32}\.pdf$",
        )

        invalid_vendor = self.client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={
                "entity_type": "vendor",
                "entity_id": 999999,
                "title": "Missing Vendor Quote",
                "document_type": "quotation",
            },
            files={"file": ("missing-vendor.pdf", b"missing", "application/pdf")},
        )
        self.assertEqual(invalid_vendor.status_code, 404)

        invalid_company = self.client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={
                "entity_type": "company",
                "entity_id": 999999,
                "title": "Missing Company Quote",
                "document_type": "quotation",
            },
            files={"file": ("missing-company.pdf", b"missing", "application/pdf")},
        )
        self.assertEqual(invalid_company.status_code, 404)

    def test_labour_workflow_documents_upload_through_api(self):
        headers = self.admin_headers()

        contractor = LabourContractor(
            company_id=self.company.id,
            contractor_code="LCTR-DOC-001",
            contractor_name="Departmental LBR",
            contact_person="Muster Supervisor",
            phone="9999999999",
        )
        self.db.add(contractor)
        self.db.flush()

        attendance = LabourAttendance(
            muster_no="MST-DOC-001",
            project_id=self.project.id,
            contractor_id=contractor.id,
            date=date(2026, 4, 3),
            attendance_date=date(2026, 4, 3),
            marked_by=self.admin_user.id,
            status="approved",
            total_wage=Decimal("12000.00"),
        )
        bill = LabourBill(
            bill_no="LB-DOC-001",
            project_id=self.project.id,
            contract_id=self.contract.id,
            contractor_id=contractor.id,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 3),
            status="approved",
            gross_amount=Decimal("12000.00"),
            deductions=Decimal("0.00"),
            net_amount=Decimal("12000.00"),
            net_payable=Decimal("12000.00"),
        )
        advance = LabourAdvance(
            advance_no="ADV-DOC-001",
            project_id=self.project.id,
            contractor_id=contractor.id,
            advance_date=date(2026, 4, 3),
            amount=Decimal("3000.00"),
            recovered_amount=Decimal("0.00"),
            balance_amount=Decimal("3000.00"),
            status="active",
        )
        self.db.add_all([attendance, bill, advance])
        self.db.commit()
        self.db.refresh(attendance)
        self.db.refresh(bill)
        self.db.refresh(advance)

        attendance_upload = self.client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={
                "entity_type": "labour_attendance",
                "entity_id": attendance.id,
                "title": "April Muster Sheet",
                "document_type": "attendance_sheet",
            },
            files={"file": ("attendance-sheet.pdf", b"attendance", "application/pdf")},
        )
        self.assertEqual(attendance_upload.status_code, 201, attendance_upload.text)
        self.assertEqual(attendance_upload.json()["entity_type"], "labour_attendance")

        bill_upload = self.client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={
                "entity_type": "labour_bill",
                "entity_id": bill.id,
                "title": "April Labour Bill Sheet",
                "document_type": "labour_bill_sheet",
            },
            files={"file": ("labour-bill-sheet.pdf", b"bill", "application/pdf")},
        )
        self.assertEqual(bill_upload.status_code, 201, bill_upload.text)
        bill_document = bill_upload.json()
        self.assertEqual(bill_document["entity_type"], "labour_bill")
        self.assertRegex(
            bill_document["latest_file_path"],
            r"^documents/labour_bill/\d+/[0-9a-f-]{36}/v1/\d{14}_[0-9a-f]{32}\.pdf$",
        )

        bill_version = self.client.post(
            f"/api/v1/documents/{bill_document['id']}/versions/upload",
            headers=headers,
            data={"remarks": "Revision A"},
            files={"file": ("labour-bill-sheet-rev-a.pdf", b"bill-v2", "application/pdf")},
        )
        self.assertEqual(bill_version.status_code, 200, bill_version.text)
        self.assertEqual(bill_version.json()["current_version_number"], 2)

        advance_upload = self.client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={
                "entity_type": "labour_advance",
                "entity_id": advance.id,
                "title": "Food Advance Register",
                "document_type": "labour_advance_sheet",
            },
            files={"file": ("food-advance.pdf", b"advance", "application/pdf")},
        )
        self.assertEqual(advance_upload.status_code, 201, advance_upload.text)
        self.assertEqual(advance_upload.json()["entity_type"], "labour_advance")

        missing_attendance = self.client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={
                "entity_type": "labour_attendance",
                "entity_id": 999999,
                "title": "Missing Attendance",
                "document_type": "attendance_sheet",
            },
            files={"file": ("missing-attendance.pdf", b"missing", "application/pdf")},
        )
        self.assertEqual(missing_attendance.status_code, 404)

        quotation_list = self.client.get(
            "/api/v1/documents/?document_type=quotation",
            headers=headers,
        )
        self.assertEqual(quotation_list.status_code, 200, quotation_list.text)
        quotation_items = quotation_list.json()["items"]
        self.assertEqual(len(quotation_items), 2)
        self.assertEqual(
            {item["entity_type"] for item in quotation_items},
            {"vendor", "company"},
        )

        vendor_only = self.client.get(
            "/api/v1/documents/?document_type=quotation&entity_type=vendor",
            headers=headers,
        )
        self.assertEqual(vendor_only.status_code, 200, vendor_only.text)
        self.assertEqual(vendor_only.json()["total"], 1)
        self.assertEqual(vendor_only.json()["items"][0]["title"], "Marco Vendor Quotation")

        export_response = self.client.get(
            "/api/v1/documents/export?document_type=quotation&entity_type=company",
            headers=headers,
        )
        self.assertEqual(export_response.status_code, 200, export_response.text)
        self.assertIn("Marco Company Quotation", export_response.text)

    def test_step3_user_delete_soft_deactivates_and_blocks_login(self):
        removable_user = User(
            full_name="Removable Viewer",
            email="removable-viewer@example.com",
            hashed_password=hash_password("StrongPass123"),
            role="viewer",
            is_active=True,
        )
        self.db.add(removable_user)
        self.db.commit()
        self.db.refresh(removable_user)

        forbidden_delete = self.client.delete(
            f"/api/v1/users/{removable_user.id}",
            headers=self.accountant_headers(),
        )
        self.assertEqual(forbidden_delete.status_code, 403, forbidden_delete.text)

        delete_response = self.client.delete(
            f"/api/v1/users/{removable_user.id}",
            headers=self.admin_headers(),
        )
        self.assertEqual(delete_response.status_code, 204, delete_response.text)

        self.db.refresh(removable_user)
        self.assertTrue(self.db.get(User, removable_user.id) is not None)
        self.assertFalse(removable_user.is_active)

        login_after_delete = self.client.post(
            "/api/v1/auth/login",
            json={"email": removable_user.email, "password": "StrongPass123"},
        )
        self.assertEqual(login_after_delete.status_code, 403, login_after_delete.text)

        self_delete = self.client.delete(
            f"/api/v1/users/{self.admin_user.id}",
            headers=self.admin_headers(),
        )
        self.assertEqual(self_delete.status_code, 400, self_delete.text)

    def test_step3_vendor_and_project_delete_are_guarded_when_in_use(self):
        vendor_forbidden = self.client.delete(
            f"/api/v1/vendors/{self.vendor.id}",
            headers=self.contractor_headers(),
        )
        self.assertEqual(vendor_forbidden.status_code, 403, vendor_forbidden.text)

        vendor_blocked = self.client.delete(
            f"/api/v1/vendors/{self.vendor.id}",
            headers=self.admin_headers(),
        )
        self.assertEqual(vendor_blocked.status_code, 400, vendor_blocked.text)
        self.assertIn("contracts", vendor_blocked.text)

        project_blocked = self.client.delete(
            f"/api/v1/projects/{self.project.id}",
            headers=self.admin_headers(),
        )
        self.assertEqual(project_blocked.status_code, 400, project_blocked.text)
        self.assertIn("contracts", project_blocked.text)

        unused_vendor = self.client.post(
            "/api/v1/vendors/",
            headers=self.admin_headers(),
            json={
                "name": "Unused API Vendor",
                "code": "API-VEN-UNUSED",
                "vendor_type": "supplier",
                "company_id": self.company.id,
            },
        )
        self.assertEqual(unused_vendor.status_code, 201, unused_vendor.text)
        unused_vendor_id = unused_vendor.json()["id"]

        delete_unused_vendor = self.client.delete(
            f"/api/v1/vendors/{unused_vendor_id}",
            headers=self.admin_headers(),
        )
        self.assertEqual(delete_unused_vendor.status_code, 204, delete_unused_vendor.text)

        fetch_deleted_vendor = self.client.get(
            f"/api/v1/vendors/{unused_vendor_id}",
            headers=self.admin_headers(),
        )
        self.assertEqual(fetch_deleted_vendor.status_code, 404, fetch_deleted_vendor.text)

        unused_project = self.client.post(
            "/api/v1/projects/",
            headers=self.admin_headers(),
            json={
                "company_id": self.company.id,
                "name": "Unused API Project",
                "code": "API-PRJ-UNUSED",
                "original_value": 10000,
                "revised_value": 10000,
                "status": "active",
            },
        )
        self.assertEqual(unused_project.status_code, 201, unused_project.text)
        unused_project_id = unused_project.json()["id"]

        delete_unused_project = self.client.delete(
            f"/api/v1/projects/{unused_project_id}",
            headers=self.admin_headers(),
        )
        self.assertEqual(delete_unused_project.status_code, 204, delete_unused_project.text)

        fetch_deleted_project = self.client.get(
            f"/api/v1/projects/{unused_project_id}",
            headers=self.admin_headers(),
        )
        self.assertEqual(fetch_deleted_project.status_code, 404, fetch_deleted_project.text)


if __name__ == "__main__":
    unittest.main()
