"""Tests for document upload rollback safety."""

import io
import tempfile
from pathlib import Path
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from fastapi import UploadFile

from app.core.config import settings
from app.models.labour_advance import LabourAdvance
from app.models.labour_attendance import LabourAttendance
from app.models.labour_bill import LabourBill
from app.services.document_service import (
    add_document_version_from_upload,
    create_document_from_upload,
)
from app.tests.helpers import FinanceDbTestCase, OperationsDbTestCase


class DocumentUploadRollbackTests(FinanceDbTestCase):
    def setUp(self):
        super().setUp()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_patch = patch.object(settings, "LOCAL_STORAGE_ROOT", self.temp_dir.name)
        self.storage_patch.start()

    def tearDown(self):
        self.storage_patch.stop()
        self.temp_dir.cleanup()
        super().tearDown()

    def _upload(self, filename: str, content: bytes) -> UploadFile:
        return UploadFile(filename=filename, file=io.BytesIO(content))

    def _stored_files(self) -> list[Path]:
        return [path for path in Path(self.temp_dir.name).rglob("*") if path.is_file()]

    def test_create_upload_deletes_file_if_db_commit_fails(self):
        with patch.object(self.db, "commit", side_effect=RuntimeError("commit failed")):
            with self.assertRaises(RuntimeError):
                create_document_from_upload(
                    self.db,
                    entity_type="contract",
                    entity_id=self.contract.id,
                    title="Contract Scan",
                    document_type="scan",
                    remarks="rollback test",
                    upload=self._upload("contract.pdf", b"contract-bytes"),
                    current_user=self.user,
                )

        self.assertEqual(self._stored_files(), [])

    def test_version_upload_deletes_new_file_if_db_commit_fails(self):
        document = create_document_from_upload(
            self.db,
            entity_type="contract",
            entity_id=self.contract.id,
            title="Contract Scan",
            document_type="scan",
            remarks="initial",
            upload=self._upload("contract.pdf", b"v1"),
            current_user=self.user,
        )
        existing_files = self._stored_files()
        self.assertEqual(len(existing_files), 1)

        with patch.object(self.db, "commit", side_effect=RuntimeError("commit failed")):
            with self.assertRaises(RuntimeError):
                add_document_version_from_upload(
                    self.db,
                    document_id=document.id,
                    remarks="rollback version",
                    upload=self._upload("contract-v2.pdf", b"v2"),
                    current_user=self.user,
                )

        remaining_files = self._stored_files()
        self.assertEqual(remaining_files, existing_files)

    def test_create_upload_supports_vendor_and_company_linkage(self):
        vendor_document = create_document_from_upload(
            self.db,
            entity_type="vendor",
            entity_id=self.vendor.id,
            title="Marco Vendor Quotation",
            document_type="quotation",
            remarks="vendor linked quote",
            upload=self._upload("vendor-quotation.pdf", b"vendor quotation"),
            current_user=self.user,
        )
        company_document = create_document_from_upload(
            self.db,
            entity_type="company",
            entity_id=self.company.id,
            title="Marco Company Quotation",
            document_type="quotation",
            remarks="company linked quote",
            upload=self._upload("company-quotation.pdf", b"company quotation"),
            current_user=self.user,
        )

        self.assertEqual(vendor_document.entity_type, "vendor")
        self.assertEqual(vendor_document.entity_id, self.vendor.id)
        self.assertEqual(vendor_document.document_type, "quotation")
        self.assertEqual(company_document.entity_type, "company")
        self.assertEqual(company_document.entity_id, self.company.id)
        self.assertEqual(company_document.document_type, "quotation")
        self.assertEqual(len(self._stored_files()), 2)

    def test_vendor_linked_quotation_accepts_version_upload(self):
        document = create_document_from_upload(
            self.db,
            entity_type="vendor",
            entity_id=self.vendor.id,
            title="Marco Vendor Quotation",
            document_type="quotation",
            remarks="initial quotation",
            upload=self._upload("vendor-quotation.pdf", b"v1"),
            current_user=self.user,
        )

        updated_document = add_document_version_from_upload(
            self.db,
            document_id=document.id,
            remarks="revised rates",
            upload=self._upload("vendor-quotation-rev-a.pdf", b"v2"),
            current_user=self.user,
        )

        self.assertEqual(updated_document.entity_type, "vendor")
        self.assertEqual(updated_document.current_version_number, 2)
        self.assertEqual(len(updated_document.versions), 2)
        self.assertEqual(updated_document.versions[-1].remarks, "revised rates")


