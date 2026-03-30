"""Backup and recovery readiness regression tests."""

from __future__ import annotations

from pathlib import Path
import unittest


class BackupRecoveryReadinessTests(unittest.TestCase):
    backend_root = Path(__file__).resolve().parents[2]

    def read_text(self, relative_path: str) -> str:
        return (self.backend_root / relative_path).read_text(encoding="utf-8")

    def test_backup_runbook_covers_required_sections(self):
        contents = self.read_text("BACKUP_RECOVERY_RUNBOOK.md")

        self.assertIn("## Backup strategy", contents)
        self.assertIn("## Restore process", contents)
        self.assertIn("## Restore test checklist", contents)
        self.assertIn("## Monthly recovery drill recommendation", contents)
        self.assertIn("/health/ready", contents)

    def test_backup_and_restore_scripts_contain_core_commands(self):
        backup_script = self.read_text("docker/backup-compose-postgres.sh")
        restore_script = self.read_text("docker/restore-compose-postgres.sh")

        self.assertIn("pg_dump", backup_script)
        self.assertIn("uploads.tar.gz", backup_script)
        self.assertIn("alembic_version", backup_script)

        self.assertIn("pg_restore", restore_script)
        self.assertIn("RESTORE_MODE", restore_script)
        self.assertIn("CONFIRM_INPLACE_RESTORE", restore_script)

    def test_ops_docs_reference_backup_assets(self):
        readme = self.read_text("README.md")
        runbook = self.read_text("RUNBOOK.md")
        staging_setup = self.read_text("STAGING_SETUP.md")
        deploy_script = self.read_text("docker/deploy-staging.sh")

        self.assertIn("BACKUP_RECOVERY_RUNBOOK.md", readme)
        self.assertIn("backup-compose-postgres.sh", readme)
        self.assertIn("BACKUP_RECOVERY_RUNBOOK.md", runbook)
        self.assertIn("RUN_PREDEPLOY_BACKUP=true", staging_setup)
        self.assertIn("backup-compose-postgres.sh", deploy_script)


if __name__ == "__main__":
    unittest.main()
