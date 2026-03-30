"""Vendor endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.vendor import VendorCreate, VendorOut, VendorUpdate
from app.services.vendor_service import (
    create_vendor,
    delete_vendor,
    get_vendor_or_404,
    list_vendors,
    update_vendor,
)
from app.utils.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/vendors", tags=["Vendors"])


@router.get("/", response_model=PaginatedResponse[VendorOut])
def list_all_vendors(
    search: str | None = None,
    vendor_type: str | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("vendors:read")),
):
    return list_vendors(
        db,
        current_user=current_user,
        pagination=pagination,
        search=search,
        vendor_type=vendor_type,
    )


@router.post("/", response_model=VendorOut, status_code=201)
def create_new_vendor(
    payload: VendorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("vendors:create")),
):
    return create_vendor(db, payload, current_user)


@router.get("/{vendor_id}", response_model=VendorOut)
def get_single_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("vendors:read")),
):
    return get_vendor_or_404(db, vendor_id, current_user=current_user)


@router.put("/{vendor_id}", response_model=VendorOut)
def update_existing_vendor(
    vendor_id: int,
    payload: VendorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("vendors:update")),
):
    return update_vendor(db, vendor_id, payload, current_user)


@router.delete("/{vendor_id}", status_code=204)
def delete_existing_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("vendors:delete")),
):
    delete_vendor(db, vendor_id, current_user)
