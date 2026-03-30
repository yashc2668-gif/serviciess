"""Verify Alembic upgrade/check discipline and startup behavior on fresh databases."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXECUTABLE = sys.executable


def run_command(args: list[str], *, env: dict[str, str], label: str) -> subprocess.CompletedProcess[str]:
    print(f"[migration-check] {label}: {' '.join(args)}")
    result = subprocess.run(
        args,
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"{label} failed with exit code {result.returncode}")
    return result


def build_env(database_url: str) -> dict[str, str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    return env


def verify_fresh_upgrade_and_drift_check() -> None:
    with tempfile.TemporaryDirectory(prefix="m2n-step7-upgrade-") as temp_dir:
        db_path = Path(temp_dir) / "migration_validation.db"
        env = build_env(f"sqlite:///{db_path.as_posix()}")

        run_command(
            [PYTHON_EXECUTABLE, "-m", "alembic", "upgrade", "head"],
            env=env,
            label="upgrade-head-first-pass",
        )
        run_command(
            [PYTHON_EXECUTABLE, "-m", "alembic", "upgrade", "head"],
            env=env,
            label="upgrade-head-second-pass",
        )

        heads = run_command(
            [PYTHON_EXECUTABLE, "-m", "alembic", "heads"],
            env=env,
            label="heads",
        )
        current = run_command(
            [PYTHON_EXECUTABLE, "-m", "alembic", "current"],
            env=env,
            label="current",
        )

        head_revision = heads.stdout.strip().split(" ", 1)[0]
        if head_revision not in current.stdout:
            raise RuntimeError(
                f"Current revision output does not contain head revision {head_revision!r}"
            )

        run_command(
            [PYTHON_EXECUTABLE, "-m", "alembic", "check"],
            env=env,
            label="alembic-check",
        )


def verify_startup_on_fresh_empty_db() -> None:
    with tempfile.TemporaryDirectory(prefix="m2n-step7-empty-startup-") as temp_dir:
        db_path = Path(temp_dir) / "fresh_empty_startup.db"
        env = build_env(f"sqlite:///{db_path.as_posix()}")
        startup_code = """
from fastapi.testclient import TestClient
import main

with TestClient(main.app) as client:
    response = client.get("/health/ready")
    assert response.status_code == 200, response.text
"""
        run_command(
            [PYTHON_EXECUTABLE, "-c", startup_code],
            env=env,
            label="startup-empty-db",
        )


def verify_startup_after_migrations() -> None:
    with tempfile.TemporaryDirectory(prefix="m2n-step7-migrated-startup-") as temp_dir:
        db_path = Path(temp_dir) / "fresh_migrated_startup.db"
        env = build_env(f"sqlite:///{db_path.as_posix()}")
        run_command(
            [PYTHON_EXECUTABLE, "-m", "alembic", "upgrade", "head"],
            env=env,
            label="upgrade-for-startup-smoke",
        )
        startup_code = """
from fastapi.testclient import TestClient
import main

with TestClient(main.app) as client:
    response = client.get("/health/ready")
    assert response.status_code == 200, response.text
"""
        run_command(
            [PYTHON_EXECUTABLE, "-c", startup_code],
            env=env,
            label="startup-migrated-db",
        )


def main() -> int:
    verify_fresh_upgrade_and_drift_check()
    verify_startup_on_fresh_empty_db()
    verify_startup_after_migrations()
    print("[migration-check] all migration discipline checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
