"""RA bill endpoints."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.ra_bill import (
    RABillCreate,
    RABillGenerateRequest,
    RABillOut,
    RABillSubmitRequest,
    RABillTransitionRequest,
)
from app.services.ra_bill_service import (
    create_ra_bill_draft,
    generate_ra_bill_items,
    get_ra_bill_or_404,
    list_ra_bills,
    submit_ra_bill,
    transition_ra_bill_status,
)
from app.utils.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/ra-bills", tags=["RA Bills"])


@router.get("/", response_model=PaginatedResponse[RABillOut])
def list_all_ra_bills(
    contract_id: int | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("ra_bills:read")),
):
    return list_ra_bills(
        db,
        current_user=current_user,
        contract_id=contract_id,
        pagination=pagination,
    )


@router.post("/", response_model=RABillOut, status_code=201)
def create_new_ra_bill(
    payload: RABillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("ra_bills:create")),
):
    return create_ra_bill_draft(db, payload, current_user)


@router.get("/{bill_id}", response_model=RABillOut)
def get_single_ra_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("ra_bills:read")),
):
    return get_ra_bill_or_404(db, bill_id, current_user=current_user)


@router.post("/{bill_id}/generate", response_model=RABillOut)
def generate_items_for_bill(
    bill_id: int,
    payload: RABillGenerateRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("ra_bills:create")),
):
    return generate_ra_bill_items(db, bill_id, current_user, payload)


@router.post("/{bill_id}/submit", response_model=RABillOut)
def submit_existing_ra_bill(
    bill_id: int,
    payload: RABillSubmitRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("ra_bills:submit")),
):
    return submit_ra_bill(
        db,
        bill_id,
        current_user,
        expected_lock_version=payload.lock_version if payload is not None else None,
        remarks=payload.remarks if payload is not None else None,
    )


@router.post("/{bill_id}/verify", response_model=RABillOut)
def verify_existing_ra_bill(
    bill_id: int,
    payload: RABillTransitionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("ra_bills:verify")),
):
    return transition_ra_bill_status(
        db,
        bill_id,
        "verified",
        current_user,
        expected_lock_version=payload.lock_version if payload is not None else None,
        remarks=payload.remarks if payload is not None else None,
        action="verify",
    )


@router.post("/{bill_id}/approve", response_model=RABillOut)
def approve_existing_ra_bill(
    bill_id: int,
    payload: RABillTransitionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("ra_bills:approve")),
):
    return transition_ra_bill_status(
        db,
        bill_id,
        "approved",
        current_user,
        expected_lock_version=payload.lock_version if payload is not None else None,
        remarks=payload.remarks if payload is not None else None,
        action="approve",
    )


@router.post("/{bill_id}/reject", response_model=RABillOut)
def reject_existing_ra_bill(
    bill_id: int,
    payload: RABillTransitionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("ra_bills:reject")),
):
    return transition_ra_bill_status(
        db,
        bill_id,
        "rejected",
        current_user,
        expected_lock_version=payload.lock_version if payload is not None else None,
        remarks=payload.remarks if payload is not None else None,
        action="reject",
    )


@router.post("/{bill_id}/cancel", response_model=RABillOut)
def cancel_existing_ra_bill(
    bill_id: int,
    payload: RABillTransitionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("ra_bills:cancel")),
):
    return transition_ra_bill_status(
        db,
        bill_id,
        "cancelled",
        current_user,
        expected_lock_version=payload.lock_version if payload is not None else None,
        remarks=payload.remarks if payload is not None else None,
        action="cancel",
    )


@router.post("/{bill_id}/finance-hold", response_model=RABillOut)
def put_ra_bill_on_finance_hold(
    bill_id: int,
    payload: RABillTransitionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("ra_bills:finance_hold")),
):
    return transition_ra_bill_status(
        db,
        bill_id,
        "finance_hold",
        current_user,
        expected_lock_version=payload.lock_version if payload is not None else None,
        remarks=payload.remarks if payload is not None else None,
        action="finance_hold",
    )


@router.post("/{bill_id}/partially-paid", response_model=RABillOut)
def mark_ra_bill_partially_paid(
    bill_id: int,
    payload: RABillTransitionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("ra_bills:partially_paid")),
):
    return transition_ra_bill_status(
        db,
        bill_id,
        "partially_paid",
        current_user,
        expected_lock_version=payload.lock_version if payload is not None else None,
        remarks=payload.remarks if payload is not None else None,
        action="partially_paid",
    )


@router.post("/{bill_id}/paid", response_model=RABillOut)
def mark_ra_bill_paid(
    bill_id: int,
    payload: RABillTransitionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("ra_bills:paid")),
):
    return transition_ra_bill_status(
        db,
        bill_id,
        "paid",
        current_user,
        expected_lock_version=payload.lock_version if payload is not None else None,
        remarks=payload.remarks if payload is not None else None,
        action="paid",
    )


@router.get("/{bill_id}/pdf")
def download_ra_bill_pdf(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("ra_bills:read")),
):
    import io

    from app.services.pdf_service import generate_ra_bill_pdf

    bill = get_ra_bill_or_404(db, bill_id, current_user=current_user)
    contract = bill.contract
    project = contract.project
    vendor = contract.vendor

    pdf_bytes = generate_ra_bill_pdf(bill, contract, project, vendor)
    filename = f"RA_Bill_{bill.bill_no}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
