"""Labour bill endpoints."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.labour_bill import (
    LabourBillCreate,
    LabourBillOut,
    LabourBillTransitionRequest,
    LabourBillUpdate,
)
from app.services.labour_bill_service import (
    create_labour_bill,
    get_labour_bill_or_404,
    list_labour_bills,
    update_labour_bill,
)
from app.utils.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/labour-bills", tags=["Labour Bills"])


@router.get("", response_model=PaginatedResponse[LabourBillOut])
@router.get("/", response_model=PaginatedResponse[LabourBillOut], include_in_schema=False)
def list_all_labour_bills(
    project_id: int | None = None,
    contract_id: int | None = None,
    contractor_id: int | None = None,
    status: str | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour_bills:read")),
):
    return list_labour_bills(
        db,
        current_user=current_user,
        pagination=pagination,
        project_id=project_id,
        contract_id=contract_id,
        contractor_id=contractor_id,
        status_filter=status,
    )


@router.post("", response_model=LabourBillOut, status_code=201)
@router.post("/", response_model=LabourBillOut, status_code=201, include_in_schema=False)
def create_new_labour_bill(
    payload: LabourBillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour_bills:create")),
):
    return create_labour_bill(db, payload, current_user)


@router.get("/{bill_id}", response_model=LabourBillOut)
def get_single_labour_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("labour_bills:read")),
):
    return get_labour_bill_or_404(db, bill_id)


@router.put("/{bill_id}", response_model=LabourBillOut)
def update_existing_labour_bill(
    bill_id: int,
    payload: LabourBillUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour_bills:approve")),
):
    return update_labour_bill(db, bill_id, payload, current_user)


@router.post("/{bill_id}/approve", response_model=LabourBillOut)
def approve_existing_labour_bill(
    bill_id: int,
    payload: LabourBillTransitionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour_bills:approve")),
):
    update_payload: dict = {"status": "approved"}
    if payload is not None and payload.remarks is not None:
        update_payload["remarks"] = payload.remarks
    return update_labour_bill(db, bill_id, LabourBillUpdate(**update_payload), current_user)


@router.post("/{bill_id}/mark-paid", response_model=LabourBillOut)
def mark_existing_labour_bill_paid(
    bill_id: int,
    payload: LabourBillTransitionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour_bills:approve")),
):
    update_payload: dict = {"status": "paid"}
    if payload is not None and payload.remarks is not None:
        update_payload["remarks"] = payload.remarks
    return update_labour_bill(db, bill_id, LabourBillUpdate(**update_payload), current_user)


@router.get("/{bill_id}/pdf")
def download_labour_bill_pdf(
    bill_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("labour_bills:read")),
):
    import io

    from app.services.pdf_service import generate_labour_bill_pdf

    bill = get_labour_bill_or_404(db, bill_id)
    contractor = bill.contractor
    project = bill.project
    contract = bill.contract  # may be None

    pdf_bytes = generate_labour_bill_pdf(bill, contractor, project, contract)
    filename = f"Labour_Bill_{bill.bill_no}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
