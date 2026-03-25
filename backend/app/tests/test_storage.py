"""Tests for pluggable local storage adapter."""

import io
import tempfile
import unittest
from pathlib import Path

from app.integrations.storage import LocalStorageAdapter, StoredFile


class LocalStorageAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.adapter = LocalStorageAdapter(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_returns_stored_file_and_persists_bytes(self):
        result = self.adapter.save(
            io.BytesIO(b"contract attachment"),
            storage_path="documents/contracts/5/v1/test.pdf",
            content_type="application/pdf",
            original_name="test.pdf",
        )

        self.assertIsInstance(result, StoredFile)
        self.assertEqual(result.storage_path, "documents/contracts/5/v1/test.pdf")
        self.assertEqual(result.size, len(b"contract attachment"))
        self.assertEqual(result.content_type, "application/pdf")
        self.assertEqual(result.original_name, "test.pdf")

        persisted_file = Path(self.temp_dir.name) / "documents" / "contracts" / "5" / "v1" / "test.pdf"
        self.assertTrue(persisted_file.exists())
        self.assertEqual(persisted_file.read_bytes(), b"contract attachment")

    def test_exists_and_delete_follow_saved_file(self):
        storage_path = "documents/payments/9/v2/advice.pdf"
        self.adapter.save(io.BytesIO(b"payment advice"), storage_path=storage_path)

        self.assertTrue(self.adapter.exists(storage_path))
        with self.adapter.open_read(storage_path) as stored_file:
            self.assertEqual(stored_file.read(), b"payment advice")
        self.adapter.delete(storage_path)
        self.assertFalse(self.adapter.exists(storage_path))

    def test_path_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            self.adapter.save(io.BytesIO(b"bad"), storage_path="../escape.txt")

        with self.assertRaises(ValueError):
            self.adapter.exists("../escape.txt")

        with self.assertRaises(ValueError):
            self.adapter.delete("../escape.txt")


if __name__ == "__main__":
    unittest.main()
