"""Site expense endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.site_expense import (
    SiteExpenseActionRequest,
    SiteExpenseCreate,
    SiteExpenseOut,
    SiteExpenseStatus,
    SiteExpenseUpdate,
)
from app.services.site_expense_service import (
    approve_site_expense,
    create_site_expense,
    get_site_expense_or_404,
    list_site_expenses,
    mark_site_expense_paid,
    update_site_expense,
)
from app.utils.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/site-expenses", tags=["Site Expenses"])


@router.get("/", response_model=PaginatedResponse[SiteExpenseOut])
def list_all_site_expenses(
    project_id: int | None = None,
    status_filter: SiteExpenseStatus | None = None,
    expense_head: str | None = None,
    search: str | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("site_expenses:read")),
):
    return list_site_expenses(
        db,
        current_user=current_user,
        pagination=pagination,
        project_id=project_id,
        status_filter=status_filter,
        expense_head=expense_head,
        search=search,
    )


@router.post("/", response_model=SiteExpenseOut, status_code=201)
def create_new_site_expense(
    payload: SiteExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("site_expenses:create")),
):
    return create_site_expense(db, payload, current_user)


@router.get("/{expense_id}", response_model=SiteExpenseOut)
def get_single_site_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("site_expenses:read")),
):
    return get_site_expense_or_404(db, expense_id, current_user=current_user)


@router.put("/{expense_id}", response_model=SiteExpenseOut)
def update_existing_site_expense(
    expense_id: int,
    payload: SiteExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("site_expenses:update")),
):
    return update_site_expense(db, expense_id, payload, current_user)


@router.post("/{expense_id}/approve", response_model=SiteExpenseOut)
def approve_existing_site_expense(
    expense_id: int,
    payload: SiteExpenseActionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("site_expenses:approve")),
):
    return approve_site_expense(
        db,
        expense_id,
        current_user,
        expected_lock_version=payload.lock_version if payload is not None else None,
        remarks=payload.remarks if payload is not None else None,
    )


@router.post("/{expense_id}/pay", response_model=SiteExpenseOut)
def mark_existing_site_expense_paid(
    expense_id: int,
    payload: SiteExpenseActionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("site_expenses:pay")),
):
    return mark_site_expense_paid(
        db,
        expense_id,
        current_user,
        expected_lock_version=payload.lock_version if payload is not None else None,
        remarks=payload.remarks if payload is not None else None,
    )
