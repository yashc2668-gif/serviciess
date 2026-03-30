"""Contract-scoped BOQ endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.boq import BOQItemCreate, BOQItemOut, BOQItemUpdate
from app.schemas.common import PaginatedResponse
from app.services.boq_service import (
    create_boq_item_with_audit,
    list_boq_items_by_contract,
    update_boq_item,
)
from app.utils.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/contracts/{contract_id}/boq-items", tags=["BOQ Items"])


@router.post("/", response_model=BOQItemOut, status_code=201)
def create_contract_boq_item(
    contract_id: int,
    payload: BOQItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("boq:create")),
):
    return create_boq_item_with_audit(db, contract_id, payload, current_user)


@router.get("/", response_model=PaginatedResponse[BOQItemOut])
def list_contract_boq_items(
    contract_id: int,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("boq:read")),
):
    return list_boq_items_by_contract(
        db,
        contract_id,
        current_user=current_user,
        pagination=pagination,
    )


@router.put("/{boq_item_id}", response_model=BOQItemOut)
def update_contract_boq_item(
    contract_id: int,
    boq_item_id: int,
    payload: BOQItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("boq:update")),
):
    return update_boq_item(db, contract_id, boq_item_id, payload, current_user)
