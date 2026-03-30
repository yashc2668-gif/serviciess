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
from app.services.company_scope_service import (
    apply_contract_company_scope,
    apply_payment_company_scope,
    apply_ra_bill_company_scope,
    resolve_company_scope,
)
from app.services.concurrency_service import (
    apply_write_lock,
    commit_with_conflict_handling,
    ensure_lock_version_matches,
    flush_with_conflict_handling,
    touch_rows,
)
from app.services.ra_bill_service import get_ra_bill_or_404, sync_ra_bill_payment_status
from app.utils.pagination import PaginationParams, paginate_query, paginate_sequence


def _get_contract_or_404(db: Session, contract_id: int, *, current_user: User) -> Contract:
    contract = (
        apply_contract_company_scope(
            db.query(Contract).filter(Contract.is_deleted.is_(False)),
            resolve_company_scope(current_user),
        )
        .filter(Contract.id == contract_id)
        .first()
    )
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found",
        )
    return contract


def get_payment_or_404(
    db: Session,
    payment_id: int,
    *,
    current_user: User,
    lock_for_update: bool = False,
) -> Payment:
    query = (
        apply_payment_company_scope(
            db.query(Payment)
        .options(joinedload(Payment.allocations))
            .filter(Payment.is_archived.is_(False)),
            resolve_company_scope(current_user),
        )
        .filter(Payment.id == payment_id)
    )
    if lock_for_update:
        query = apply_write_lock(query, db)
    payment = query.first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    return payment


def _get_ra_bill_or_404(
    db: Session,
    ra_bill_id: int,
    *,
    current_user: User,
    lock_for_update: bool = False,
) -> RABill:
    return get_ra_bill_or_404(
        db,
        ra_bill_id,
        current_user=current_user,
        lock_for_update=lock_for_update,
    )


def _load_ra_bills_for_allocation(
    db: Session,
    ra_bill_ids: list[int],
    *,
    current_user: User,
) -> list[RABill]:
    unique_ids = list(dict.fromkeys(ra_bill_ids))
    bills = (
        apply_write_lock(
            apply_ra_bill_company_scope(
                db.query(RABill)
                .options(joinedload(RABill.payment_allocations))
                .filter(RABill.is_archived.is_(False), RABill.id.in_(unique_ids)),
                resolve_company_scope(current_user),
            ),
            db,
        )
        .order_by(RABill.id.asc())
        .all()
    )
    bill_map = {bill.id: bill for bill in bills}
    missing_ids = [bill_id for bill_id in unique_ids if bill_id not in bill_map]
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RA bill not found for id(s): {', '.join(map(str, missing_ids))}",
        )
    return [bill_map[bill_id] for bill_id in unique_ids]


def create_payment(db: Session, payload: PaymentCreate, current_user: User) -> Payment:
    _get_contract_or_404(db, payload.contract_id, current_user=current_user)
    if payload.ra_bill_id is not None:
        bill = _get_ra_bill_or_404(db, payload.ra_bill_id, current_user=current_user)
        if bill.contract_id != payload.contract_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="RA bill does not belong to the selected contract",
            )

    payment = Payment(**payload.model_dump(exclude_none=True), status="draft")
    db.add(payment)
    flush_with_conflict_handling(db, entity_name="Payment")
    log_audit_event(
        db,
        entity_type="payment",
        entity_id=payment.id,
        action="create",
        performed_by=current_user,
        after_data=serialize_model(payment),
        remarks=payload.remarks,
    )
    commit_with_conflict_handling(db, entity_name="Payment")
    db.refresh(payment)
    log_business_event(
        "payment.created",
        payment_id=payment.id,
        contract_id=payment.contract_id,
        amount=float(payment.amount or 0),
        status=payment.status,
    )
    return get_payment_or_404(db, payment.id, current_user=current_user)


def approve_payment(
    db: Session,
    payment_id: int,
    current_user: User,
    *,
    expected_lock_version: int | None = None,
    remarks: str | None = None,
) -> Payment:
    payment = get_payment_or_404(db, payment_id, current_user=current_user, lock_for_update=True)
    ensure_lock_version_matches(
        payment,
        expected_lock_version,
        entity_name="Payment",
    )
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
    flush_with_conflict_handling(db, entity_name="Payment")
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
    commit_with_conflict_handling(db, entity_name="Payment")
    db.refresh(payment)
    log_business_event(
        "payment.approved",
        payment_id=payment.id,
        contract_id=payment.contract_id,
        amount=float(payment.amount or 0),
        status=payment.status,
    )
    return get_payment_or_404(db, payment.id, current_user=current_user)


