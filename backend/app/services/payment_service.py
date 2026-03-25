"""Payment service helpers."""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.logging import log_business_event
from app.models.contract import Contract
from app.models.payment import Payment
from app.models.payment_allocation import PaymentAllocation
from app.models.ra_bill import RABill
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentAllocationCreate
from app.services.audit_service import log_audit_event, serialize_model, serialize_models
from app.services.ra_bill_service import get_ra_bill_or_404, sync_ra_bill_payment_status


def _get_contract_or_404(db: Session, contract_id: int) -> Contract:
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found",
        )
    return contract


def get_payment_or_404(db: Session, payment_id: int) -> Payment:
    payment = (
        db.query(Payment)
        .options(joinedload(Payment.allocations))
        .filter(Payment.id == payment_id)
        .first()
    )
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    return payment


def _get_ra_bill_or_404(db: Session, ra_bill_id: int) -> RABill:
    return get_ra_bill_or_404(db, ra_bill_id)


def create_payment(db: Session, payload: PaymentCreate, current_user: User) -> Payment:
    _get_contract_or_404(db, payload.contract_id)
    if payload.ra_bill_id is not None:
        bill = _get_ra_bill_or_404(db, payload.ra_bill_id)
        if bill.contract_id != payload.contract_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="RA bill does not belong to the selected contract",
            )

    payment = Payment(**payload.model_dump(exclude_none=True), status="draft")
    db.add(payment)
    db.flush()
    log_audit_event(
        db,
        entity_type="payment",
        entity_id=payment.id,
        action="create",
        performed_by=current_user,
        after_data=serialize_model(payment),
        remarks=payload.remarks,
    )
    db.commit()
    db.refresh(payment)
    log_business_event(
        "payment.created",
        payment_id=payment.id,
        contract_id=payment.contract_id,
        amount=float(payment.amount or 0),
        status=payment.status,
    )
    return get_payment_or_404(db, payment.id)


def approve_payment(
    db: Session,
    payment_id: int,
    current_user: User,
    remarks: str | None = None,
) -> Payment:
    payment = get_payment_or_404(db, payment_id)
    if payment.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft payments can be approved",
        )

    before_data = serialize_model(payment)
    payment.status = "approved"
    payment.approved_by = current_user.id
    payment.approved_at = datetime.now(timezone.utc)
    if remarks is not None:
        payment.remarks = remarks
    db.flush()
    log_audit_event(
        db,
        entity_type="payment",
        entity_id=payment.id,
        action="approve",
        performed_by=current_user,
        before_data=before_data,
        after_data=serialize_model(payment),
        remarks=remarks,
    )
    db.commit()
    db.refresh(payment)
    log_business_event(
        "payment.approved",
        payment_id=payment.id,
        contract_id=payment.contract_id,
        amount=float(payment.amount or 0),
        status=payment.status,
    )
    return get_payment_or_404(db, payment.id)


def release_payment(
    db: Session,
    payment_id: int,
    current_user: User,
    remarks: str | None = None,
) -> Payment:
    payment = get_payment_or_404(db, payment_id)
    if payment.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only approved payments can be released",
        )

    before_data = serialize_model(payment)
    payment.status = "released"
    payment.released_by = current_user.id
    payment.released_at = datetime.now(timezone.utc)
    if remarks is not None:
        payment.remarks = remarks
    db.flush()
    log_audit_event(
        db,
        entity_type="payment",
        entity_id=payment.id,
        action="release",
        performed_by=current_user,
        before_data=before_data,
        after_data=serialize_model(payment),
        remarks=remarks,
    )
    db.commit()
    db.refresh(payment)
    log_business_event(
        "payment.released",
        payment_id=payment.id,
        contract_id=payment.contract_id,
        amount=float(payment.amount or 0),
        status=payment.status,
    )
    return get_payment_or_404(db, payment.id)


def allocate_payment(
    db: Session,
    payment_id: int,
    allocations: list[PaymentAllocationCreate],
    current_user: User,
) -> Payment:
    payment = get_payment_or_404(db, payment_id)
    if payment.status != "released":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only released payments can be allocated",
        )
    if not allocations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one allocation is required",
        )

    before_data = {
        "payment": serialize_model(payment),
        "allocations": serialize_models(payment.allocations),
    }
    requested_total = sum((Decimal(str(item.amount)) for item in allocations), Decimal("0"))
    if requested_total > Decimal(str(payment.available_amount)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Allocation amount exceeds available payment balance",
        )

    for allocation in allocations:
        bill = _get_ra_bill_or_404(db, allocation.ra_bill_id)
        if bill.contract_id != payment.contract_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="RA bill does not belong to the payment contract",
            )
        if bill.status not in {"approved", "partially_paid"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment can only be allocated to approved or partially paid RA bills",
            )
        outstanding_amount = Decimal(str(bill.outstanding_amount))
        if Decimal(str(allocation.amount)) > outstanding_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Allocation exceeds outstanding amount for RA bill {bill.id}",
            )

        bill.payment_allocations.append(
            PaymentAllocation(
                payment_id=payment.id,
                ra_bill_id=bill.id,
                amount=Decimal(str(allocation.amount)),
                remarks=allocation.remarks,
            )
        )
        db.flush()
        sync_ra_bill_payment_status(
            db,
            bill,
            current_user,
            remarks=allocation.remarks or f"Payment allocation from payment {payment.id}",
        )

    log_audit_event(
        db,
        entity_type="payment",
        entity_id=payment.id,
        action="allocate",
        performed_by=current_user,
        before_data=before_data,
        after_data={
            "payment": serialize_model(payment),
            "allocations": serialize_models(payment.allocations),
        },
    )
    db.commit()
    db.refresh(payment)
    log_business_event(
        "payment.allocated",
        payment_id=payment.id,
        contract_id=payment.contract_id,
        status=payment.status,
        allocations_count=len(payment.allocations),
        allocated_amount=float(sum((allocation.amount for allocation in payment.allocations), Decimal("0"))),
    )
    return get_payment_or_404(db, payment.id)


def list_payments(db: Session, contract_id: int | None = None) -> list[Payment]:
    query = db.query(Payment).options(joinedload(Payment.allocations))
    if contract_id is not None:
        query = query.filter(Payment.contract_id == contract_id)
    return query.order_by(Payment.created_at.desc(), Payment.id.desc()).all()


def list_outstanding_bills(db: Session, contract_id: int | None = None) -> list[dict]:
    query = db.query(RABill).options(joinedload(RABill.payment_allocations))
    if contract_id is not None:
        query = query.filter(RABill.contract_id == contract_id)
    query = query.filter(RABill.status.in_(["approved", "partially_paid"]))
    bills = query.order_by(RABill.bill_no.asc(), RABill.id.asc()).all()
    results: list[dict] = []
    for bill in bills:
        outstanding = Decimal(str(bill.outstanding_amount))
        if outstanding <= 0:
            continue
        results.append(
            {
                "ra_bill_id": bill.id,
                "bill_no": bill.bill_no,
                "status": bill.status,
                "net_payable": float(bill.net_payable or 0),
                "paid_amount": float(bill.paid_amount or 0),
                "outstanding_amount": float(outstanding),
            }
        )
    return results
