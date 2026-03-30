"""Admin-facing user service helpers."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import validate_role
from app.core.security import hash_password, validate_password_policy
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.schemas.user import UserUpdate
from app.services.audit_service import log_audit_event, serialize_model
from app.utils.pagination import PaginationParams, paginate_query
from app.core.security import utc_now


def list_users(db: Session, *, pagination: PaginationParams) -> dict[str, object]:
    return paginate_query(
        db.query(User).order_by(User.created_at.desc(), User.id.desc()),
        pagination=pagination,
    )


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
    validate_password_policy(payload.password, email=payload.email)

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
    if "password" in update_data:
        password = update_data.pop("password")
        if password:
            validate_password_policy(password, email=user.email)
            user.hashed_password = hash_password(password)
            user.password_changed_at = utc_now()

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int, current_user: User) -> None:
    user = get_user_or_404(db, user_id)
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )
    if not user.is_active:
        return

    before_data = serialize_model(user)
    user.is_active = False
    db.flush()
    log_audit_event(
        db,
        entity_type="user",
        entity_id=user.id,
        action="deactivate",
        performed_by=current_user,
        before_data=before_data,
        after_data=serialize_model(user),
        remarks=user.email,
    )
    db.commit()
