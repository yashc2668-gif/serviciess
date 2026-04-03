"""Helpers for company-scoped access control and query filtering."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Query

from app.models.company import Company
from app.models.contract import Contract
from app.models.labour import Labour
from app.models.labour_advance import LabourAdvance
from app.models.labour_attendance import LabourAttendance
from app.models.labour_bill import LabourBill
from app.models.labour_contractor import LabourContractor
from app.models.labour_productivity import LabourProductivity
from app.models.material import Material
from app.models.material_issue import MaterialIssue
from app.models.material_receipt import MaterialReceipt
from app.models.material_requisition import MaterialRequisition
from app.models.material_stock_adjustment import MaterialStockAdjustment
from app.models.payment import Payment
from app.models.project import Project
from app.models.ra_bill import RABill
from app.models.secured_advance import SecuredAdvance
from app.models.site_expense import SiteExpense
from app.models.user import User
from app.models.vendor import Vendor


def is_admin_user(user: User) -> bool:
    return (user.role or "").strip().lower() == "admin"


def resolve_company_scope(
    current_user: User,
    requested_company_id: int | None = None,
) -> int | None:
    if is_admin_user(current_user):
        return requested_company_id
    if current_user.company_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user is not assigned to a company scope",
        )
    if requested_company_id is not None and requested_company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot access another company scope",
        )
    return current_user.company_id


def require_company_scope(current_user: User, company_id: int | None) -> int:
    resolved_company_id = resolve_company_scope(current_user, company_id)
    if resolved_company_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="company_id is required for this operation",
        )
    return resolved_company_id


def ensure_company_exists(query: Query, company_id: int) -> Company:
    company = query.session.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    return company


def apply_project_company_scope(query: Query, company_id: int | None) -> Query:
    if company_id is None:
        return query
    return query.filter(Project.company_id == company_id)


def apply_contract_company_scope(query: Query, company_id: int | None) -> Query:
    if company_id is None:
        return query
    return query.join(Project, Contract.project_id == Project.id).filter(Project.company_id == company_id)


def apply_vendor_company_scope(query: Query, company_id: int | None) -> Query:
    if company_id is None:
        return query
    return query.filter(Vendor.company_id == company_id)


def apply_labour_company_scope(query: Query, company_id: int | None) -> Query:
    if company_id is None:
        return query
    return query.filter(Labour.company_id == company_id)


def apply_labour_contractor_company_scope(query: Query, company_id: int | None) -> Query:
    if company_id is None:
        return query
    return query.filter(LabourContractor.company_id == company_id)


def apply_material_company_scope(query: Query, company_id: int | None) -> Query:
    if company_id is None:
        return query
    return query.filter(Material.company_id == company_id)


def apply_ra_bill_company_scope(query: Query, company_id: int | None) -> Query:
    if company_id is None:
        return query
    return query.join(Contract, RABill.contract_id == Contract.id).join(
        Project, Contract.project_id == Project.id
    ).filter(Project.company_id == company_id)


def apply_payment_company_scope(query: Query, company_id: int | None) -> Query:
    if company_id is None:
        return query
    return query.join(Contract, Payment.contract_id == Contract.id).join(
        Project, Contract.project_id == Project.id
    ).filter(Project.company_id == company_id)


def apply_secured_advance_company_scope(query: Query, company_id: int | None) -> Query:
    if company_id is None:
        return query
    return query.join(Contract, SecuredAdvance.contract_id == Contract.id).join(
        Project, Contract.project_id == Project.id
    ).filter(Project.company_id == company_id)


# ---------------------------------------------------------------------------
# Project-based entity scoping (entities with project_id → Project.company_id)
# ---------------------------------------------------------------------------

def _apply_project_based_scope(query: Query, model: type, company_id: int | None) -> Query:
    """Scope any model that has a ``project_id`` FK through Project.company_id."""
    if company_id is None:
        return query
    return query.join(Project, model.project_id == Project.id).filter(
        Project.company_id == company_id,
    )


def apply_labour_advance_company_scope(query: Query, company_id: int | None) -> Query:
    return _apply_project_based_scope(query, LabourAdvance, company_id)


def apply_labour_bill_company_scope(query: Query, company_id: int | None) -> Query:
    return _apply_project_based_scope(query, LabourBill, company_id)


def apply_labour_attendance_company_scope(query: Query, company_id: int | None) -> Query:
    return _apply_project_based_scope(query, LabourAttendance, company_id)


def apply_labour_productivity_company_scope(query: Query, company_id: int | None) -> Query:
    return _apply_project_based_scope(query, LabourProductivity, company_id)


def apply_material_receipt_company_scope(query: Query, company_id: int | None) -> Query:
    return _apply_project_based_scope(query, MaterialReceipt, company_id)


def apply_material_issue_company_scope(query: Query, company_id: int | None) -> Query:
    return _apply_project_based_scope(query, MaterialIssue, company_id)


def apply_material_requisition_company_scope(query: Query, company_id: int | None) -> Query:
    return _apply_project_based_scope(query, MaterialRequisition, company_id)


def apply_material_stock_adjustment_company_scope(query: Query, company_id: int | None) -> Query:
    return _apply_project_based_scope(query, MaterialStockAdjustment, company_id)


def apply_site_expense_company_scope(query: Query, company_id: int | None) -> Query:
    return _apply_project_based_scope(query, SiteExpense, company_id)
