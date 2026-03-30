"""Material receipt endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.material_receipt import (
    MaterialReceiptCreate,
    MaterialReceiptOut,
    MaterialReceiptUpdate,
)
from app.services.material_receipt_service import (
    create_material_receipt,
    get_material_receipt_or_404,
    list_material_receipts,
    update_material_receipt,
)
from app.utils.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/material-receipts", tags=["Material Receipts"])


@router.get("", response_model=PaginatedResponse[MaterialReceiptOut])
@router.get("/", response_model=PaginatedResponse[MaterialReceiptOut], include_in_schema=False)
def list_all_material_receipts(
    vendor_id: int | None = None,
    project_id: int | None = None,
    status: str | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("material_receipts:read")),
):
    return list_material_receipts(
        db,
        current_user=current_user,
        pagination=pagination,
        vendor_id=vendor_id,
        project_id=project_id,
        status_filter=status,
    )


@router.post("", response_model=MaterialReceiptOut, status_code=201)
@router.post(
    "/",
    response_model=MaterialReceiptOut,
    status_code=201,
    include_in_schema=False,
)
def create_new_material_receipt(
    payload: MaterialReceiptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("receipts:create")),
):
    return create_material_receipt(db, payload, current_user)


@router.get("/{receipt_id}", response_model=MaterialReceiptOut)
def get_single_material_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("material_receipts:read")),
):
    return get_material_receipt_or_404(db, receipt_id)


@router.put("/{receipt_id}", response_model=MaterialReceiptOut)
def update_existing_material_receipt(
    receipt_id: int,
    payload: MaterialReceiptUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("material_receipts:update")),
):
    return update_material_receipt(db, receipt_id, payload, current_user)
