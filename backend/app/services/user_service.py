"""Admin-facing user service helpers."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import validate_role
from app.core.security import hash_password
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.schemas.user import UserUpdate


def list_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.created_at.desc(), User.id.desc()).all()


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def create_user(db: Session, payload: RegisterRequest) -> User:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        company_id=payload.company_id,
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        phone=payload.phone,
        role=validate_role(payload.role),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: int, payload: UserUpdate) -> User:
    user = get_user_or_404(db, user_id)
    update_data = payload.model_dump(exclude_unset=True)
    if "role" in update_data and update_data["role"] is not None:
        update_data["role"] = validate_role(update_data["role"])

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> None:
    user = get_user_or_404(db, user_id)
    db.delete(user)
    db.commit()
