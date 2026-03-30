"""Labour contractor endpoints."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.labour_contractor import (
    LabourContractorCreate,
    LabourContractorOut,
    LabourContractorUpdate,
)
from app.services.labour_contractor_service import (
    create_labour_contractor,
    delete_labour_contractor,
    get_labour_contractor_or_404,
    list_labour_contractors,
    update_labour_contractor,
)
from app.utils.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/labour-contractors", tags=["Labour Contractors"])


@router.get("/", response_model=PaginatedResponse[LabourContractorOut])
def list_all_labour_contractors(
    is_active: bool | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour_contractors:read")),
):
    return list_labour_contractors(
        db,
        current_user=current_user,
        pagination=pagination,
        is_active=is_active,
    )


@router.post("/", response_model=LabourContractorOut, status_code=201)
def create_new_labour_contractor(
    payload: LabourContractorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour_contractors:create")),
):
    return create_labour_contractor(db, payload, current_user)


@router.get("/{contractor_id}", response_model=LabourContractorOut)
def get_single_labour_contractor(
    contractor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour_contractors:read")),
):
    return get_labour_contractor_or_404(db, contractor_id, current_user=current_user)


@router.put("/{contractor_id}", response_model=LabourContractorOut)
def update_existing_labour_contractor(
    contractor_id: int,
    payload: LabourContractorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour_contractors:update")),
):
    return update_labour_contractor(db, contractor_id, payload, current_user)


@router.delete("/{contractor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_labour_contractor(
    contractor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour_contractors:delete")),
):
    delete_labour_contractor(db, contractor_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
