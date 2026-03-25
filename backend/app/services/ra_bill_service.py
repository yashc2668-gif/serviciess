"""RA bill service helpers."""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.calculators.deduction_calculator import build_generate_deduction_payloads
from app.calculators.ra_bill_calculator import calculate_bill_totals
from app.core.logging import log_business_event
from app.models.contract import Contract
from app.models.deduction import Deduction
from app.models.ra_bill import RABill
from app.models.ra_bill_item import RABillItem
from app.models.ra_bill_status_log import RABillStatusLog
from app.models.user import User
from app.models.work_done import WorkDoneItem
from app.schemas.ra_bill import (
    DeductionCreate,
    RABillCreate,
    RABillGenerateRequest,
    RABillStatus,
)
from app.services.audit_service import log_audit_event, serialize_model, serialize_models
from app.services.deduction_service import build_deduction_models
from app.services.secured_advance_service import (
    apply_secured_advance_recoveries_for_bill,
    validate_secured_advance_recoveries_for_bill,
)

RA_BILL_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"submitted", "cancelled"},
    "submitted": {"verified", "rejected", "cancelled", "finance_hold"},
    "verified": {"approved", "rejected", "cancelled", "finance_hold"},
    "finance_hold": {"verified", "rejected", "cancelled"},
    "approved": {"partially_paid", "paid"},
    "partially_paid": {"partially_paid", "paid"},
    "rejected": set(),
    "cancelled": set(),
    "paid": set(),
}


def _validate_period(period_from, period_to) -> None:
    if period_from and period_to and period_from > period_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="period_from cannot be after period_to",
        )


def _get_contract_or_404(db: Session, contract_id: int) -> Contract:
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found",
        )
    return contract


def _get_ra_bill_query(db: Session):
    return db.query(RABill).options(
        joinedload(RABill.items),
        joinedload(RABill.deductions).joinedload(Deduction.secured_advance),
        joinedload(RABill.status_logs),
        joinedload(RABill.payment_allocations),
    )


def get_ra_bill_or_404(db: Session, bill_id: int) -> RABill:
    bill = _get_ra_bill_query(db).filter(RABill.id == bill_id).first()
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RA bill not found",
        )
    return bill


def list_ra_bills(db: Session, contract_id: int | None = None) -> list[RABill]:
    query = _get_ra_bill_query(db)
    if contract_id is not None:
        query = query.filter(RABill.contract_id == contract_id)
    return query.order_by(RABill.bill_no.desc(), RABill.id.desc()).all()


def _ensure_draft_bill(bill: RABill) -> None:
    if bill.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft RA bills can be modified",
        )


def validate_ra_bill_transition(
    current_status: str,
    target_status: RABillStatus,
    remarks: str | None = None,
) -> None:
    allowed_statuses = RA_BILL_ALLOWED_TRANSITIONS.get(current_status, set())
    if target_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot move RA bill from {current_status} to {target_status}",
        )
    if target_status == "rejected" and not (remarks or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Remarks are mandatory when rejecting an RA bill",
        )


def _append_status_log(
    bill: RABill,
    *,
    from_status: str | None,
    to_status: str,
    action: str,
    current_user: User,
    remarks: str | None = None,
) -> None:
    bill.status_logs.append(
        RABillStatusLog(
            ra_bill_id=bill.id,
            from_status=from_status,
            to_status=to_status,
            action=action,
            remarks=remarks,
            actor_user_id=current_user.id,
        )
    )


def _apply_transition_side_effects(
    bill: RABill,
    target_status: RABillStatus,
    current_user: User,
) -> None:
    if target_status == "approved":
        bill.approved_by = current_user.id
        bill.approved_at = datetime.now(timezone.utc)


def _next_bill_no(db: Session, contract_id: int) -> int:
    current = db.query(func.coalesce(func.max(RABill.bill_no), 0)).filter(
        RABill.contract_id == contract_id
    ).scalar()
    return int(current or 0) + 1


def _ensure_bill_no_unique(
    db: Session,
    contract_id: int,
    bill_no: int,
    exclude_bill_id: int | None = None,
) -> None:
    query = db.query(RABill).filter(
        RABill.contract_id == contract_id,
        RABill.bill_no == bill_no,
    )
    if exclude_bill_id is not None:
        query = query.filter(RABill.id != exclude_bill_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bill number already exists for this contract",
        )


def _deduction_payloads_from_models(deductions) -> list[DeductionCreate]:
    return [
        DeductionCreate(
            deduction_type=deduction.deduction_type,
            description=deduction.description,
            reason=deduction.reason,
            percentage=float(deduction.percentage) if deduction.percentage is not None else None,
            amount=0 if deduction.percentage is not None else float(deduction.amount),
            secured_advance_id=deduction.secured_advance_id,
            is_system_generated=deduction.is_system_generated,
        )
        for deduction in deductions
    ]


def _replace_deductions(
    bill: RABill,
    deductions: list[DeductionCreate],
    gross_amount,
) -> None:
    bill.deductions.clear()
    bill.deductions.extend(
        build_deduction_models(
            ra_bill_id=bill.id,
            gross_amount=gross_amount,
            deductions=deductions,
        )
    )


