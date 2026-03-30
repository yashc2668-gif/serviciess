"""Database seed helpers."""

import logging

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core.permissions import ROLE_DEFINITIONS
from app.core.permissions import validate_role
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.role import Role
from app.models.user import User

logger = logging.getLogger(__name__)
REQUIRED_SEED_TABLES = ("roles", "users")


def _schema_ready_for_seed(db: Session) -> bool:
    bind = db.get_bind()
    if bind is None:
        return False

    inspector = inspect(bind)
    missing_tables = [table for table in REQUIRED_SEED_TABLES if not inspector.has_table(table)]
    if missing_tables:
        logger.warning(
            "seed.skipped_schema_not_ready",
            extra={"missing_tables": missing_tables},
        )
        return False
    return True


def seed_roles(db: Session) -> None:
    existing_roles = {role.name: role for role in db.query(Role).all()}
    for role_name, definition in ROLE_DEFINITIONS.items():
        role = existing_roles.get(role_name) or existing_roles.get(definition["label"])
        if role is None:
            db.add(
                Role(
                    name=role_name,
                    description=definition["description"],
                )
            )
            continue
        role.name = role_name
        role.description = definition["description"]
    db.commit()


def seed_admin_user(db: Session) -> None:
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        return

    existing = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
    if existing:
        return

    db.add(
        User(
            full_name=settings.ADMIN_FULL_NAME,
            email=settings.ADMIN_EMAIL,
            hashed_password=hash_password(settings.ADMIN_PASSWORD),
            phone=settings.ADMIN_PHONE,
            role=validate_role(settings.ADMIN_ROLE),
            is_active=True,
        )
    )
    db.commit()


def run_seed() -> None:
    """Populate core reference data."""
    db = SessionLocal()
    try:
        if not _schema_ready_for_seed(db):
            return
        seed_roles(db)
        seed_admin_user(db)
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
