"""Labour advance service helpers."""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.labour_advance import LabourAdvance
from app.models.labour_advance_recovery import LabourAdvanceRecovery
from app.models.labour_bill import LabourBill
from app.models.labour_contractor import LabourContractor
from app.models.project import Project
from app.models.user import User
from app.schemas.labour_advance import (
    LabourAdvanceCreate,
    LabourAdvanceRecoveryCreate,
    LabourAdvanceUpdate,
)
from app.services.audit_service import (
    log_audit_event,
    serialize_model,
    serialize_models,
)
from app.services.company_scope_service import (
    apply_labour_advance_company_scope,
    resolve_company_scope,
)
from app.services.concurrency_service import (
    apply_write_lock,
    commit_with_conflict_handling,
    flush_with_conflict_handling,
)
from app.utils.pagination import PaginationParams, paginate_query

VALID_LABOUR_ADVANCE_STATUSES = {"active", "closed", "cancelled"}


def _normalize_status(raw_status: str) -> str:
    normalized = raw_status.strip().lower()
    if normalized not in VALID_LABOUR_ADVANCE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid labour advance status. Allowed values: active, closed, cancelled",
        )
    return normalized


def _normalize_advance_no(raw_advance_no: str) -> str:
    normalized = raw_advance_no.strip().upper()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="advance_no cannot be empty",
        )
    return normalized


def _normalize_optional_text(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    return raw_value.strip() or None


def _ensure_unique_advance_no(
    db: Session,
    advance_no: str,
    *,
    exclude_advance_id: int | None = None,
) -> None:
    query = db.query(LabourAdvance).filter(
        func.lower(LabourAdvance.advance_no) == advance_no.lower()
    )
    if exclude_advance_id is not None:
        query = query.filter(LabourAdvance.id != exclude_advance_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Advance number already exists",
        )


def _ensure_project_exists(db: Session, project_id: int) -> None:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )


def _ensure_contractor_exists(db: Session, contractor_id: int) -> None:
    contractor = (
        db.query(LabourContractor).filter(LabourContractor.id == contractor_id).first()
    )
    if not contractor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labour contractor not found",
        )


def _ensure_bill_exists(
    db: Session,
    labour_bill_id: int | None,
    *,
    lock_for_update: bool = False,
) -> LabourBill | None:
    if labour_bill_id is None:
        return None
    query = db.query(LabourBill).filter(LabourBill.id == labour_bill_id)
    if lock_for_update:
        query = apply_write_lock(query, db)
    bill = query.first()
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labour bill not found",
        )
    return bill


def _serialize_advance(advance: LabourAdvance) -> dict:
    return {
        "advance": serialize_model(advance),
        "recoveries": serialize_models(list(advance.recoveries)),
    }


def list_labour_advances(
    db: Session,
    *,
    current_user: User,
    pagination: PaginationParams,
    project_id: int | None = None,
    contractor_id: int | None = None,
    status_filter: str | None = None,
) -> dict[str, object]:
    company_id = resolve_company_scope(current_user)
    query = apply_labour_advance_company_scope(
        db.query(LabourAdvance).options(joinedload(LabourAdvance.recoveries)),
        company_id,
    )
    if project_id is not None:
        query = query.filter(LabourAdvance.project_id == project_id)
    if contractor_id is not None:
        query = query.filter(LabourAdvance.contractor_id == contractor_id)
    if status_filter:
        query = query.filter(LabourAdvance.status == _normalize_status(status_filter))
    return paginate_query(
        query.order_by(LabourAdvance.advance_date.desc(), LabourAdvance.id.desc()),
        pagination=pagination,
    )


def get_labour_advance_or_404(
    db: Session,
    advance_id: int,
    *,
    lock_for_update: bool = False,
) -> LabourAdvance:
    query = (
        db.query(LabourAdvance)
        .options(joinedload(LabourAdvance.recoveries))
        .filter(LabourAdvance.id == advance_id)
    )
    if lock_for_update:
        query = apply_write_lock(query, db)
    advance = query.first()
    if not advance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labour advance not found",
        )
    return advance


def list_labour_advance_recoveries(
    db: Session,
    advance_id: int,
) -> list[LabourAdvanceRecovery]:
    get_labour_advance_or_404(db, advance_id)
    return (
        db.query(LabourAdvanceRecovery)
        .filter(LabourAdvanceRecovery.advance_id == advance_id)
        .order_by(LabourAdvanceRecovery.recovery_date.asc(), LabourAdvanceRecovery.id.asc())
        .all()
    )


