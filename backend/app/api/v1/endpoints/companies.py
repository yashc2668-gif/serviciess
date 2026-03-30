"""Company endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.company import CompanyCreate, CompanyOut, CompanyUpdate
from app.services.company_service import (
    create_company,
    get_company_or_404,
    list_companies,
    update_company,
)
from app.utils.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.get("/", response_model=PaginatedResponse[CompanyOut])
def list_all_companies(
    search: str | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("companies:read")),
):
    return list_companies(db, current_user=current_user, pagination=pagination, search=search)


@router.post("/", response_model=CompanyOut, status_code=201)
def create_new_company(
    payload: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("companies:create")),
):
    return create_company(db, payload, current_user)


@router.get("/{company_id}", response_model=CompanyOut)
def get_single_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("companies:read")),
):
    return get_company_or_404(db, company_id, current_user=current_user)


@router.put("/{company_id}", response_model=CompanyOut)
def update_existing_company(
    company_id: int,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("companies:update")),
):
    return update_company(db, company_id, payload, current_user)
