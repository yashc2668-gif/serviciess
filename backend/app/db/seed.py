"""Database seed helpers."""

from sqlalchemy.orm import Session

from app.core.permissions import ROLE_DEFINITIONS
from app.core.permissions import validate_role
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.role import Role
from app.models.user import User


def seed_roles(db: Session) -> None:
    existing_names = {role.name for role in db.query(Role).all()}
    for definition in ROLE_DEFINITIONS.values():
        if definition["label"] in existing_names:
            continue
        db.add(
            Role(
                name=definition["label"],
                description=definition["description"],
            )
        )
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
        seed_roles(db)
        seed_admin_user(db)
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
