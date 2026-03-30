"""Company service helpers."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.services.audit_service import log_audit_event, serialize_model
from app.services.company_scope_service import resolve_company_scope
from app.utils.pagination import PaginationParams, paginate_query


def get_company_or_404(db: Session, company_id: int, *, current_user: User) -> Company:
    scoped_company_id = resolve_company_scope(current_user, company_id)
    query = db.query(Company)
    if scoped_company_id is not None:
        query = query.filter(Company.id == scoped_company_id)
    company = query.filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    return company


def list_companies(
    db: Session,
    current_user: User,
    *,
    pagination: PaginationParams,
    search: str | None = None,
) -> dict[str, object]:
    scoped_company_id = resolve_company_scope(current_user)
    query = db.query(Company)
    if scoped_company_id is not None:
        query = query.filter(Company.id == scoped_company_id)
    if search:
        pattern = f"%{search}%"
        query = query.filter(Company.name.ilike(pattern))
    return paginate_query(query.order_by(Company.name), pagination=pagination)


def create_company(db: Session, payload: CompanyCreate, current_user: User) -> Company:
    existing = db.query(Company).filter(Company.name == payload.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company name already exists",
        )
    company = Company(**payload.model_dump())
    db.add(company)
    db.flush()
    log_audit_event(
        db,
        entity_type="company",
        entity_id=company.id,
        action="create",
        performed_by=current_user,
        after_data=serialize_model(company),
        remarks=company.name,
    )
    db.commit()
    db.refresh(company)
    return company


def update_company(
    db: Session,
    company_id: int,
    payload: CompanyUpdate,
    current_user: User,
) -> Company:
    company = get_company_or_404(db, company_id, current_user=current_user)
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] != company.name:
        existing = db.query(Company).filter(Company.name == updates["name"]).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company name already exists",
            )
    before_data = serialize_model(company)
    for field, value in updates.items():
        setattr(company, field, value)
    db.flush()
    log_audit_event(
        db,
        entity_type="company",
        entity_id=company.id,
        action="update",
        performed_by=current_user,
        before_data=before_data,
        after_data=serialize_model(company),
        remarks=company.name,
    )
    db.commit()
    db.refresh(company)
    return company
