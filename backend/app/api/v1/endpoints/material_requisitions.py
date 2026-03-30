"""Material requisition endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.material_requisition import (
    MaterialRequisitionApproveRequest,
    MaterialRequisitionCreate,
    MaterialRequisitionOut,
    MaterialRequisitionTransitionRequest,
    MaterialRequisitionUpdate,
)
from app.services.material_requisition_service import (
    approve_material_requisition,
    create_material_requisition,
    get_material_requisition_or_404,
    list_material_requisitions,
    reject_material_requisition,
    submit_material_requisition,
    update_material_requisition,
)
from app.utils.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/material-requisitions", tags=["Material Requisitions"])


@router.get("", response_model=PaginatedResponse[MaterialRequisitionOut])
@router.get("/", response_model=PaginatedResponse[MaterialRequisitionOut], include_in_schema=False)
def list_all_material_requisitions(
    project_id: int | None = None,
    contract_id: int | None = None,
    status: str | None = None,
    requested_by: int | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("material_requisitions:read")),
):
    return list_material_requisitions(
        db,
        current_user=current_user,
        pagination=pagination,
        project_id=project_id,
        contract_id=contract_id,
        status_filter=status,
        requested_by=requested_by,
    )


@router.post("", response_model=MaterialRequisitionOut, status_code=201)
@router.post("/", response_model=MaterialRequisitionOut, status_code=201, include_in_schema=False)
def create_new_material_requisition(
    payload: MaterialRequisitionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("requisitions:create")),
):
    return create_material_requisition(db, payload, current_user)


@router.get("/{requisition_id}", response_model=MaterialRequisitionOut)
def get_single_material_requisition(
    requisition_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("material_requisitions:read")),
):
    return get_material_requisition_or_404(db, requisition_id)


@router.put("/{requisition_id}", response_model=MaterialRequisitionOut)
def update_existing_material_requisition(
    requisition_id: int,
    payload: MaterialRequisitionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("requisitions:approve")),
):
    return update_material_requisition(db, requisition_id, payload, current_user)


@router.post("/{requisition_id}/submit", response_model=MaterialRequisitionOut)
def submit_existing_material_requisition(
    requisition_id: int,
    payload: MaterialRequisitionTransitionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("requisitions:create")),
):
    return submit_material_requisition(
        db,
        requisition_id,
        current_user,
        remarks=payload.remarks if payload is not None else None,
    )


@router.post("/{requisition_id}/approve", response_model=MaterialRequisitionOut)
def approve_existing_material_requisition(
    requisition_id: int,
    payload: MaterialRequisitionApproveRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("requisitions:approve")),
):
    item_updates = None
    if payload is not None and payload.items is not None:
        item_updates = [item.model_dump(exclude_unset=True) for item in payload.items]
    return approve_material_requisition(
        db,
        requisition_id,
        current_user,
        remarks=payload.remarks if payload is not None else None,
        item_updates=item_updates,
    )


@router.post("/{requisition_id}/reject", response_model=MaterialRequisitionOut)
def reject_existing_material_requisition(
    requisition_id: int,
    payload: MaterialRequisitionTransitionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("requisitions:approve")),
):
    return reject_material_requisition(
        db,
        requisition_id,
        current_user,
        remarks=payload.remarks if payload is not None else None,
    )
