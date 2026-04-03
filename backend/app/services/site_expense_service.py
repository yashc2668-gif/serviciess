"""Site expense service helpers."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.project import Project
from app.models.site_expense import SiteExpense
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.site_expense import SiteExpenseCreate, SiteExpenseUpdate
from app.services.audit_service import log_audit_event, serialize_model
from app.services.company_scope_service import (
    apply_project_company_scope,
    apply_site_expense_company_scope,
    apply_vendor_company_scope,
    resolve_company_scope,
)
from app.services.concurrency_service import (
    apply_write_lock,
    commit_with_conflict_handling,
    ensure_lock_version_matches,
    flush_with_conflict_handling,
)
from app.utils.pagination import PaginationParams, paginate_query

VALID_SITE_EXPENSE_STATUSES = {"draft", "approved", "paid"}


def _normalize_code(value: str) -> str:
    normalized = value.strip().upper()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expense_no cannot be empty")
    return normalized


def _normalize_head(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if len(normalized) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expense_head is required")
    return normalized


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_status(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in VALID_SITE_EXPENSE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid site expense status. Allowed values: draft, approved, paid",
        )
    return normalized


def _ensure_unique_expense_no(
    db: Session,
    expense_no: str,
    *,
    exclude_expense_id: int | None = None,
) -> None:
    query = db.query(SiteExpense).filter(func.lower(SiteExpense.expense_no) == expense_no.lower())
    if exclude_expense_id is not None:
        query = query.filter(SiteExpense.id != exclude_expense_id)
    if query.first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Expense number already exists")


def _get_project_or_404(
    db: Session,
    project_id: int,
    *,
    current_user: User,
) -> Project:
    query = apply_project_company_scope(
        db.query(Project).filter(Project.is_deleted.is_(False), Project.id == project_id),
        resolve_company_scope(current_user),
    )
    project = query.first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _get_vendor_or_404(
    db: Session,
    vendor_id: int,
    *,
    company_id: int | None,
) -> Vendor:
    query = apply_vendor_company_scope(
        db.query(Vendor).filter(Vendor.is_deleted.is_(False), Vendor.id == vendor_id),
        company_id,
    )
    vendor = query.first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return vendor


def _serialize_expense(expense: SiteExpense) -> dict:
    return serialize_model(expense)


def list_site_expenses(
    db: Session,
    *,
    current_user: User,
    pagination: PaginationParams,
    project_id: int | None = None,
    status_filter: str | None = None,
    expense_head: str | None = None,
    search: str | None = None,
) -> dict[str, object]:
    query = apply_site_expense_company_scope(
        db.query(SiteExpense).options(joinedload(SiteExpense.project), joinedload(SiteExpense.vendor)),
        resolve_company_scope(current_user),
    )
    if project_id is not None:
        query = query.filter(SiteExpense.project_id == project_id)
    if status_filter:
        query = query.filter(SiteExpense.status == _normalize_status(status_filter))
    if expense_head:
        query = query.filter(SiteExpense.expense_head.ilike(expense_head.strip()))
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                SiteExpense.expense_no.ilike(search_term),
                SiteExpense.expense_head.ilike(search_term),
                SiteExpense.payee_name.ilike(search_term),
                SiteExpense.reference_no.ilike(search_term),
                SiteExpense.remarks.ilike(search_term),
            )
        )
    return paginate_query(
        query.order_by(SiteExpense.expense_date.desc(), SiteExpense.id.desc()),
        pagination=pagination,
    )


def get_site_expense_or_404(
    db: Session,
    expense_id: int,
    *,
    current_user: User,
    lock_for_update: bool = False,
) -> SiteExpense:
    query = apply_site_expense_company_scope(
        db.query(SiteExpense).options(joinedload(SiteExpense.project), joinedload(SiteExpense.vendor)),
        resolve_company_scope(current_user),
    ).filter(SiteExpense.id == expense_id)
    if lock_for_update:
        query = apply_write_lock(query, db)
    expense = query.first()
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site expense not found")
    return expense


def create_site_expense(
    db: Session,
    payload: SiteExpenseCreate,
    current_user: User,
) -> SiteExpense:
    project = _get_project_or_404(db, payload.project_id, current_user=current_user)
    vendor_id = payload.vendor_id
    if vendor_id is not None:
        _get_vendor_or_404(db, vendor_id, company_id=project.company_id)

    data = payload.model_dump()
    data["expense_no"] = _normalize_code(data["expense_no"])
    data["expense_head"] = _normalize_head(data["expense_head"])
    data["payee_name"] = _normalize_optional_text(data.get("payee_name"))
    data["payment_mode"] = _normalize_optional_text(data.get("payment_mode"))
    data["reference_no"] = _normalize_optional_text(data.get("reference_no"))
    data["remarks"] = _normalize_optional_text(data.get("remarks"))
    _ensure_unique_expense_no(db, data["expense_no"])

    expense = SiteExpense(**data, status="draft", created_by=current_user.id)
    db.add(expense)
    flush_with_conflict_handling(db, entity_name="Site expense")
    log_audit_event(
        db,
        entity_type="site_expense",
        entity_id=expense.id,
        action="create",
        performed_by=current_user,
        after_data=_serialize_expense(expense),
        remarks=expense.expense_no,
    )
    commit_with_conflict_handling(db, entity_name="Site expense")
    return get_site_expense_or_404(db, expense.id, current_user=current_user)


def update_site_expense(
    db: Session,
    expense_id: int,
    payload: SiteExpenseUpdate,
    current_user: User,
) -> SiteExpense:
    expense = get_site_expense_or_404(db, expense_id, current_user=current_user, lock_for_update=True)
    if expense.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only draft site expenses can be updated")

    updates = payload.model_dump(exclude_unset=True)
    ensure_lock_version_matches(expense, updates.pop("lock_version", None), entity_name="Site expense")

    if "expense_no" in updates and updates["expense_no"] is not None:
        updates["expense_no"] = _normalize_code(updates["expense_no"])
        _ensure_unique_expense_no(db, updates["expense_no"], exclude_expense_id=expense.id)
    if "expense_head" in updates and updates["expense_head"] is not None:
        updates["expense_head"] = _normalize_head(updates["expense_head"])
    for field in ("payee_name", "payment_mode", "reference_no", "remarks"):
        if field in updates:
            updates[field] = _normalize_optional_text(updates[field])

    next_project_id = expense.project_id
    if "project_id" in updates and updates["project_id"] is not None:
        project = _get_project_or_404(db, updates["project_id"], current_user=current_user)
        next_project_id = project.id
        next_company_id = project.company_id
    else:
        project = _get_project_or_404(db, expense.project_id, current_user=current_user)
        next_company_id = project.company_id
    if "vendor_id" in updates and updates["vendor_id"] is not None:
        _get_vendor_or_404(db, updates["vendor_id"], company_id=next_company_id)
    elif expense.vendor_id is not None and "project_id" in updates:
        _get_vendor_or_404(db, expense.vendor_id, company_id=next_company_id)

    before_data = _serialize_expense(expense)
    for field, value in updates.items():
        setattr(expense, field, value)
    expense.project_id = next_project_id
    flush_with_conflict_handling(db, entity_name="Site expense")
    log_audit_event(
        db,
        entity_type="site_expense",
        entity_id=expense.id,
        action="update",
        performed_by=current_user,
        before_data=before_data,
        after_data=_serialize_expense(expense),
        remarks=expense.expense_no,
    )
    commit_with_conflict_handling(db, entity_name="Site expense")
    return get_site_expense_or_404(db, expense.id, current_user=current_user)


def approve_site_expense(
    db: Session,
    expense_id: int,
    current_user: User,
    *,
    expected_lock_version: int | None = None,
    remarks: str | None = None,
) -> SiteExpense:
    expense = get_site_expense_or_404(db, expense_id, current_user=current_user, lock_for_update=True)
    ensure_lock_version_matches(expense, expected_lock_version, entity_name="Site expense")
    if expense.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only draft site expenses can be approved")

    before_data = _serialize_expense(expense)
    expense.status = "approved"
    expense.approved_by = current_user.id
    expense.approved_at = datetime.now(timezone.utc)
    if remarks is not None:
        expense.remarks = _normalize_optional_text(remarks)
    flush_with_conflict_handling(db, entity_name="Site expense")
    log_audit_event(
        db,
        entity_type="site_expense",
        entity_id=expense.id,
        action="approve",
        performed_by=current_user,
        before_data=before_data,
        after_data=_serialize_expense(expense),
        remarks=expense.remarks,
    )
    commit_with_conflict_handling(db, entity_name="Site expense")
    return get_site_expense_or_404(db, expense.id, current_user=current_user)


def mark_site_expense_paid(
    db: Session,
    expense_id: int,
    current_user: User,
    *,
    expected_lock_version: int | None = None,
    remarks: str | None = None,
) -> SiteExpense:
    expense = get_site_expense_or_404(db, expense_id, current_user=current_user, lock_for_update=True)
    ensure_lock_version_matches(expense, expected_lock_version, entity_name="Site expense")
    if expense.status != "approved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only approved site expenses can be marked paid")

    before_data = _serialize_expense(expense)
    expense.status = "paid"
    expense.paid_by = current_user.id
    expense.paid_at = datetime.now(timezone.utc)
    if remarks is not None:
        expense.remarks = _normalize_optional_text(remarks)
    flush_with_conflict_handling(db, entity_name="Site expense")
    log_audit_event(
        db,
        entity_type="site_expense",
        entity_id=expense.id,
        action="paid",
        performed_by=current_user,
        before_data=before_data,
        after_data=_serialize_expense(expense),
        remarks=expense.remarks,
    )
    commit_with_conflict_handling(db, entity_name="Site expense")
    return get_site_expense_or_404(db, expense.id, current_user=current_user)
