"""Payment endpoints."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
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
from app.utils.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("/outstanding/ra-bills", response_model=PaginatedResponse[OutstandingBillOut])
def list_ra_bill_outstandings(
    contract_id: int | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("payments:read")),
):
    return list_outstanding_bills(
        db,
        current_user=current_user,
        contract_id=contract_id,
        pagination=pagination,
    )


@router.get("/", response_model=PaginatedResponse[PaymentOut])
def list_all_payments(
    contract_id: int | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("payments:read")),
):
    return list_payments(
        db,
        current_user=current_user,
        contract_id=contract_id,
        pagination=pagination,
    )


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
    current_user: User = Depends(require_permissions("payments:read")),
):
    return get_payment_or_404(db, payment_id, current_user=current_user)


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
        expected_lock_version=payload.lock_version if payload is not None else None,
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
        expected_lock_version=payload.lock_version if payload is not None else None,
        remarks=payload.remarks if payload is not None else None,
    )


@router.post("/{payment_id}/allocate", response_model=PaymentOut)
def allocate_existing_payment(
    payment_id: int,
    allocations: list[PaymentAllocationCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("payments:allocate")),
):
    return allocate_payment(db, payment_id, allocations, current_user)


@router.get("/{payment_id}/pdf")
def download_payment_pdf(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("payments:read")),
):
    import io

    from app.services.pdf_service import generate_payment_voucher_pdf

    payment = get_payment_or_404(db, payment_id, current_user=current_user)
    contract = payment.contract
    project = contract.project
    vendor = contract.vendor

    pdf_bytes = generate_payment_voucher_pdf(payment, contract, project, vendor)
    filename = f"Payment_Voucher_{payment.id}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
