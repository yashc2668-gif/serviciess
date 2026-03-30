"""Vendor service helpers."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.material_receipt import MaterialReceipt
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.vendor import VendorCreate, VendorUpdate
from app.services.audit_service import log_audit_event, serialize_model
from app.services.company_scope_service import (
    apply_vendor_company_scope,
    require_company_scope,
    resolve_company_scope,
)
from app.services.concurrency_service import (
    commit_with_conflict_handling,
    ensure_lock_version_matches,
    flush_with_conflict_handling,
)
from app.utils.pagination import PaginationParams, paginate_query


def _ensure_unique_vendor(
    db: Session,
    name: str,
    code: str | None,
    *,
    exclude_vendor_id: int | None = None,
) -> None:
    existing_name_query = db.query(Vendor).filter(Vendor.name == name, Vendor.is_deleted.is_(False))
    if exclude_vendor_id is not None:
        existing_name_query = existing_name_query.filter(Vendor.id != exclude_vendor_id)
    existing_name = existing_name_query.first()
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor name already exists",
        )
    if code:
        existing_code_query = db.query(Vendor).filter(Vendor.code == code, Vendor.is_deleted.is_(False))
        if exclude_vendor_id is not None:
            existing_code_query = existing_code_query.filter(Vendor.id != exclude_vendor_id)
        existing_code = existing_code_query.first()
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vendor code already exists",
            )


def get_vendor_or_404(db: Session, vendor_id: int, *, current_user: User) -> Vendor:
    company_id = resolve_company_scope(current_user)
    vendor = (
        apply_vendor_company_scope(
            db.query(Vendor).filter(Vendor.is_deleted.is_(False)),
            company_id,
        )
        .filter(Vendor.id == vendor_id)
        .first()
    )
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found",
        )
    return vendor


def create_vendor(db: Session, payload: VendorCreate, current_user: User) -> Vendor:
    company_id = require_company_scope(current_user, payload.company_id)
    _ensure_unique_vendor(db, payload.name, payload.code)
    vendor = Vendor(**payload.model_dump(exclude={"company_id"}), company_id=company_id)
    db.add(vendor)
    flush_with_conflict_handling(db, entity_name="Vendor")
    log_audit_event(
        db,
        entity_type="vendor",
        entity_id=vendor.id,
        action="create",
        performed_by=current_user,
        after_data=serialize_model(vendor),
        remarks=vendor.name,
    )
    commit_with_conflict_handling(db, entity_name="Vendor")
    db.refresh(vendor)
    return vendor


def update_vendor(
    db: Session,
    vendor_id: int,
    payload: VendorUpdate,
    current_user: User,
) -> Vendor:
    vendor = get_vendor_or_404(db, vendor_id, current_user=current_user)
    updates = payload.model_dump(exclude_unset=True)
    ensure_lock_version_matches(
        vendor,
        updates.pop("lock_version", None),
        entity_name="Vendor",
    )
    if "company_id" in updates and updates["company_id"] is not None:
        updates["company_id"] = require_company_scope(current_user, updates["company_id"])
    next_name = updates.get("name", vendor.name)
    next_code = updates.get("code", vendor.code)
    _ensure_unique_vendor(db, next_name, next_code, exclude_vendor_id=vendor.id)

    before_data = serialize_model(vendor)
    for field, value in updates.items():
        setattr(vendor, field, value)
    flush_with_conflict_handling(db, entity_name="Vendor")
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
    commit_with_conflict_handling(db, entity_name="Vendor")
    db.refresh(vendor)
    return vendor


def list_vendors(
    db: Session,
    current_user: User,
    *,
    pagination: PaginationParams,
    search: str | None = None,
    vendor_type: str | None = None,
) -> dict[str, object]:
    company_id = resolve_company_scope(current_user)
    query = apply_vendor_company_scope(
        db.query(Vendor).filter(Vendor.is_deleted.is_(False)),
        company_id,
    )
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            Vendor.name.ilike(pattern) | Vendor.code.ilike(pattern)
        )
    if vendor_type:
        query = query.filter(Vendor.vendor_type == vendor_type)
    return paginate_query(query.order_by(Vendor.name), pagination=pagination)


def delete_vendor(db: Session, vendor_id: int, current_user: User) -> None:
    vendor = get_vendor_or_404(db, vendor_id, current_user=current_user)
    dependencies: list[str] = []
    if (
        db.query(Contract.id)
        .filter(
            Contract.vendor_id == vendor.id,
            Contract.is_deleted.is_(False),
            Contract.status.in_(["draft", "active", "on_hold"]),
        )
        .first()
    ):
        dependencies.append("active_contracts")
    if db.query(MaterialReceipt.id).filter(MaterialReceipt.vendor_id == vendor.id).first():
        dependencies.append("material_receipts")
    if dependencies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Vendor cannot be deleted because it is referenced by: "
                + ", ".join(dependencies)
            ),
        )

    before_data = serialize_model(vendor)
    log_audit_event(
        db,
        entity_type="vendor",
        entity_id=vendor.id,
        action="delete",
        performed_by=current_user,
        before_data=before_data,
        remarks=vendor.name,
    )
    vendor.is_deleted = True
    vendor.deleted_at = datetime.now(timezone.utc)
    flush_with_conflict_handling(db, entity_name="Vendor")
    commit_with_conflict_handling(db, entity_name="Vendor")
