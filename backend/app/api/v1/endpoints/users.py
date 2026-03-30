"""Admin user management endpoints."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.permissions import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserOut, UserUpdate
from app.services.user_service import (
    create_user,
    delete_user,
    get_user_or_404,
    list_users,
    update_user,
)
from app.utils.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=PaginatedResponse[UserOut])
def list_all_users(
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    return list_users(db, pagination=pagination)


@router.post("/", response_model=UserOut, status_code=201)
def create_admin_user(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    return create_user(db, payload)


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    return get_user_or_404(db, user_id)


@router.put("/{user_id}", response_model=UserOut)
def update_existing_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    return update_user(db, user_id, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    delete_user(db, user_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