def create_labour_advance(
    db: Session,
    payload: LabourAdvanceCreate,
    current_user: User,
) -> LabourAdvance:
    data = payload.model_dump()
    data["advance_no"] = _normalize_advance_no(data["advance_no"])
    data["status"] = _normalize_status(data["status"])
    data["remarks"] = _normalize_optional_text(data.get("remarks"))

    _ensure_unique_advance_no(db, data["advance_no"])
    _ensure_project_exists(db, data["project_id"])
    _ensure_contractor_exists(db, data["contractor_id"])

    amount = Decimal(str(data["amount"]))
    data["amount"] = amount
    data["recovered_amount"] = Decimal("0")
    data["balance_amount"] = amount
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="amount must be greater than 0",
        )
    if amount == 0:
        data["status"] = "closed"

    advance = LabourAdvance(**data)
    db.add(advance)
    flush_with_conflict_handling(db, entity_name="Labour advance")
    log_audit_event(
        db,
        entity_type="labour_advance",
        entity_id=advance.id,
        action="create",
        performed_by=current_user,
        after_data=_serialize_advance(advance),
        remarks=advance.advance_no,
    )
    commit_with_conflict_handling(db, entity_name="Labour advance")
    return get_labour_advance_or_404(db, advance.id)


def update_labour_advance(
    db: Session,
    advance_id: int,
    payload: LabourAdvanceUpdate,
    current_user: User,
) -> LabourAdvance:
    advance = get_labour_advance_or_404(db, advance_id, lock_for_update=True)
    updates = payload.model_dump(exclude_unset=True)

    if "advance_no" in updates and updates["advance_no"] is not None:
        updates["advance_no"] = _normalize_advance_no(updates["advance_no"])
        _ensure_unique_advance_no(
            db,
            updates["advance_no"],
            exclude_advance_id=advance.id,
        )
    if "status" in updates and updates["status"] is not None:
        updates["status"] = _normalize_status(updates["status"])
    if "remarks" in updates:
        updates["remarks"] = _normalize_optional_text(updates["remarks"])

    next_contractor_id = updates.get("contractor_id", advance.contractor_id)
    _ensure_contractor_exists(db, next_contractor_id)

    next_amount = Decimal(str(updates.get("amount", advance.amount)))
    recovered = Decimal(str(advance.recovered_amount or 0))
    if next_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="amount must be greater than 0",
        )
    if recovered > next_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="amount cannot be less than recovered_amount",
        )
    updates["balance_amount"] = next_amount - recovered
    if updates["balance_amount"] == 0 and "status" not in updates:
        updates["status"] = "closed"
    elif "status" not in updates and advance.status == "closed":
        updates["status"] = "active"

    before_data = _serialize_advance(advance)
    for field, value in updates.items():
        setattr(advance, field, value)
    flush_with_conflict_handling(db, entity_name="Labour advance")
    log_audit_event(
        db,
        entity_type="labour_advance",
        entity_id=advance.id,
        action="update",
        performed_by=current_user,
        before_data=before_data,
        after_data=_serialize_advance(advance),
        remarks=advance.advance_no,
    )
    commit_with_conflict_handling(db, entity_name="Labour advance")
    return get_labour_advance_or_404(db, advance.id)


def add_labour_advance_recovery(
    db: Session,
    advance_id: int,
    payload: LabourAdvanceRecoveryCreate,
    current_user: User,
) -> LabourAdvance:
    advance = get_labour_advance_or_404(db, advance_id, lock_for_update=True)
    if advance.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot recover a cancelled advance",
        )

    bill = _ensure_bill_exists(db, payload.labour_bill_id, lock_for_update=True)
    if bill and bill.contractor_id != advance.contractor_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Labour bill contractor does not match advance contractor",
        )
    if bill and bill.project_id != advance.project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Labour bill project does not match advance project",
        )

    recovery_amount = Decimal(str(payload.amount))
    if recovery_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recovery amount must be greater than 0",
        )

    balance_before = Decimal(str(advance.balance_amount or 0))
    if recovery_amount > balance_before:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recovery amount cannot exceed balance_amount",
        )

    before_data = _serialize_advance(advance)

    recovery = LabourAdvanceRecovery(
        advance_id=advance.id,
        labour_bill_id=payload.labour_bill_id,
        recovery_date=payload.recovery_date,
        amount=recovery_amount,
        remarks=_normalize_optional_text(payload.remarks),
    )
    db.add(recovery)
    flush_with_conflict_handling(db, entity_name="Labour advance")

    advance.recovered_amount = Decimal(str(advance.recovered_amount or 0)) + recovery_amount
    advance.balance_amount = Decimal(str(advance.amount or 0)) - Decimal(
        str(advance.recovered_amount or 0)
    )
    if advance.balance_amount <= 0:
        advance.balance_amount = Decimal("0")
        advance.status = "closed"
    elif advance.status == "closed":
        advance.status = "active"

    flush_with_conflict_handling(db, entity_name="Labour advance")
    log_audit_event(
        db,
        entity_type="labour_advance",
        entity_id=advance.id,
        action="recovery",
        performed_by=current_user,
        before_data=before_data,
        after_data=_serialize_advance(advance),
        remarks=recovery.remarks or advance.advance_no,
    )
    commit_with_conflict_handling(db, entity_name="Labour advance")
    return get_labour_advance_or_404(db, advance.id)
