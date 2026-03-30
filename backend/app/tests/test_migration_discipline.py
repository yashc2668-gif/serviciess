"""Migration and startup discipline tests."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class MigrationDisciplineTests(unittest.TestCase):
    backend_root = Path(__file__).resolve().parents[2]

    def run_command(self, args: list[str], *, database_url: str) -> subprocess.CompletedProcess[str]:
        env = dict(**__import__("os").environ)
        env["DATABASE_URL"] = database_url
        result = subprocess.run(
            args,
            cwd=self.backend_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=(
                f"Command failed: {' '.join(args)}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            ),
        )
        return result

    def test_fresh_sqlite_migrations_upgrade_to_head_and_have_no_drift(self):
        with tempfile.TemporaryDirectory(prefix="m2n-test-step7-upgrade-") as temp_dir:
            database_url = f"sqlite:///{Path(temp_dir, 'migration_test.db').as_posix()}"

            self.run_command([sys.executable, "-m", "alembic", "upgrade", "head"], database_url=database_url)
            heads = self.run_command([sys.executable, "-m", "alembic", "heads"], database_url=database_url)
            current = self.run_command([sys.executable, "-m", "alembic", "current"], database_url=database_url)
            self.run_command([sys.executable, "-m", "alembic", "check"], database_url=database_url)

            head_revision = heads.stdout.strip().split(" ", 1)[0]
            self.assertIn(head_revision, current.stdout)

    def test_startup_does_not_crash_on_fresh_empty_sqlite_db(self):
        with tempfile.TemporaryDirectory(prefix="m2n-test-step7-empty-startup-") as temp_dir:
            database_url = f"sqlite:///{Path(temp_dir, 'empty_startup.db').as_posix()}"
            startup_code = """
from fastapi.testclient import TestClient
import main

with TestClient(main.app) as client:
    response = client.get("/health/ready")
    assert response.status_code == 200, response.text
"""
            self.run_command([sys.executable, "-c", startup_code], database_url=database_url)

    def test_startup_succeeds_after_migrating_fresh_sqlite_db(self):
        with tempfile.TemporaryDirectory(prefix="m2n-test-step7-migrated-startup-") as temp_dir:
            database_url = f"sqlite:///{Path(temp_dir, 'migrated_startup.db').as_posix()}"
            self.run_command([sys.executable, "-m", "alembic", "upgrade", "head"], database_url=database_url)

            startup_code = """
from fastapi.testclient import TestClient
import main

with TestClient(main.app) as client:
    response = client.get("/health/ready")
    assert response.status_code == 200, response.text
"""
            self.run_command([sys.executable, "-c", startup_code], database_url=database_url)


if __name__ == "__main__":
    unittest.main()
