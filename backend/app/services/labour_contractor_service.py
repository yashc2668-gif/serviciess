"""Labour contractor service helpers."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.labour_contractor import LabourContractor
from app.models.user import User
from app.schemas.labour_contractor import LabourContractorCreate, LabourContractorUpdate
from app.services.audit_service import log_audit_event, serialize_model
from app.services.company_scope_service import (
    apply_labour_contractor_company_scope,
    require_company_scope,
    resolve_company_scope,
)
from app.services.concurrency_service import (
    commit_with_conflict_handling,
    ensure_lock_version_matches,
    flush_with_conflict_handling,
)
from app.utils.pagination import PaginationParams, paginate_query


def _normalize_optional_text(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    return raw_value.strip() or None


def _normalize_code(raw_code: str) -> str:
    normalized = raw_code.strip().upper()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="contractor_code cannot be empty",
        )
    return normalized


def _generate_contractor_code(db: Session, contractor_name: str) -> str:
    token = "".join(ch for ch in contractor_name.upper() if ch.isalnum())[:4] or "GEN"
    prefix = f"LCTR-{token}"
    for index in range(1, 10000):
        candidate = f"{prefix}-{index:03d}"
        exists = (
            db.query(LabourContractor.id)
            .filter(func.lower(LabourContractor.contractor_code) == candidate.lower())
            .first()
        )
        if not exists:
            return candidate
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to generate a unique contractor code",
    )


def _ensure_unique_contractor(
    db: Session,
    contractor_code: str,
    contractor_name: str,
    *,
    exclude_contractor_id: int | None = None,
) -> None:
    code_query = db.query(LabourContractor).filter(
        func.lower(LabourContractor.contractor_code) == contractor_code.lower()
    )
    name_query = db.query(LabourContractor).filter(
        func.lower(LabourContractor.contractor_name) == contractor_name.lower()
    )
    if exclude_contractor_id is not None:
        code_query = code_query.filter(LabourContractor.id != exclude_contractor_id)
        name_query = name_query.filter(LabourContractor.id != exclude_contractor_id)
    if code_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contractor code already exists",
        )
    if name_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contractor name already exists",
        )


def list_labour_contractors(
    db: Session,
    current_user: User,
    *,
    pagination: PaginationParams,
    is_active: bool | None = None,
) -> dict[str, object]:
    company_id = resolve_company_scope(current_user)
    query = apply_labour_contractor_company_scope(db.query(LabourContractor), company_id)
    if is_active is not None:
        query = query.filter(LabourContractor.is_active == is_active)
    return paginate_query(
        query.order_by(LabourContractor.contractor_name.asc(), LabourContractor.id.asc()),
        pagination=pagination,
    )


def get_labour_contractor_or_404(
    db: Session,
    contractor_id: int,
    *,
    current_user: User,
) -> LabourContractor:
    contractor = (
        apply_labour_contractor_company_scope(
            db.query(LabourContractor),
            resolve_company_scope(current_user),
        )
        .filter(LabourContractor.id == contractor_id)
        .first()
    )
    if not contractor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labour contractor not found",
        )
    return contractor


def create_labour_contractor(
    db: Session,
    payload: LabourContractorCreate,
    current_user: User,
) -> LabourContractor:
    data = payload.model_dump()
    data["company_id"] = require_company_scope(current_user, data.get("company_id"))
    data["contractor_name"] = data["contractor_name"].strip()
    if not data["contractor_name"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="contractor_name cannot be empty",
        )
    raw_code = data.get("contractor_code")
    if raw_code:
        data["contractor_code"] = _normalize_code(raw_code)
    else:
        data["contractor_code"] = _generate_contractor_code(db, data["contractor_name"])
    data["contact_person"] = _normalize_optional_text(data.get("contact_person"))
    data["gang_name"] = data["contact_person"]
    data["phone"] = _normalize_optional_text(data.get("phone"))
    data["address"] = _normalize_optional_text(data.get("address"))

    _ensure_unique_contractor(db, data["contractor_code"], data["contractor_name"])
    contractor = LabourContractor(**data)
    db.add(contractor)
    flush_with_conflict_handling(db, entity_name="Labour contractor")
    log_audit_event(
        db,
        entity_type="labour_contractor",
        entity_id=contractor.id,
        action="create",
        performed_by=current_user,
        after_data=serialize_model(contractor),
        remarks=contractor.contractor_name,
    )
    commit_with_conflict_handling(db, entity_name="Labour contractor")
    db.refresh(contractor)
    return contractor


def update_labour_contractor(
    db: Session,
    contractor_id: int,
    payload: LabourContractorUpdate,
    current_user: User,
) -> LabourContractor:
    contractor = get_labour_contractor_or_404(db, contractor_id, current_user=current_user)
    updates = payload.model_dump(exclude_unset=True)
    ensure_lock_version_matches(
        contractor,
        updates.pop("lock_version", None),
        entity_name="Labour contractor",
    )
    if "company_id" in updates and updates["company_id"] is not None:
        updates["company_id"] = require_company_scope(current_user, updates["company_id"])

    if "contractor_code" in updates and updates["contractor_code"] is not None:
        updates["contractor_code"] = _normalize_code(updates["contractor_code"])
    if "contractor_name" in updates and updates["contractor_name"] is not None:
        updates["contractor_name"] = updates["contractor_name"].strip()
        if not updates["contractor_name"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="contractor_name cannot be empty",
            )
    if "contact_person" in updates:
        updates["contact_person"] = _normalize_optional_text(updates["contact_person"])
        updates["gang_name"] = updates["contact_person"]
    for field in ("phone", "address"):
        if field in updates:
            updates[field] = _normalize_optional_text(updates[field])

    next_code = updates.get("contractor_code", contractor.contractor_code)
    next_name = updates.get("contractor_name", contractor.contractor_name)
    _ensure_unique_contractor(
        db,
        next_code,
        next_name,
        exclude_contractor_id=contractor.id,
    )

    before_data = serialize_model(contractor)
    for field, value in updates.items():
        setattr(contractor, field, value)
    flush_with_conflict_handling(db, entity_name="Labour contractor")
    log_audit_event(
        db,
        entity_type="labour_contractor",
        entity_id=contractor.id,
        action="update",
        performed_by=current_user,
        before_data=before_data,
        after_data=serialize_model(contractor),
        remarks=contractor.contractor_name,
    )
    commit_with_conflict_handling(db, entity_name="Labour contractor")
    db.refresh(contractor)
    return contractor


def delete_labour_contractor(
    db: Session,
    contractor_id: int,
    current_user: User,
) -> None:
    """Deactivate a contractor after checking for active child records."""
    from app.models.labour import Labour
    from app.models.labour_advance import LabourAdvance
    from app.models.labour_attendance import LabourAttendance
    from app.models.labour_bill import LabourBill

    contractor = get_labour_contractor_or_404(db, contractor_id, current_user=current_user)
    dependencies: list[str] = []
    dependency_checks = (
        (
            "active_labour",
            db.query(Labour.id).filter(
                Labour.contractor_id == contractor.id,
                Labour.is_deleted.is_(False),
            ),
        ),
        (
            "active_attendance",
            db.query(LabourAttendance.id).filter(
                LabourAttendance.contractor_id == contractor.id,
                LabourAttendance.status.notin_(["cancelled"]),
            ),
        ),
        (
            "active_bills",
            db.query(LabourBill.id).filter(
                LabourBill.contractor_id == contractor.id,
                LabourBill.status.notin_(["cancelled"]),
            ),
        ),
        (
            "active_advances",
            db.query(LabourAdvance.id).filter(
                LabourAdvance.contractor_id == contractor.id,
                LabourAdvance.status.notin_(["cancelled", "closed"]),
            ),
        ),
    )
    for label, query in dependency_checks:
        if query.first():
            dependencies.append(label)
    if dependencies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Labour contractor cannot be deleted because it is referenced by: "
                + ", ".join(dependencies)
            ),
        )

    before_data = serialize_model(contractor)
    log_audit_event(
        db,
        entity_type="labour_contractor",
        entity_id=contractor.id,
        action="delete",
        performed_by=current_user,
        before_data=before_data,
        remarks=contractor.contractor_name,
    )
    contractor.is_active = False
    contractor.updated_at = datetime.now(timezone.utc)
    flush_with_conflict_handling(db, entity_name="Labour contractor")
    commit_with_conflict_handling(db, entity_name="Labour contractor")