class LabourWorkflowDocumentUploadTests(OperationsDbTestCase):
    def setUp(self):
        super().setUp()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_patch = patch.object(settings, "LOCAL_STORAGE_ROOT", self.temp_dir.name)
        self.storage_patch.start()

        self.contractor = self.create_labour_contractor()
        self.attendance = LabourAttendance(
            muster_no="MST-20260403-0001",
            project_id=self.project.id,
            contractor_id=self.contractor.id,
            date=date(2026, 4, 3),
            attendance_date=date(2026, 4, 3),
            marked_by=self.user.id,
            status="approved",
            total_wage=Decimal("12000.00"),
        )
        self.bill = LabourBill(
            bill_no="LB-20260403-0001",
            project_id=self.project.id,
            contract_id=self.contract.id,
            contractor_id=self.contractor.id,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 3),
            status="approved",
            gross_amount=Decimal("12000.00"),
            deductions=Decimal("0.00"),
            net_amount=Decimal("12000.00"),
            net_payable=Decimal("12000.00"),
        )
        self.advance = LabourAdvance(
            advance_no="ADV-20260403-0001",
            project_id=self.project.id,
            contractor_id=self.contractor.id,
            advance_date=date(2026, 4, 3),
            amount=Decimal("3000.00"),
            recovered_amount=Decimal("0.00"),
            balance_amount=Decimal("3000.00"),
            status="active",
        )
        self.db.add_all([self.attendance, self.bill, self.advance])
        self.db.commit()
        self.db.refresh(self.attendance)
        self.db.refresh(self.bill)
        self.db.refresh(self.advance)

    def tearDown(self):
        self.storage_patch.stop()
        self.temp_dir.cleanup()
        super().tearDown()

    def _upload(self, filename: str, content: bytes) -> UploadFile:
        return UploadFile(filename=filename, file=io.BytesIO(content))

    def test_create_upload_supports_labour_workflow_entities(self):
        attendance_document = create_document_from_upload(
            self.db,
            entity_type="labour_attendance",
            entity_id=self.attendance.id,
            title="April Muster Sheet",
            document_type="attendance_sheet",
            remarks="Crew attendance backing sheet",
            upload=self._upload("attendance-sheet.pdf", b"attendance"),
            current_user=self.user,
        )
        bill_document = create_document_from_upload(
            self.db,
            entity_type="labour_bill",
            entity_id=self.bill.id,
            title="April Labour Bill Sheet",
            document_type="labour_bill_sheet",
            remarks="Departmental labour summary",
            upload=self._upload("labour-bill-sheet.pdf", b"bill"),
            current_user=self.user,
        )
        advance_document = create_document_from_upload(
            self.db,
            entity_type="labour_advance",
            entity_id=self.advance.id,
            title="Food Advance Register",
            document_type="labour_advance_sheet",
            remarks="Weekly food advance",
            upload=self._upload("food-advance.pdf", b"advance"),
            current_user=self.user,
        )

        self.assertEqual(attendance_document.entity_type, "labour_attendance")
        self.assertEqual(bill_document.entity_type, "labour_bill")
        self.assertEqual(advance_document.entity_type, "labour_advance")

    def test_labour_bill_document_accepts_version_upload(self):
        document = create_document_from_upload(
            self.db,
            entity_type="labour_bill",
            entity_id=self.bill.id,
            title="April Labour Bill Sheet",
            document_type="labour_bill_sheet",
            remarks="initial sheet",
            upload=self._upload("labour-bill-sheet.pdf", b"v1"),
            current_user=self.user,
        )

        updated_document = add_document_version_from_upload(
            self.db,
            document_id=document.id,
            remarks="revised sheet",
            upload=self._upload("labour-bill-sheet-rev-a.pdf", b"v2"),
            current_user=self.user,
        )

        self.assertEqual(updated_document.entity_type, "labour_bill")
        self.assertEqual(updated_document.current_version_number, 2)
        self.assertEqual(updated_document.versions[-1].remarks, "revised sheet")
