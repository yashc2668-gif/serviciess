"""Backward-compatible singular labour routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.labour import LabourCreate, LabourOut, LabourUpdate
from app.services.labour_service import (
    create_labour,
    get_labour_or_404,
    list_labours,
    update_labour,
)
from app.utils.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/labour", tags=["Labour Master"])


@router.get("", response_model=PaginatedResponse[LabourOut], include_in_schema=False)
@router.get("/", response_model=PaginatedResponse[LabourOut], include_in_schema=False)
def list_all_labours_alias(
    contractor_id: int | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour:read")),
):
    return list_labours(
        db,
        current_user=current_user,
        pagination=pagination,
        contractor_id=contractor_id,
        is_active=is_active,
        search=search,
    )


@router.post("", response_model=LabourOut, status_code=201, include_in_schema=False)
@router.post("/", response_model=LabourOut, status_code=201, include_in_schema=False)
def create_new_labour_alias(
    payload: LabourCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour:create")),
):
    return create_labour(db, payload, current_user)


@router.get("/{labour_id}", response_model=LabourOut, include_in_schema=False)
def get_single_labour_alias(
    labour_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour:read")),
):
    return get_labour_or_404(db, labour_id, current_user=current_user)


@router.put("/{labour_id}", response_model=LabourOut, include_in_schema=False)
def update_existing_labour_alias(
    labour_id: int,
    payload: LabourUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour:update")),
):
    return update_labour(db, labour_id, payload, current_user)
