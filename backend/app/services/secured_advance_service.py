"""Secured advance service helpers."""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.contract import Contract
from app.models.secured_advance import SecuredAdvance
from app.models.secured_advance_recovery import SecuredAdvanceRecovery
from app.models.user import User
from app.schemas.secured_advance import SecuredAdvanceIssueCreate, SecuredAdvanceUpdate
from app.services.audit_service import log_audit_event, serialize_model


def _get_contract_or_404(db: Session, contract_id: int) -> Contract:
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found",
        )
    return contract


def get_secured_advance_or_404(db: Session, secured_advance_id: int) -> SecuredAdvance:
    advance = (
        db.query(SecuredAdvance)
        .options(joinedload(SecuredAdvance.recoveries))
        .filter(SecuredAdvance.id == secured_advance_id)
        .first()
    )
    if not advance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Secured advance not found",
        )
    return advance


def list_secured_advances(db: Session, contract_id: int | None = None) -> list[SecuredAdvance]:
    query = db.query(SecuredAdvance).options(joinedload(SecuredAdvance.recoveries))
    if contract_id is not None:
        query = query.filter(SecuredAdvance.contract_id == contract_id)
    return query.order_by(SecuredAdvance.advance_date.desc(), SecuredAdvance.id.desc()).all()


def list_secured_advance_recoveries(
    db: Session,
    secured_advance_id: int,
) -> list[SecuredAdvanceRecovery]:
    get_secured_advance_or_404(db, secured_advance_id)
    return (
        db.query(SecuredAdvanceRecovery)
        .filter(SecuredAdvanceRecovery.secured_advance_id == secured_advance_id)
        .order_by(SecuredAdvanceRecovery.recovery_date.asc(), SecuredAdvanceRecovery.id.asc())
        .all()
    )


def issue_secured_advance(
    db: Session,
    payload: SecuredAdvanceIssueCreate,
    current_user: User,
) -> SecuredAdvance:
    _get_contract_or_404(db, payload.contract_id)
    amount = Decimal(str(payload.advance_amount))
    advance = SecuredAdvance(
        contract_id=payload.contract_id,
        advance_date=payload.advance_date,
        description=payload.description,
        advance_amount=amount,
        recovered_amount=Decimal("0"),
        balance=amount,
        status="active",
        issued_by=current_user.id,
    )
    db.add(advance)
    db.flush()
    log_audit_event(
        db,
        entity_type="secured_advance",
        entity_id=advance.id,
        action="issue",
        performed_by=current_user,
        after_data=serialize_model(advance),
        remarks=advance.description,
    )
    db.commit()
    db.refresh(advance)
    return get_secured_advance_or_404(db, advance.id)


def update_secured_advance(
    db: Session,
    secured_advance_id: int,
    payload: SecuredAdvanceUpdate,
    current_user: User,
) -> SecuredAdvance:
    advance = get_secured_advance_or_404(db, secured_advance_id)
    updates = payload.model_dump(exclude_unset=True, mode="json")
    before_data = serialize_model(advance)
    for field, value in updates.items():
        setattr(advance, field, value)
    db.flush()
    log_audit_event(
        db,
        entity_type="secured_advance",
        entity_id=advance.id,
        action="update",
        performed_by=current_user,
        before_data=before_data,
        after_data=serialize_model(advance),
    )
    db.commit()
    db.refresh(advance)
    return get_secured_advance_or_404(db, advance.id)


def validate_secured_advance_recoveries_for_bill(db: Session, bill) -> None:
    requested_by_advance: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))

    for deduction in bill.deductions:
        if not deduction.secured_advance_id:
            continue
        requested_by_advance[deduction.secured_advance_id] += Decimal(str(deduction.amount or 0))

    for secured_advance_id, requested in requested_by_advance.items():
        advance = get_secured_advance_or_404(db, secured_advance_id)
        available = Decimal(str(advance.balance or 0))
        if requested > available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Secured advance {secured_advance_id} recovery exceeds available balance "
                    f"({float(requested)} > {float(available)})"
                ),
            )


def apply_secured_advance_recoveries_for_bill(
    db: Session,
    bill,
    current_user: User,
) -> None:
    existing = (
        db.query(SecuredAdvanceRecovery)
        .filter(SecuredAdvanceRecovery.ra_bill_id == bill.id)
        .count()
    )
    if existing:
        return

    validate_secured_advance_recoveries_for_bill(db, bill)

    for deduction in bill.deductions:
        if not deduction.secured_advance_id:
            continue

        advance = deduction.secured_advance
        before_data = serialize_model(advance)
        recovery_amount = Decimal(str(deduction.amount or 0))
        advance.recovered_amount = Decimal(str(advance.recovered_amount or 0)) + recovery_amount
        advance.balance = Decimal(str(advance.advance_amount or 0)) - Decimal(
            str(advance.recovered_amount or 0)
        )
        if advance.balance <= 0:
            advance.balance = Decimal("0")
            advance.status = "fully_recovered"
        elif advance.status == "written_off":
            advance.status = "written_off"
        else:
            advance.status = "active"

        recovery = SecuredAdvanceRecovery(
            secured_advance_id=advance.id,
            ra_bill_id=bill.id,
            recovery_date=bill.bill_date or date.today(),
            amount=recovery_amount,
            remarks=deduction.reason or deduction.description,
            created_by=current_user.id,
        )
        db.add(recovery)
        db.flush()
        log_audit_event(
            db,
            entity_type="secured_advance",
            entity_id=advance.id,
            action="recovery",
            performed_by=current_user,
            before_data=before_data,
            after_data={
                "secured_advance": serialize_model(advance),
                "recovery": serialize_model(recovery),
            },
            remarks=recovery.remarks,
        )
