"""Vendor endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.vendor import VendorCreate, VendorOut, VendorUpdate
from app.services.vendor_service import create_vendor, update_vendor

router = APIRouter(prefix="/vendors", tags=["Vendors"])


@router.post("/", response_model=VendorOut, status_code=201)
def create_new_vendor(
    payload: VendorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("vendors:create")),
):
    return create_vendor(db, payload, current_user)


@router.put("/{vendor_id}", response_model=VendorOut)
def update_existing_vendor(
    vendor_id: int,
    payload: VendorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("vendors:update")),
):
    return update_vendor(db, vendor_id, payload, current_user)