def _build_default_generation_payload(bill: RABill) -> RABillGenerateRequest:
    if bill.deductions:
        return RABillGenerateRequest(
            apply_contract_retention=False,
            deductions=_deduction_payloads_from_models(bill.deductions),
        )
    return RABillGenerateRequest()


def _bill_snapshot(bill: RABill) -> dict:
    return {
        "bill": serialize_model(bill),
        "items_count": len(bill.items),
        "deductions_count": len(bill.deductions),
    }


def _deduction_snapshot(bill: RABill) -> dict:
    return {
        "ra_bill_id": bill.id,
        "deductions": serialize_models(list(bill.deductions)),
        "total_deductions": float(bill.total_deductions or 0),
        "net_payable": float(bill.net_payable or 0),
    }


def create_ra_bill_draft(db: Session, payload: RABillCreate, current_user: User) -> RABill:
    _get_contract_or_404(db, payload.contract_id)
    _validate_period(payload.period_from, payload.period_to)

    bill_no = payload.bill_no or _next_bill_no(db, payload.contract_id)
    _ensure_bill_no_unique(db, payload.contract_id, bill_no)

    bill = RABill(
        contract_id=payload.contract_id,
        bill_no=bill_no,
        bill_date=payload.bill_date,
        period_from=payload.period_from,
        period_to=payload.period_to,
        remarks=payload.remarks,
        status="draft",
    )
    db.add(bill)
    db.flush()

    _replace_deductions(bill, payload.deductions, gross_amount=0)
    totals = calculate_bill_totals([], bill.deductions)
    bill.gross_amount = totals["gross_amount"]
    bill.total_deductions = totals["total_deductions"]
    bill.net_payable = totals["net_payable"]
    _append_status_log(
        bill,
        from_status=None,
        to_status="draft",
        action="create",
        current_user=current_user,
        remarks=payload.remarks,
    )
    if bill.deductions:
        log_audit_event(
            db,
            entity_type="deduction",
            entity_id=bill.id,
            action="change",
            performed_by=current_user,
            after_data=_deduction_snapshot(bill),
            remarks=f"Initial deductions for RA Bill {bill.bill_no}",
        )

    db.commit()
    db.refresh(bill)
    return get_ra_bill_or_404(db, bill.id)


def _billed_work_done_ids_query(db: Session, bill: RABill):
    query = (
        db.query(RABillItem.work_done_item_id)
        .join(RABill, RABill.id == RABillItem.ra_bill_id)
        .filter(
            RABill.contract_id == bill.contract_id,
            RABill.id != bill.id,
            RABill.status != "rejected",
        )
    )
    return [row[0] for row in query.all()]


def generate_ra_bill_items(
    db: Session,
    bill_id: int,
    current_user: User,
    payload: RABillGenerateRequest | None = None,
) -> RABill:
    bill = get_ra_bill_or_404(db, bill_id)
    _ensure_draft_bill(bill)
    _validate_period(bill.period_from, bill.period_to)
    had_existing_items = bool(bill.items)
    contract = _get_contract_or_404(db, bill.contract_id)
    before_bill_data = _bill_snapshot(bill)
    before_deduction_data = _deduction_snapshot(bill)

    excluded_work_done_ids = _billed_work_done_ids_query(db, bill)
    work_done_query = (
        db.query(WorkDoneItem)
        .options(joinedload(WorkDoneItem.boq_item))
        .filter(WorkDoneItem.contract_id == bill.contract_id)
    )
    if bill.period_from is not None:
        work_done_query = work_done_query.filter(WorkDoneItem.recorded_date >= bill.period_from)
    if bill.period_to is not None:
        work_done_query = work_done_query.filter(WorkDoneItem.recorded_date <= bill.period_to)
    if excluded_work_done_ids:
        work_done_query = work_done_query.filter(~WorkDoneItem.id.in_(excluded_work_done_ids))
    work_done_entries = work_done_query.order_by(
        WorkDoneItem.recorded_date.asc(),
        WorkDoneItem.id.asc(),
    ).all()

    bill.items.clear()
    db.flush()
    for entry in work_done_entries:
        bill.items.append(
            RABillItem(
                ra_bill_id=bill.id,
                work_done_item_id=entry.id,
                measurement_id=entry.measurement_id,
                boq_item_id=entry.boq_item_id,
                item_code_snapshot=entry.boq_item.item_code if entry.boq_item else None,
                description_snapshot=entry.boq_item.description if entry.boq_item else "",
                unit_snapshot=entry.boq_item.unit if entry.boq_item else "",
                prev_quantity=entry.previous_quantity,
                curr_quantity=entry.current_quantity,
                cumulative_quantity=entry.cumulative_quantity,
                rate=entry.rate,
                amount=entry.amount,
            )
        )

    generation_payload = payload or _build_default_generation_payload(bill)
    deduction_payloads = build_generate_deduction_payloads(contract, generation_payload)
    totals = calculate_bill_totals(bill.items, deduction_payloads)
    _replace_deductions(bill, deduction_payloads, totals["gross_amount"])
    validate_secured_advance_recoveries_for_bill(db, bill)
    totals = calculate_bill_totals(bill.items, bill.deductions)
    bill.gross_amount = totals["gross_amount"]
    bill.total_deductions = totals["total_deductions"]
    bill.net_payable = totals["net_payable"]
    action = "recalculate" if had_existing_items else "generate"
    log_audit_event(
        db,
        entity_type="ra_bill",
        entity_id=bill.id,
        action=action,
        performed_by=current_user,
        before_data=before_bill_data,
        after_data=_bill_snapshot(bill),
        remarks=f"RA Bill {bill.bill_no}",
    )
    log_audit_event(
        db,
        entity_type="deduction",
        entity_id=bill.id,
        action="change",
        performed_by=current_user,
        before_data=before_deduction_data,
        after_data=_deduction_snapshot(bill),
        remarks=f"Deductions updated for RA Bill {bill.bill_no}",
    )

    db.commit()
    db.refresh(bill)
    log_business_event(
        "ra_bill.generated",
        bill_id=bill.id,
        contract_id=bill.contract_id,
        bill_no=bill.bill_no,
        status=bill.status,
        items_count=len(bill.items),
        gross_amount=float(bill.gross_amount or 0),
        net_payable=float(bill.net_payable or 0),
    )
    return get_ra_bill_or_404(db, bill.id)


