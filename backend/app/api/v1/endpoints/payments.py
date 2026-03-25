"""Payment endpoints."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.payment import (
    OutstandingBillOut,
    PaymentActionRequest,
    PaymentAllocationCreate,
    PaymentCreate,
    PaymentOut,
)
from app.services.payment_service import (
    allocate_payment,
    approve_payment,
    create_payment,
    get_payment_or_404,
    list_outstanding_bills,
    list_payments,
    release_payment,
)

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("/outstanding/ra-bills", response_model=List[OutstandingBillOut])
def list_ra_bill_outstandings(
    contract_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("payments:read")),
):
    return list_outstanding_bills(db, contract_id=contract_id)


@router.get("/", response_model=List[PaymentOut])
def list_all_payments(
    contract_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("payments:read")),
):
    return list_payments(db, contract_id=contract_id)


@router.post("/", response_model=PaymentOut, status_code=201)
def create_new_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("payments:create")),
):
    return create_payment(db, payload, current_user)


@router.get("/{payment_id}", response_model=PaymentOut)
def get_single_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("payments:read")),
):
    return get_payment_or_404(db, payment_id)


@router.post("/{payment_id}/approve", response_model=PaymentOut)
def approve_existing_payment(
    payment_id: int,
    payload: PaymentActionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("payments:approve")),
):
    return approve_payment(
        db,
        payment_id,
        current_user,
        remarks=payload.remarks if payload is not None else None,
    )


@router.post("/{payment_id}/release", response_model=PaymentOut)
def release_existing_payment(
    payment_id: int,
    payload: PaymentActionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("payments:release")),
):
    return release_payment(
        db,
        payment_id,
        current_user,
        remarks=payload.remarks if payload is not None else None,
    )


@router.post("/{payment_id}/allocate", response_model=PaymentOut)
def allocate_existing_payment(
    payment_id: int,
    allocations: List[PaymentAllocationCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("payments:allocate")),
):
    return allocate_payment(db, payment_id, allocations, current_user)
