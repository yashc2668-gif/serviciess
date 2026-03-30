"""Deduction endpoints (read-only — deductions are created via RA Bills)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.contract import Contract
from app.models.deduction import Deduction
from app.models.project import Project
from app.models.ra_bill import RABill
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.deduction import DeductionOut
from app.services.company_scope_service import resolve_company_scope
from app.utils.pagination import PaginationParams, get_pagination_params, paginate_query

router = APIRouter(prefix="/deductions", tags=["Deductions"])


@router.get("/", response_model=PaginatedResponse[DeductionOut])
def list_deductions(
    ra_bill_id: int | None = Query(default=None, description="Filter by RA bill"),
    deduction_type: str | None = Query(default=None, description="Filter by type"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("ra_bills:read")),
):
    query = db.query(Deduction)
    company_id = resolve_company_scope(current_user)
    if company_id is not None:
        query = (
            query.join(RABill, Deduction.ra_bill_id == RABill.id)
            .join(Contract, RABill.contract_id == Contract.id)
            .join(Project, Contract.project_id == Project.id)
            .filter(Project.company_id == company_id)
        )
    if ra_bill_id is not None:
        query = query.filter(Deduction.ra_bill_id == ra_bill_id)
    if deduction_type is not None:
        query = query.filter(Deduction.deduction_type == deduction_type)
    query = query.order_by(Deduction.created_at.desc())
    return paginate_query(query, pagination=pagination)


@router.get("/{deduction_id}", response_model=DeductionOut)
def get_deduction(
    deduction_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("ra_bills:read")),
):
    from fastapi import HTTPException, status

    deduction = db.query(Deduction).filter(Deduction.id == deduction_id).first()
    if not deduction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deduction not found",
        )
    return deduction
