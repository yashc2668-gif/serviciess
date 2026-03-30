"""Labour productivity endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.labour_productivity import (
    LabourProductivityCreate,
    LabourProductivityOut,
    LabourProductivityUpdate,
)
from app.services.labour_productivity_service import (
    create_labour_productivity,
    get_labour_productivity_or_404,
    list_labour_productivities,
    update_labour_productivity,
)
from app.utils.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/labour-productivities", tags=["Labour Productivity"])


@router.get("/", response_model=PaginatedResponse[LabourProductivityOut])
def list_all_labour_productivities(
    project_id: int | None = None,
    contract_id: int | None = None,
    labour_id: int | None = None,
    trade: str | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour_productivity:read")),
):
    return list_labour_productivities(
        db,
        current_user=current_user,
        pagination=pagination,
        project_id=project_id,
        contract_id=contract_id,
        labour_id=labour_id,
        trade=trade,
    )


@router.post("/", response_model=LabourProductivityOut, status_code=201)
def create_new_labour_productivity(
    payload: LabourProductivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour_productivity:create")),
):
    return create_labour_productivity(db, payload, current_user)


@router.get("/{productivity_id}", response_model=LabourProductivityOut)
def get_single_labour_productivity(
    productivity_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("labour_productivity:read")),
):
    return get_labour_productivity_or_404(db, productivity_id)


@router.put("/{productivity_id}", response_model=LabourProductivityOut)
def update_existing_labour_productivity(
    productivity_id: int,
    payload: LabourProductivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour_productivity:update")),
):
    return update_labour_productivity(db, productivity_id, payload, current_user)
