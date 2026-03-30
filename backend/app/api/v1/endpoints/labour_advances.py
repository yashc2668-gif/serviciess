"""Labour advance endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.labour_advance import (
    LabourAdvanceCreate,
    LabourAdvanceOut,
    LabourAdvanceRecoveryCreate,
    LabourAdvanceRecoveryOut,
    LabourAdvanceUpdate,
)
from app.services.labour_advance_service import (
    add_labour_advance_recovery,
    create_labour_advance,
    get_labour_advance_or_404,
    list_labour_advance_recoveries,
    list_labour_advances,
    update_labour_advance,
)
from app.utils.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/labour-advances", tags=["Labour Advances"])


@router.get("/", response_model=PaginatedResponse[LabourAdvanceOut])
def list_all_labour_advances(
    project_id: int | None = None,
    contractor_id: int | None = None,
    status: str | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour_advances:read")),
):
    return list_labour_advances(
        db,
        current_user=current_user,
        pagination=pagination,
        project_id=project_id,
        contractor_id=contractor_id,
        status_filter=status,
    )


@router.post("/", response_model=LabourAdvanceOut, status_code=201)
def create_new_labour_advance(
    payload: LabourAdvanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour_advances:create")),
):
    return create_labour_advance(db, payload, current_user)


@router.get("/{advance_id}", response_model=LabourAdvanceOut)
def get_single_labour_advance(
    advance_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("labour_advances:read")),
):
    return get_labour_advance_or_404(db, advance_id)


@router.put("/{advance_id}", response_model=LabourAdvanceOut)
def update_existing_labour_advance(
    advance_id: int,
    payload: LabourAdvanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour_advances:update")),
):
    return update_labour_advance(db, advance_id, payload, current_user)


@router.post("/{advance_id}/recoveries", response_model=LabourAdvanceOut)
def add_recovery_to_labour_advance(
    advance_id: int,
    payload: LabourAdvanceRecoveryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour_advances:update")),
):
    return add_labour_advance_recovery(db, advance_id, payload, current_user)


@router.get("/{advance_id}/recoveries", response_model=list[LabourAdvanceRecoveryOut])
def list_recoveries_for_labour_advance(
    advance_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("labour_advances:read")),
):
    return list_labour_advance_recoveries(db, advance_id)
