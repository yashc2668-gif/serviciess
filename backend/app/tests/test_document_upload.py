"""Tests for document upload rollback safety."""

import io
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi import UploadFile

from app.core.config import settings
from app.services.document_service import (
    add_document_version_from_upload,
    create_document_from_upload,
    delete_document,
)
from app.tests.helpers import FinanceDbTestCase


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

    def test_delete_document_removes_versions_and_stored_files(self):
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
        document = add_document_version_from_upload(
            self.db,
            document_id=document.id,
            remarks="v2",
            upload=self._upload("contract-v2.pdf", b"v2"),
            current_user=self.user,
        )

        self.assertEqual(len(self._stored_files()), 2)

        delete_document(self.db, document.id, self.user)

        self.assertIsNone(self.db.query(type(document)).filter(type(document).id == document.id).first())
        self.assertEqual(self._stored_files(), [])

    def test_create_upload_rejects_temporary_office_file(self):
        with self.assertRaises(HTTPException) as exc:
            create_document_from_upload(
                self.db,
                entity_type="contract",
                entity_id=self.contract.id,
                title="Temp Workbook",
                document_type="sheet",
                remarks="temp",
                upload=self._upload("~$contract.xlsx", b"temp"),
                current_user=self.user,
            )

        self.assertEqual(exc.exception.status_code, 400)
        self.assertIn("Temporary Office files", exc.exception.detail)

