"""Vendor service helpers."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.vendor import Vendor
from app.models.user import User
from app.schemas.vendor import VendorCreate, VendorUpdate
from app.services.audit_service import log_audit_event, serialize_model


def _ensure_unique_vendor(
    db: Session,
    name: str,
    code: str | None,
    *,
    exclude_vendor_id: int | None = None,
) -> None:
    existing_name_query = db.query(Vendor).filter(Vendor.name == name)
    if exclude_vendor_id is not None:
        existing_name_query = existing_name_query.filter(Vendor.id != exclude_vendor_id)
    existing_name = existing_name_query.first()
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor name already exists",
        )
    if code:
        existing_code_query = db.query(Vendor).filter(Vendor.code == code)
        if exclude_vendor_id is not None:
            existing_code_query = existing_code_query.filter(Vendor.id != exclude_vendor_id)
        existing_code = existing_code_query.first()
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vendor code already exists",
            )


def get_vendor_or_404(db: Session, vendor_id: int) -> Vendor:
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found",
        )
    return vendor


def create_vendor(db: Session, payload: VendorCreate, current_user: User) -> Vendor:
    _ensure_unique_vendor(db, payload.name, payload.code)
    vendor = Vendor(**payload.model_dump())
    db.add(vendor)
    db.flush()
    log_audit_event(
        db,
        entity_type="vendor",
        entity_id=vendor.id,
        action="create",
        performed_by=current_user,
        after_data=serialize_model(vendor),
        remarks=vendor.name,
    )
    db.commit()
    db.refresh(vendor)
    return vendor


def update_vendor(
    db: Session,
    vendor_id: int,
    payload: VendorUpdate,
    current_user: User,
) -> Vendor:
    vendor = get_vendor_or_404(db, vendor_id)
    updates = payload.model_dump(exclude_unset=True)
    next_name = updates.get("name", vendor.name)
    next_code = updates.get("code", vendor.code)
    _ensure_unique_vendor(db, next_name, next_code, exclude_vendor_id=vendor.id)

    before_data = serialize_model(vendor)
    for field, value in updates.items():
        setattr(vendor, field, value)
    db.flush()
    log_audit_event(
        db,
        entity_type="vendor",
        entity_id=vendor.id,
        action="update",
        performed_by=current_user,
        before_data=before_data,
        after_data=serialize_model(vendor),
        remarks=vendor.name,
    )
    db.commit()
    db.refresh(vendor)
    return vendor