def release_payment(
    db: Session,
    payment_id: int,
    current_user: User,
    *,
    expected_lock_version: int | None = None,
    remarks: str | None = None,
) -> Payment:
    payment = get_payment_or_404(db, payment_id, current_user=current_user, lock_for_update=True)
    ensure_lock_version_matches(
        payment,
        expected_lock_version,
        entity_name="Payment",
    )
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
    flush_with_conflict_handling(db, entity_name="Payment")
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
    commit_with_conflict_handling(db, entity_name="Payment")
    db.refresh(payment)
    log_business_event(
        "payment.released",
        payment_id=payment.id,
        contract_id=payment.contract_id,
        amount=float(payment.amount or 0),
        status=payment.status,
    )
    return get_payment_or_404(db, payment.id, current_user=current_user)


def allocate_payment(
    db: Session,
    payment_id: int,
    allocations: list[PaymentAllocationCreate],
    current_user: User,
) -> Payment:
    payment = get_payment_or_404(db, payment_id, current_user=current_user, lock_for_update=True)
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

    requested_by_bill: dict[int, Decimal] = {}
    for allocation in allocations:
        requested_by_bill.setdefault(allocation.ra_bill_id, Decimal("0"))
        requested_by_bill[allocation.ra_bill_id] += Decimal(str(allocation.amount))

    bills = _load_ra_bills_for_allocation(
        db,
        list(requested_by_bill.keys()),
        current_user=current_user,
    )
    bill_map = {bill.id: bill for bill in bills}
    touch_rows(payment, bills)

    for bill_id, requested_amount in requested_by_bill.items():
        bill = bill_map[bill_id]
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
        if requested_amount > outstanding_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Allocation exceeds outstanding amount for RA bill {bill.id}",
            )

    for allocation in allocations:
        bill = bill_map[allocation.ra_bill_id]
        bill.payment_allocations.append(
            PaymentAllocation(
                payment_id=payment.id,
                ra_bill_id=bill.id,
                amount=Decimal(str(allocation.amount)),
                remarks=allocation.remarks,
            )
        )
    flush_with_conflict_handling(db, entity_name="Payment")

    for bill in bills:
        sync_ra_bill_payment_status(
            db,
            bill,
            current_user,
            remarks=f"Payment allocation from payment {payment.id}",
        )
    flush_with_conflict_handling(db, entity_name="Payment")

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
    commit_with_conflict_handling(db, entity_name="Payment")
    db.refresh(payment)
    log_business_event(
        "payment.allocated",
        payment_id=payment.id,
        contract_id=payment.contract_id,
        status=payment.status,
        allocations_count=len(payment.allocations),
        allocated_amount=float(sum((allocation.amount for allocation in payment.allocations), Decimal("0"))),
    )
    return get_payment_or_404(db, payment.id, current_user=current_user)


def list_payments(
    db: Session,
    current_user: User,
    contract_id: int | None = None,
    *,
    pagination: PaginationParams,
) -> dict[str, object]:
    query = apply_payment_company_scope(
        db.query(Payment)
        .options(joinedload(Payment.allocations))
        .filter(Payment.is_archived.is_(False)),
        resolve_company_scope(current_user),
    )
    if contract_id is not None:
        query = query.filter(Payment.contract_id == contract_id)
    return paginate_query(
        query.order_by(Payment.created_at.desc(), Payment.id.desc()),
        pagination=pagination,
    )


def list_outstanding_bills(
    db: Session,
    current_user: User,
    contract_id: int | None = None,
    *,
    pagination: PaginationParams,
) -> dict[str, object]:
    query = apply_ra_bill_company_scope(
        db.query(RABill)
        .options(joinedload(RABill.payment_allocations))
        .filter(RABill.is_archived.is_(False)),
        resolve_company_scope(current_user),
    )
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
    return paginate_sequence(results, pagination=pagination)
