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
from app.models.boq import BOQItem
from app.models.company import Company
from app.models.contract import Contract
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
        create_audit_payload = document_audit_create.json()
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
        version_audit_payload = document_audit_version.json()
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
        self.assertGreaterEqual(len(audit_success.json()), 3)

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
        payload = filtered_logs.json()
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
        self.assertEqual(len(ranged_logs.json()), 1)

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


if __name__ == "__main__":
    unittest.main()
