"""Labour master service helpers."""

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.labour import Labour
from app.models.labour_contractor import LabourContractor
from app.models.user import User
from app.schemas.labour import LabourCreate, LabourUpdate
from app.services.audit_service import log_audit_event, serialize_model
from app.services.company_scope_service import (
    apply_labour_company_scope,
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
            detail="labour_code cannot be empty",
        )
    return normalized


def _ensure_unique_labour_code(
    db: Session,
    labour_code: str,
    *,
    exclude_labour_id: int | None = None,
) -> None:
    query = db.query(Labour).filter(
        func.lower(Labour.labour_code) == labour_code.lower(),
        Labour.is_deleted.is_(False),
    )
    if exclude_labour_id is not None:
        query = query.filter(Labour.id != exclude_labour_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Labour code already exists",
        )


def _ensure_contractor_exists(
    db: Session,
    contractor_id: int | None,
    *,
    company_id: int | None,
) -> None:
    if contractor_id is None:
        return
    contractor = (
        apply_labour_contractor_company_scope(
            db.query(LabourContractor),
            company_id,
        )
        .filter(LabourContractor.id == contractor_id)
        .first()
    )
    if not contractor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labour contractor not found",
        )


def list_labours(
    db: Session,
    current_user: User,
    *,
    pagination: PaginationParams,
    contractor_id: int | None = None,
    is_active: bool | None = None,
    search: str | None = None,
) -> dict[str, object]:
    company_id = resolve_company_scope(current_user)
    query = apply_labour_company_scope(
        db.query(Labour).filter(Labour.is_deleted.is_(False)),
        company_id,
    )
    if contractor_id is not None:
        query = query.filter(Labour.contractor_id == contractor_id)
    if is_active is not None:
        query = query.filter(Labour.is_active == is_active)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Labour.labour_code.ilike(search_term),
                Labour.full_name.ilike(search_term),
                Labour.trade.ilike(search_term),
                Labour.skill_type.ilike(search_term),
            )
        )
    return paginate_query(
        query.order_by(Labour.full_name.asc(), Labour.id.asc()),
        pagination=pagination,
    )


def get_labour_or_404(db: Session, labour_id: int, *, current_user: User) -> Labour:
    labour = (
        apply_labour_company_scope(
            db.query(Labour).filter(Labour.is_deleted.is_(False)),
            resolve_company_scope(current_user),
        )
        .filter(Labour.id == labour_id)
        .first()
    )
    if not labour:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labour not found",
        )
    return labour


def create_labour(db: Session, payload: LabourCreate, current_user: User) -> Labour:
    data = payload.model_dump()
    data["company_id"] = require_company_scope(current_user, data.get("company_id"))
    data["labour_code"] = _normalize_code(data["labour_code"])
    data["full_name"] = data["full_name"].strip()
    if not data["full_name"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="full_name cannot be empty",
        )
    data["trade"] = _normalize_optional_text(data.get("trade"))
    data["skill_level"] = _normalize_optional_text(data.get("skill_level"))
    data["daily_rate"] = float(data.get("daily_rate", 0))
    if data["daily_rate"] < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="daily_rate cannot be negative",
        )
    # Keep legacy fields in sync for backward compatibility.
    data["skill_type"] = data["trade"]
    data["default_wage_rate"] = data["daily_rate"]
    data["unit"] = data["unit"].strip()
    if not data["unit"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="unit cannot be empty",
        )

    _ensure_unique_labour_code(db, data["labour_code"])
    _ensure_contractor_exists(db, data.get("contractor_id"), company_id=data["company_id"])

    labour = Labour(**data)
    db.add(labour)
    flush_with_conflict_handling(db, entity_name="Labour")
    log_audit_event(
        db,
        entity_type="labour",
        entity_id=labour.id,
        action="create",
        performed_by=current_user,
        after_data=serialize_model(labour),
        remarks=labour.full_name,
    )
    commit_with_conflict_handling(db, entity_name="Labour")
    db.refresh(labour)
    return labour


def update_labour(
    db: Session,
    labour_id: int,
    payload: LabourUpdate,
    current_user: User,
) -> Labour:
    labour = get_labour_or_404(db, labour_id, current_user=current_user)
    updates = payload.model_dump(exclude_unset=True)
    ensure_lock_version_matches(
        labour,
        updates.pop("lock_version", None),
        entity_name="Labour",
    )
    if "company_id" in updates and updates["company_id"] is not None:
        updates["company_id"] = require_company_scope(current_user, updates["company_id"])

    if "labour_code" in updates and updates["labour_code"] is not None:
        updates["labour_code"] = _normalize_code(updates["labour_code"])
    if "full_name" in updates and updates["full_name"] is not None:
        updates["full_name"] = updates["full_name"].strip()
        if not updates["full_name"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="full_name cannot be empty",
            )
    if "unit" in updates and updates["unit"] is not None:
        updates["unit"] = updates["unit"].strip()
        if not updates["unit"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="unit cannot be empty",
            )
    if "trade" in updates:
        updates["trade"] = _normalize_optional_text(updates["trade"])
        updates["skill_type"] = updates["trade"]
    if "skill_level" in updates:
        updates["skill_level"] = _normalize_optional_text(updates["skill_level"])
    if "daily_rate" in updates and updates["daily_rate"] is not None:
        if float(updates["daily_rate"]) < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="daily_rate cannot be negative",
            )
        updates["default_wage_rate"] = float(updates["daily_rate"])

    next_code = updates.get("labour_code", labour.labour_code)
    _ensure_unique_labour_code(db, next_code, exclude_labour_id=labour.id)
    next_company_id = updates.get("company_id", labour.company_id)
    next_contractor_id = updates.get("contractor_id", labour.contractor_id)
    _ensure_contractor_exists(db, next_contractor_id, company_id=next_company_id)

    before_data = serialize_model(labour)
    for field, value in updates.items():
        setattr(labour, field, value)
    flush_with_conflict_handling(db, entity_name="Labour")
    log_audit_event(
        db,
        entity_type="labour",
        entity_id=labour.id,
        action="update",
        performed_by=current_user,
        before_data=before_data,
        after_data=serialize_model(labour),
        remarks=labour.full_name,
    )
    commit_with_conflict_handling(db, entity_name="Labour")
    db.refresh(labour)
    return labour