def submit_ra_bill(db: Session, bill_id: int, current_user: User, remarks: str | None = None) -> RABill:
    bill = get_ra_bill_or_404(db, bill_id)
    _ensure_draft_bill(bill)
    if not bill.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Generate RA bill items before submitting the bill",
        )

    totals = calculate_bill_totals(bill.items, bill.deductions)
    bill.gross_amount = totals["gross_amount"]
    bill.total_deductions = totals["total_deductions"]
    bill.net_payable = totals["net_payable"]
    bill.submitted_by = current_user.id
    bill.submitted_at = datetime.now(timezone.utc)
    if remarks is not None:
        bill.remarks = remarks
    previous_status = bill.status
    before_data = _bill_snapshot(bill)
    bill.status = "submitted"
    _append_status_log(
        bill,
        from_status=previous_status,
        to_status="submitted",
        action="submit",
        current_user=current_user,
        remarks=remarks,
    )
    log_audit_event(
        db,
        entity_type="ra_bill",
        entity_id=bill.id,
        action="submit",
        performed_by=current_user,
        before_data=before_data,
        after_data=_bill_snapshot(bill),
        remarks=remarks,
    )

    db.commit()
    db.refresh(bill)
    log_business_event(
        "ra_bill.submitted",
        bill_id=bill.id,
        contract_id=bill.contract_id,
        bill_no=bill.bill_no,
        status=bill.status,
        net_payable=float(bill.net_payable or 0),
    )
    return get_ra_bill_or_404(db, bill.id)


def transition_ra_bill_status(
    db: Session,
    bill_id: int,
    target_status: RABillStatus,
    current_user: User,
    remarks: str | None = None,
    action: str | None = None,
) -> RABill:
    bill = get_ra_bill_or_404(db, bill_id)
    validate_ra_bill_transition(bill.status, target_status, remarks)

    previous_status = bill.status
    before_data = _bill_snapshot(bill)
    bill.status = target_status
    if remarks is not None:
        bill.remarks = remarks
    _apply_transition_side_effects(bill, target_status, current_user)
    if target_status == "approved":
        apply_secured_advance_recoveries_for_bill(db, bill, current_user)
    _append_status_log(
        bill,
        from_status=previous_status,
        to_status=target_status,
        action=action or target_status,
        current_user=current_user,
        remarks=remarks,
    )
    log_audit_event(
        db,
        entity_type="ra_bill",
        entity_id=bill.id,
        action=action or target_status,
        performed_by=current_user,
        before_data=before_data,
        after_data=_bill_snapshot(bill),
        remarks=remarks,
    )

    db.commit()
    db.refresh(bill)
    log_business_event(
        "ra_bill.transitioned",
        bill_id=bill.id,
        contract_id=bill.contract_id,
        bill_no=bill.bill_no,
        from_status=previous_status,
        to_status=target_status,
        net_payable=float(bill.net_payable or 0),
    )
    return get_ra_bill_or_404(db, bill.id)


def sync_ra_bill_payment_status(
    db: Session,
    bill: RABill,
    current_user: User,
    remarks: str | None = None,
) -> None:
    outstanding_amount = Decimal(str(bill.outstanding_amount or 0))
    net_payable = Decimal(str(bill.net_payable or 0))

    if outstanding_amount <= 0 and bill.status != "paid":
        previous_status = bill.status
        bill.status = "paid"
        _append_status_log(
            bill,
            from_status=previous_status,
            to_status="paid",
            action="paid",
            current_user=current_user,
            remarks=remarks,
        )
    elif Decimal("0") < outstanding_amount < net_payable and bill.status == "approved":
        previous_status = bill.status
        bill.status = "partially_paid"
        _append_status_log(
            bill,
            from_status=previous_status,
            to_status="partially_paid",
            action="partially_paid",
            current_user=current_user,
            remarks=remarks,
        )
