"""Reporting services for management intelligence views."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session, selectinload

from app.models.company import Company
from app.models.contract import Contract
from app.models.deduction import Deduction
from app.models.labour_bill import LabourBill
from app.models.labour_productivity import LabourProductivity
from app.models.material import Material
from app.models.material_issue import MaterialIssue
from app.models.material_issue_item import MaterialIssueItem
from app.models.material_requisition import MaterialRequisition
from app.models.material_requisition_item import MaterialRequisitionItem
from app.models.material_stock_adjustment import MaterialStockAdjustment
from app.models.material_stock_adjustment_item import MaterialStockAdjustmentItem
from app.models.payment import Payment
from app.models.payment_allocation import PaymentAllocation
from app.models.project import Project
from app.models.ra_bill import RABill
from app.models.secured_advance import SecuredAdvance
from app.models.vendor import Vendor
from app.models.user import User
from app.services.company_scope_service import apply_project_company_scope, resolve_company_scope
from app.utils.pagination import PaginationParams, paginate_query, paginate_sequence
from app.utils.sorting import SortDirection, apply_sorting


PROJECT_COST_BILLED_STATUSES = {
    "submitted",
    "verified",
    "finance_hold",
    "approved",
    "partially_paid",
    "paid",
}
PROJECT_COST_LABOUR_STATUSES = {"approved", "paid"}
PENDING_PAYMENT_STATUSES = {"draft", "approved"}
CASH_FLOW_RECEIVABLE_STATUSES = {"approved", "partially_paid"}
MATERIAL_REQUIRED_REQUISITION_STATUSES = {"approved", "partially_issued", "issued"}
LABOUR_PRODUCTIVITY_BENCHMARK_VARIANCE_THRESHOLD = 10.0


def _age_bucket(age_days: int) -> tuple[str, str]:
    if age_days <= 30:
        return "0_30", "0-30 days"
    if age_days <= 60:
        return "31_60", "31-60 days"
    if age_days <= 90:
        return "61_90", "61-90 days"
    if age_days <= 120:
        return "91_120", "91-120 days"
    return "121_plus", "121+ days"


def _forecast_bucket_label(start: date, end: date) -> str:
    if start.month == end.month:
        return f"{start.strftime('%d')} - {end.strftime('%d %b')}"
    return f"{start.strftime('%d %b')} - {end.strftime('%d %b')}"


def _shift_month(anchor: date, offset: int) -> date:
    month_index = (anchor.month - 1) + offset
    year = anchor.year + (month_index // 12)
    month = (month_index % 12) + 1
    return date(year, month, 1)


def _month_label(month_start: date) -> str:
    return month_start.strftime("%b %Y")


def _material_string(value: object | None) -> str:
    return str(value or "").lower()


def _sort_material_consumption_rows(
    rows: list[dict[str, object]],
    *,
    sort_by: str | None,
    sort_dir: SortDirection,
) -> list[dict[str, object]]:
    selected = sort_by or "wastage_amount"
    reverse = sort_dir == SortDirection.DESC
    string_fields = {"company_name", "project_name", "project_code", "material_code", "material_name", "category", "unit"}
    numeric_fields = {
        "requested_qty",
        "required_qty",
        "requisition_issued_qty",
        "issued_qty",
        "wastage_qty",
        "balance_to_issue_qty",
        "excess_issue_qty",
        "issue_coverage_pct",
        "wastage_pct",
        "required_amount",
        "issued_amount",
        "wastage_amount",
    }

    if selected in string_fields:
        return sorted(
            rows,
            key=lambda row: (
                _material_string(row.get(selected)),
                _material_string(row.get("project_name")),
                _material_string(row.get("material_name")),
            ),
            reverse=reverse,
        )

    if selected in numeric_fields:
        return sorted(
            rows,
            key=lambda row: (
                float(row.get(selected) or 0),
                _material_string(row.get("project_name")),
                _material_string(row.get("material_name")),
            ),
            reverse=reverse,
        )

    return sorted(
        rows,
        key=lambda row: (
            float(row.get("wastage_amount") or 0),
            float(row.get("issued_amount") or 0),
            _material_string(row.get("project_name")),
            _material_string(row.get("material_name")),
        ),
        reverse=True,
    )


def _project_cost_report_query(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
):
    scoped_company_id = resolve_company_scope(current_user, company_id)

    contract_summary = (
        db.query(
            Contract.project_id.label("project_id"),
            func.count(Contract.id).label("contract_count"),
            func.coalesce(func.sum(Contract.revised_value), 0).label("committed_amount"),
            func.coalesce(
                func.sum(case((Contract.status == "active", 1), else_=0)),
                0,
            ).label("active_contract_count"),
        )
        .filter(Contract.is_deleted.is_(False))
        .group_by(Contract.project_id)
        .subquery()
    )
    billed_summary = (
        db.query(
            Contract.project_id.label("project_id"),
            func.coalesce(func.sum(RABill.net_payable), 0).label("billed_cost_amount"),
        )
        .join(Contract, Contract.id == RABill.contract_id)
        .filter(
            Contract.is_deleted.is_(False),
            RABill.status.in_(PROJECT_COST_BILLED_STATUSES),
        )
        .group_by(Contract.project_id)
        .subquery()
    )
    payment_summary = (
        db.query(
            Contract.project_id.label("project_id"),
            func.coalesce(func.sum(Payment.amount), 0).label("paid_cost_amount"),
        )
        .join(Contract, Contract.id == Payment.contract_id)
        .filter(
            Contract.is_deleted.is_(False),
            Payment.is_archived.is_(False),
            Payment.status == "released",
        )
        .group_by(Contract.project_id)
        .subquery()
    )
    material_issue_summary = (
        db.query(
            MaterialIssue.project_id.label("project_id"),
            func.coalesce(func.sum(MaterialIssue.total_amount), 0).label(
                "material_issued_amount"
            ),
        )
        .filter(MaterialIssue.status == "issued")
        .group_by(MaterialIssue.project_id)
        .subquery()
    )
    labour_bill_summary = (
        db.query(
            LabourBill.project_id.label("project_id"),
            func.coalesce(func.sum(LabourBill.net_payable), 0).label(
                "labour_billed_amount"
            ),
        )
        .filter(LabourBill.status.in_(PROJECT_COST_LABOUR_STATUSES))
        .group_by(LabourBill.project_id)
        .subquery()
    )
    secured_advance_summary = (
        db.query(
            Contract.project_id.label("project_id"),
            func.coalesce(func.sum(SecuredAdvance.balance), 0).label(
                "secured_advance_outstanding"
            ),
        )
        .join(Contract, Contract.id == SecuredAdvance.contract_id)
        .filter(
            Contract.is_deleted.is_(False),
            SecuredAdvance.is_archived.is_(False),
            SecuredAdvance.balance > 0,
        )
        .group_by(Contract.project_id)
        .subquery()
    )

    contract_count_expr = func.coalesce(contract_summary.c.contract_count, 0)
    active_contract_count_expr = func.coalesce(
        contract_summary.c.active_contract_count, 0
    )
    committed_amount_expr = func.coalesce(contract_summary.c.committed_amount, 0)
    billed_cost_amount_expr = func.coalesce(billed_summary.c.billed_cost_amount, 0)
    paid_cost_amount_expr = func.coalesce(payment_summary.c.paid_cost_amount, 0)
    material_issued_amount_expr = func.coalesce(
        material_issue_summary.c.material_issued_amount, 0
    )
    labour_billed_amount_expr = func.coalesce(
        labour_bill_summary.c.labour_billed_amount, 0
    )
    secured_advance_outstanding_expr = func.coalesce(
        secured_advance_summary.c.secured_advance_outstanding, 0
    )
    actual_cost_amount_expr = (
        paid_cost_amount_expr + material_issued_amount_expr + labour_billed_amount_expr
    )
    actual_variance_amount_expr = Project.revised_value - actual_cost_amount_expr
    committed_variance_amount_expr = Project.revised_value - committed_amount_expr
    actual_utilization_pct_expr = case(
        (Project.revised_value > 0, (actual_cost_amount_expr * 100.0) / Project.revised_value),
        else_=0.0,
    )
    committed_utilization_pct_expr = case(
        (Project.revised_value > 0, (committed_amount_expr * 100.0) / Project.revised_value),
        else_=0.0,
    )

    query = (
        db.query(
            Project.id.label("project_id"),
            Project.company_id.label("company_id"),
            Company.name.label("company_name"),
            Project.name.label("project_name"),
            Project.code.label("project_code"),
            Project.status.label("status"),
            Project.original_value.label("original_budget_amount"),
            Project.revised_value.label("budget_amount"),
            contract_count_expr.label("contract_count"),
            active_contract_count_expr.label("active_contract_count"),
            committed_amount_expr.label("committed_amount"),
            billed_cost_amount_expr.label("billed_cost_amount"),
            paid_cost_amount_expr.label("paid_cost_amount"),
            material_issued_amount_expr.label("material_issued_amount"),
            labour_billed_amount_expr.label("labour_billed_amount"),
            actual_cost_amount_expr.label("actual_cost_amount"),
            secured_advance_outstanding_expr.label("secured_advance_outstanding"),
            actual_variance_amount_expr.label("actual_variance_amount"),
            committed_variance_amount_expr.label("committed_variance_amount"),
            actual_utilization_pct_expr.label("actual_utilization_pct"),
            committed_utilization_pct_expr.label("committed_utilization_pct"),
        )
        .join(Company, Company.id == Project.company_id)
        .outerjoin(contract_summary, contract_summary.c.project_id == Project.id)
        .outerjoin(billed_summary, billed_summary.c.project_id == Project.id)
        .outerjoin(payment_summary, payment_summary.c.project_id == Project.id)
        .outerjoin(material_issue_summary, material_issue_summary.c.project_id == Project.id)
        .outerjoin(labour_bill_summary, labour_bill_summary.c.project_id == Project.id)
        .outerjoin(
            secured_advance_summary,
            secured_advance_summary.c.project_id == Project.id,
        )
        .filter(Project.is_deleted.is_(False))
    )
    query = apply_project_company_scope(query, scoped_company_id)

    if status_filter:
        query = query.filter(Project.status == status_filter.strip().lower())
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Project.name.ilike(search_term),
                Project.code.ilike(search_term),
                Project.client_name.ilike(search_term),
                Project.location.ilike(search_term),
                Company.name.ilike(search_term),
            )
        )

    sort_options = {
        "project_name": (Project.name, Project.id),
        "company_name": (Company.name, Project.id),
        "status": (Project.status, Project.id),
        "budget_amount": (Project.revised_value, Project.id),
        "committed_amount": (committed_amount_expr, Project.id),
        "billed_cost_amount": (billed_cost_amount_expr, Project.id),
        "paid_cost_amount": (paid_cost_amount_expr, Project.id),
        "material_issued_amount": (material_issued_amount_expr, Project.id),
        "labour_billed_amount": (labour_billed_amount_expr, Project.id),
        "actual_cost_amount": (actual_cost_amount_expr, Project.id),
        "actual_variance_amount": (actual_variance_amount_expr, Project.id),
        "committed_variance_amount": (committed_variance_amount_expr, Project.id),
        "actual_utilization_pct": (actual_utilization_pct_expr, Project.id),
        "committed_utilization_pct": (committed_utilization_pct_expr, Project.id),
    }
    default_order = (actual_variance_amount_expr.asc(), Project.id.asc())
    return query, sort_options, default_order


def list_project_cost_report(
    db: Session,
    *,
    current_user: User,
    pagination: PaginationParams,
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: SortDirection = SortDirection.ASC,
) -> dict[str, object]:
    query, sort_options, default_order = _project_cost_report_query(
        db,
        current_user=current_user,
        company_id=company_id,
        status_filter=status_filter,
        search=search,
    )
    return paginate_query(
        apply_sorting(
            query,
            sort_by=sort_by,
            sort_dir=sort_dir,
            sort_options=sort_options,
            default_order=default_order,
        ),
        pagination=pagination,
    )


def list_project_cost_report_for_export(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: SortDirection = SortDirection.ASC,
):
    query, sort_options, default_order = _project_cost_report_query(
        db,
        current_user=current_user,
        company_id=company_id,
        status_filter=status_filter,
        search=search,
    )
    return apply_sorting(
        query,
        sort_by=sort_by,
        sort_dir=sort_dir,
        sort_options=sort_options,
        default_order=default_order,
    ).all()


def _contract_commercial_query(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
    search: str | None = None,
):
    scoped_company_id = resolve_company_scope(current_user, company_id)

    billed_summary = (
        db.query(
            RABill.contract_id.label("contract_id"),
            func.coalesce(func.sum(RABill.net_payable), 0).label("billed_amount"),
        )
        .filter(
            RABill.is_archived.is_(False),
            RABill.status.in_(PROJECT_COST_BILLED_STATUSES),
        )
        .group_by(RABill.contract_id)
        .subquery()
    )
    payment_summary = (
        db.query(
            Payment.contract_id.label("contract_id"),
            func.coalesce(func.sum(Payment.amount), 0).label("paid_amount"),
        )
        .filter(
            Payment.is_archived.is_(False),
            Payment.status == "released",
        )
        .group_by(Payment.contract_id)
        .subquery()
    )
    material_summary = (
        db.query(
            MaterialIssue.contract_id.label("contract_id"),
            func.coalesce(func.sum(MaterialIssue.total_amount), 0).label(
                "material_cost_amount"
            ),
        )
        .filter(
            MaterialIssue.contract_id.isnot(None),
            MaterialIssue.status == "issued",
        )
        .group_by(MaterialIssue.contract_id)
        .subquery()
    )
    labour_summary = (
        db.query(
            LabourBill.contract_id.label("contract_id"),
            func.coalesce(func.sum(LabourBill.net_payable), 0).label(
                "labour_cost_amount"
            ),
        )
        .filter(
            LabourBill.contract_id.isnot(None),
            LabourBill.status.in_(PROJECT_COST_LABOUR_STATUSES),
        )
        .group_by(LabourBill.contract_id)
        .subquery()
    )
    retention_summary = (
        db.query(
            RABill.contract_id.label("contract_id"),
            func.coalesce(func.sum(Deduction.amount), 0).label("retention_held_amount"),
        )
        .join(RABill, RABill.id == Deduction.ra_bill_id)
        .filter(
            RABill.is_archived.is_(False),
            Deduction.deduction_type == "retention",
        )
        .group_by(RABill.contract_id)
        .subquery()
    )
    secured_advance_summary = (
        db.query(
            SecuredAdvance.contract_id.label("contract_id"),
            func.coalesce(func.sum(SecuredAdvance.balance), 0).label(
                "secured_advance_outstanding"
            ),
        )
        .filter(
            SecuredAdvance.is_archived.is_(False),
            SecuredAdvance.balance > 0,
        )
        .group_by(SecuredAdvance.contract_id)
        .subquery()
    )

    billed_amount_expr = func.coalesce(billed_summary.c.billed_amount, 0)
    paid_amount_expr = func.coalesce(payment_summary.c.paid_amount, 0)
    material_cost_amount_expr = func.coalesce(material_summary.c.material_cost_amount, 0)
    labour_cost_amount_expr = func.coalesce(labour_summary.c.labour_cost_amount, 0)
    retention_held_amount_expr = func.coalesce(
        retention_summary.c.retention_held_amount, 0
    )
    secured_advance_outstanding_expr = func.coalesce(
        secured_advance_summary.c.secured_advance_outstanding, 0
    )
    actual_cost_amount_expr = (
        paid_amount_expr + material_cost_amount_expr + labour_cost_amount_expr
    )
    outstanding_payable_expr = billed_amount_expr - paid_amount_expr
    commercial_headroom_amount_expr = Contract.revised_value - actual_cost_amount_expr
    billed_margin_amount_expr = billed_amount_expr - actual_cost_amount_expr
    headroom_pct_expr = case(
        (Contract.revised_value > 0, (commercial_headroom_amount_expr * 100.0) / Contract.revised_value),
        else_=0.0,
    )
    counterparty_name_expr = func.coalesce(Vendor.name, Contract.client_name, "Client contract")

    query = (
        db.query(
            Contract.id.label("contract_id"),
            Contract.project_id.label("project_id"),
            Company.name.label("company_name"),
            Project.name.label("project_name"),
            counterparty_name_expr.label("vendor_name"),
            Contract.contract_no.label("contract_no"),
            Contract.title.label("contract_title"),
            Contract.status.label("status"),
            Contract.end_date.label("end_date"),
            Contract.revised_value.label("contract_value"),
            billed_amount_expr.label("billed_amount"),
            paid_amount_expr.label("paid_amount"),
            material_cost_amount_expr.label("material_cost_amount"),
            labour_cost_amount_expr.label("labour_cost_amount"),
            actual_cost_amount_expr.label("actual_cost_amount"),
            outstanding_payable_expr.label("outstanding_payable"),
            retention_held_amount_expr.label("retention_held_amount"),
            secured_advance_outstanding_expr.label("secured_advance_outstanding"),
            commercial_headroom_amount_expr.label("commercial_headroom_amount"),
            billed_margin_amount_expr.label("billed_margin_amount"),
            headroom_pct_expr.label("headroom_pct"),
        )
        .join(Project, Project.id == Contract.project_id)
        .join(Company, Company.id == Project.company_id)
        .outerjoin(Vendor, Vendor.id == Contract.vendor_id)
        .outerjoin(billed_summary, billed_summary.c.contract_id == Contract.id)
        .outerjoin(payment_summary, payment_summary.c.contract_id == Contract.id)
        .outerjoin(material_summary, material_summary.c.contract_id == Contract.id)
        .outerjoin(labour_summary, labour_summary.c.contract_id == Contract.id)
        .outerjoin(retention_summary, retention_summary.c.contract_id == Contract.id)
        .outerjoin(
            secured_advance_summary,
            secured_advance_summary.c.contract_id == Contract.id,
        )
        .filter(Contract.is_deleted.is_(False), Project.is_deleted.is_(False))
    )
    query = apply_project_company_scope(query, scoped_company_id)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Contract.contract_no.ilike(search_term),
                Contract.title.ilike(search_term),
                Project.name.ilike(search_term),
                counterparty_name_expr.ilike(search_term),
                Company.name.ilike(search_term),
            )
        )

    sort_options = {
        "contract_no": (Contract.contract_no, Contract.id),
        "project_name": (Project.name, Contract.id),
        "vendor_name": (Vendor.name, Contract.id),
        "status": (Contract.status, Contract.id),
        "contract_value": (Contract.revised_value, Contract.id),
        "billed_amount": (billed_amount_expr, Contract.id),
        "paid_amount": (paid_amount_expr, Contract.id),
        "actual_cost_amount": (actual_cost_amount_expr, Contract.id),
        "commercial_headroom_amount": (commercial_headroom_amount_expr, Contract.id),
        "billed_margin_amount": (billed_margin_amount_expr, Contract.id),
        "headroom_pct": (headroom_pct_expr, Contract.id),
        "outstanding_payable": (outstanding_payable_expr, Contract.id),
        "retention_held_amount": (retention_held_amount_expr, Contract.id),
    }
    default_order = (commercial_headroom_amount_expr.asc(), Contract.id.asc())
    return query, sort_options, default_order


def list_contract_commercial_report(
    db: Session,
    *,
    current_user: User,
    pagination: PaginationParams,
    company_id: int | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: SortDirection = SortDirection.ASC,
) -> dict[str, object]:
    query, sort_options, default_order = _contract_commercial_query(
        db,
        current_user=current_user,
        company_id=company_id,
        search=search,
    )
    return paginate_query(
        apply_sorting(
            query,
            sort_by=sort_by,
            sort_dir=sort_dir,
            sort_options=sort_options,
            default_order=default_order,
        ),
        pagination=pagination,
    )


def list_contract_commercial_report_for_export(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: SortDirection = SortDirection.ASC,
):
    query, sort_options, default_order = _contract_commercial_query(
        db,
        current_user=current_user,
        company_id=company_id,
        search=search,
    )
    return apply_sorting(
        query,
        sort_by=sort_by,
        sort_dir=sort_dir,
        sort_options=sort_options,
        default_order=default_order,
    ).all()


def get_ageing_analysis(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
    top_limit: int = 8,
) -> dict[str, object]:
    scoped_company_id = resolve_company_scope(current_user, company_id)
    today = date.today()

    bill_query = (
        db.query(
            RABill.id.label("bill_id"),
            RABill.contract_id.label("contract_id"),
            Project.name.label("project_name"),
            Contract.contract_no.label("contract_no"),
            Contract.title.label("contract_title"),
            RABill.bill_no.label("bill_no"),
            RABill.bill_date.label("bill_date"),
            RABill.status.label("status"),
            (
                func.coalesce(RABill.net_payable, 0)
                - func.coalesce(
                    db.query(func.sum(PaymentAllocation.amount))
                    .filter(PaymentAllocation.ra_bill_id == RABill.id)
                    .correlate(RABill)
                    .scalar_subquery(),
                    0,
                )
            ).label("outstanding_amount"),
        )
        .join(Contract, Contract.id == RABill.contract_id)
        .join(Project, Project.id == Contract.project_id)
        .filter(
            Contract.is_deleted.is_(False),
            Project.is_deleted.is_(False),
            RABill.is_archived.is_(False),
            RABill.status.in_(["approved", "partially_paid"]),
        )
    )
    bill_query = apply_project_company_scope(bill_query, scoped_company_id)

    payment_query = (
        db.query(
            Payment.id.label("payment_id"),
            Payment.contract_id.label("contract_id"),
            Project.name.label("project_name"),
            Contract.contract_no.label("contract_no"),
            Payment.payment_date.label("payment_date"),
            Payment.status.label("status"),
            Payment.amount.label("pending_amount"),
        )
        .join(Contract, Contract.id == Payment.contract_id)
        .join(Project, Project.id == Contract.project_id)
        .filter(
            Contract.is_deleted.is_(False),
            Project.is_deleted.is_(False),
            Payment.is_archived.is_(False),
            Payment.status.in_(PENDING_PAYMENT_STATUSES),
            Payment.payment_date < today,
        )
    )
    payment_query = apply_project_company_scope(payment_query, scoped_company_id)

    bill_bucket_counts: defaultdict[str, int] = defaultdict(int)
    bill_bucket_amounts: defaultdict[str, float] = defaultdict(float)
    overdue_ra_bills: list[dict[str, object]] = []
    for row in bill_query.all():
        outstanding_amount = float(row.outstanding_amount or 0)
        if outstanding_amount <= 0:
            continue
        age_days = max((today - row.bill_date).days, 0)
        bucket, label = _age_bucket(age_days)
        bill_bucket_counts[bucket] += 1
        bill_bucket_amounts[bucket] += outstanding_amount
        overdue_ra_bills.append(
            {
                "bill_id": row.bill_id,
                "contract_id": row.contract_id,
                "project_name": row.project_name,
                "contract_no": row.contract_no,
                "contract_title": row.contract_title,
                "bill_no": row.bill_no,
                "bill_date": row.bill_date,
                "status": row.status,
                "outstanding_amount": outstanding_amount,
                "age_days": age_days,
                "bucket": label,
            }
        )

    payment_bucket_counts: defaultdict[str, int] = defaultdict(int)
    payment_bucket_amounts: defaultdict[str, float] = defaultdict(float)
    overdue_payments: list[dict[str, object]] = []
    for row in payment_query.all():
        pending_amount = float(row.pending_amount or 0)
        if pending_amount <= 0:
            continue
        age_days = max((today - row.payment_date).days, 0)
        bucket, label = _age_bucket(age_days)
        payment_bucket_counts[bucket] += 1
        payment_bucket_amounts[bucket] += pending_amount
        overdue_payments.append(
            {
                "payment_id": row.payment_id,
                "contract_id": row.contract_id,
                "project_name": row.project_name,
                "contract_no": row.contract_no,
                "payment_date": row.payment_date,
                "status": row.status,
                "pending_amount": pending_amount,
                "age_days": age_days,
                "bucket": label,
            }
        )

    bucket_order = [
        ("0_30", "0-30 days"),
        ("31_60", "31-60 days"),
        ("61_90", "61-90 days"),
        ("91_120", "91-120 days"),
        ("121_plus", "121+ days"),
    ]
    overdue_ra_bills.sort(key=lambda row: (-row["age_days"], -row["outstanding_amount"]))
    overdue_payments.sort(key=lambda row: (-row["age_days"], -row["pending_amount"]))

    return {
        "ra_bill_buckets": [
            {
                "bucket": bucket,
                "label": label,
                "count": bill_bucket_counts[bucket],
                "amount": round(bill_bucket_amounts[bucket], 2),
            }
            for bucket, label in bucket_order
        ],
        "payment_buckets": [
            {
                "bucket": bucket,
                "label": label,
                "count": payment_bucket_counts[bucket],
                "amount": round(payment_bucket_amounts[bucket], 2),
            }
            for bucket, label in bucket_order
        ],
        "overdue_ra_bills": overdue_ra_bills[:top_limit],
        "overdue_payments": overdue_payments[:top_limit],
    }


def _retention_tracking_query(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
    search: str | None = None,
):
    scoped_company_id = resolve_company_scope(current_user, company_id)
    today = date.today()

    billed_summary = (
        db.query(
            RABill.contract_id.label("contract_id"),
            func.coalesce(func.sum(RABill.net_payable), 0).label("billed_amount"),
        )
        .filter(
            RABill.is_archived.is_(False),
            RABill.status.in_(PROJECT_COST_BILLED_STATUSES),
        )
        .group_by(RABill.contract_id)
        .subquery()
    )
    retention_summary = (
        db.query(
            RABill.contract_id.label("contract_id"),
            func.coalesce(func.sum(Deduction.amount), 0).label(
                "total_retention_deducted"
            ),
        )
        .join(RABill, RABill.id == Deduction.ra_bill_id)
        .filter(
            RABill.is_archived.is_(False),
            Deduction.deduction_type == "retention",
        )
        .group_by(RABill.contract_id)
        .subquery()
    )

    billed_amount_expr = func.coalesce(billed_summary.c.billed_amount, 0)
    total_retention_deducted_expr = func.coalesce(
        retention_summary.c.total_retention_deducted, 0
    )
    estimated_retention_cap_expr = (
        Contract.revised_value * func.coalesce(Contract.retention_percentage, 0) / 100.0
    )
    progress_pct_expr = case(
        (
            estimated_retention_cap_expr > 0,
            (total_retention_deducted_expr * 100.0) / estimated_retention_cap_expr,
        ),
        else_=0.0,
    )
    release_status_expr = case(
        (total_retention_deducted_expr <= 0, "clear"),
        (Contract.status == "completed", "ready_for_review"),
        (
            (Contract.end_date.isnot(None)) & (Contract.end_date < today),
            "past_due_review",
        ),
        else_="tracking",
    )
    counterparty_name_expr = func.coalesce(Vendor.name, Contract.client_name, "Client contract")

    query = (
        db.query(
            Contract.id.label("contract_id"),
            Contract.project_id.label("project_id"),
            Company.name.label("company_name"),
            Project.name.label("project_name"),
            counterparty_name_expr.label("vendor_name"),
            Contract.contract_no.label("contract_no"),
            Contract.title.label("contract_title"),
            Contract.status.label("status"),
            Contract.end_date.label("scheduled_release_date"),
            Contract.retention_percentage.label("retention_percentage"),
            Contract.revised_value.label("contract_value"),
            billed_amount_expr.label("billed_amount"),
            estimated_retention_cap_expr.label("estimated_retention_cap"),
            total_retention_deducted_expr.label("total_retention_deducted"),
            total_retention_deducted_expr.label("outstanding_retention_amount"),
            progress_pct_expr.label("progress_pct"),
            release_status_expr.label("release_status"),
        )
        .join(Project, Project.id == Contract.project_id)
        .join(Company, Company.id == Project.company_id)
        .outerjoin(Vendor, Vendor.id == Contract.vendor_id)
        .outerjoin(billed_summary, billed_summary.c.contract_id == Contract.id)
        .outerjoin(retention_summary, retention_summary.c.contract_id == Contract.id)
        .filter(Contract.is_deleted.is_(False), Project.is_deleted.is_(False))
    )
    query = apply_project_company_scope(query, scoped_company_id)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Contract.contract_no.ilike(search_term),
                Contract.title.ilike(search_term),
                Project.name.ilike(search_term),
                counterparty_name_expr.ilike(search_term),
                Company.name.ilike(search_term),
            )
        )

    sort_options = {
        "contract_no": (Contract.contract_no, Contract.id),
        "project_name": (Project.name, Contract.id),
        "vendor_name": (counterparty_name_expr, Contract.id),
        "retention_percentage": (Contract.retention_percentage, Contract.id),
        "contract_value": (Contract.revised_value, Contract.id),
        "billed_amount": (billed_amount_expr, Contract.id),
        "estimated_retention_cap": (estimated_retention_cap_expr, Contract.id),
        "outstanding_retention_amount": (total_retention_deducted_expr, Contract.id),
        "progress_pct": (progress_pct_expr, Contract.id),
        "scheduled_release_date": (Contract.end_date, Contract.id),
    }
    default_order = (total_retention_deducted_expr.desc(), Contract.id.asc())
    return query, sort_options, default_order


def list_retention_tracking_report(
    db: Session,
    *,
    current_user: User,
    pagination: PaginationParams,
    company_id: int | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: SortDirection = SortDirection.ASC,
) -> dict[str, object]:
    query, sort_options, default_order = _retention_tracking_query(
        db,
        current_user=current_user,
        company_id=company_id,
        search=search,
    )
    return paginate_query(
        apply_sorting(
            query,
            sort_by=sort_by,
            sort_dir=sort_dir,
            sort_options=sort_options,
            default_order=default_order,
        ),
        pagination=pagination,
    )


def list_retention_tracking_report_for_export(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: SortDirection = SortDirection.ASC,
):
    query, sort_options, default_order = _retention_tracking_query(
        db,
        current_user=current_user,
        company_id=company_id,
        search=search,
    )
    return apply_sorting(
        query,
        sort_by=sort_by,
        sort_dir=sort_dir,
        sort_options=sort_options,
        default_order=default_order,
    ).all()


def get_mis_summary(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    months: int = 6,
    top_limit: int = 6,
) -> dict[str, object]:
    scoped_company_id = resolve_company_scope(current_user, company_id)
    search_term = f"%{search.strip()}%" if search and search.strip() else None
    month_count = max(int(months or 0), 1)
    row_limit = max(int(top_limit or 0), 1)
    today = date.today()
    current_month_start = today.replace(day=1)
    previous_month_start = _shift_month(current_month_start, -1)
    month_starts = [
        _shift_month(current_month_start, offset)
        for offset in range(-(month_count - 1), 1)
    ]
    month_lookup = {
        month_start.strftime("%Y-%m"): month_start for month_start in month_starts
    }
    overdue_cutoff = today - timedelta(days=30)

    project_ids_query = (
        db.query(Project.id)
        .join(Company, Company.id == Project.company_id)
        .outerjoin(Contract, Contract.project_id == Project.id)
        .outerjoin(Vendor, Vendor.id == Contract.vendor_id)
        .filter(Project.is_deleted.is_(False))
    )
    project_ids_query = apply_project_company_scope(project_ids_query, scoped_company_id)
    if status_filter:
        project_ids_query = project_ids_query.filter(
            Project.status == status_filter.strip().lower()
        )
    if search_term:
        project_ids_query = project_ids_query.filter(
            or_(
                Company.name.ilike(search_term),
                Project.name.ilike(search_term),
                Project.code.ilike(search_term),
                Project.client_name.ilike(search_term),
                Project.location.ilike(search_term),
                Contract.contract_no.ilike(search_term),
                Contract.title.ilike(search_term),
                Vendor.name.ilike(search_term),
            )
        )

    project_ids = [row[0] for row in project_ids_query.distinct().all()]
    projects = []
    if project_ids:
        projects = (
            db.query(Project)
            .options(
                selectinload(Project.contracts)
                .selectinload(Contract.ra_bills)
                .selectinload(RABill.payment_allocations),
                selectinload(Project.contracts)
                .selectinload(Contract.ra_bills)
                .selectinload(RABill.deductions),
                selectinload(Project.contracts).selectinload(Contract.payments),
                selectinload(Project.contracts).selectinload(Contract.secured_advances),
            )
            .filter(Project.id.in_(project_ids))
            .all()
        )

    project_count = len(projects)
    active_project_count = sum(1 for project in projects if project.status == "active")
    active_contract_count = 0
    outstanding_payable = 0.0
    overdue_vendor_bill_amount = 0.0
    overdue_pending_payment_amount = 0.0
    retention_held_amount = 0.0
    secured_advance_outstanding = 0.0
    status_counter: Counter[str] = Counter()
    monthly_billed: defaultdict[str, float] = defaultdict(float)
    monthly_released: defaultdict[str, float] = defaultdict(float)
    monthly_retention: defaultdict[str, float] = defaultdict(float)
    top_outstanding_projects: list[dict[str, object]] = []

    for project in projects:
        status_counter[project.status] += 1
        project_billed = 0.0
        project_released = 0.0
        project_outstanding = 0.0
        project_active_contract_count = 0

        for contract in project.contracts or []:
            if getattr(contract, "is_deleted", False):
                continue
            if contract.status == "active":
                active_contract_count += 1
                project_active_contract_count += 1

            for bill in contract.ra_bills or []:
                if bill.status not in PROJECT_COST_BILLED_STATUSES:
                    continue

                bill_amount = round(float(bill.net_payable or 0), 2)
                paid_amount = round(
                    sum(
                        float(allocation.amount or 0)
                        for allocation in bill.payment_allocations or []
                    ),
                    2,
                )
                outstanding_amount = (
                    round(max(bill_amount - paid_amount, 0), 2)
                    if bill.status in {"approved", "partially_paid", "paid"}
                    else 0.0
                )

                project_billed += bill_amount
                project_outstanding += outstanding_amount
                outstanding_payable += outstanding_amount

                if (
                    bill.bill_date is not None
                    and bill.bill_date <= overdue_cutoff
                    and outstanding_amount > 0
                    and bill.status in {"approved", "partially_paid", "paid"}
                ):
                    overdue_vendor_bill_amount += outstanding_amount

                if bill.bill_date is not None:
                    month_key = bill.bill_date.strftime("%Y-%m")
                    if month_key in month_lookup:
                        monthly_billed[month_key] += bill_amount

                for deduction in bill.deductions or []:
                    if deduction.deduction_type != "retention":
                        continue
                    deduction_amount = round(float(deduction.amount or 0), 2)
                    retention_held_amount += deduction_amount
                    if bill.bill_date is not None:
                        month_key = bill.bill_date.strftime("%Y-%m")
                        if month_key in month_lookup:
                            monthly_retention[month_key] += deduction_amount

            for payment in contract.payments or []:
                payment_amount = round(float(payment.amount or 0), 2)
                if payment.status == "released":
                    project_released += payment_amount
                    if payment.payment_date is not None:
                        month_key = payment.payment_date.strftime("%Y-%m")
                        if month_key in month_lookup:
                            monthly_released[month_key] += payment_amount
                elif (
                    payment.status in PENDING_PAYMENT_STATUSES
                    and payment.payment_date is not None
                    and payment.payment_date <= overdue_cutoff
                ):
                    overdue_pending_payment_amount += payment_amount

            for secured_advance in contract.secured_advances or []:
                if getattr(secured_advance, "is_archived", False):
                    continue
                secured_advance_outstanding += round(
                    max(float(secured_advance.balance or 0), 0.0),
                    2,
                )

        top_outstanding_projects.append(
            {
                "project_id": project.id,
                "project_name": project.name,
                "project_code": project.code,
                "status": project.status,
                "billed_amount": round(project_billed, 2),
                "released_amount": round(project_released, 2),
                "outstanding_amount": round(project_outstanding, 2),
                "active_contract_count": project_active_contract_count,
            }
        )

    current_month_key = current_month_start.strftime("%Y-%m")
    previous_month_key = previous_month_start.strftime("%Y-%m")
    current_month_billed_amount = round(monthly_billed[current_month_key], 2)
    previous_month_billed_amount = round(monthly_billed[previous_month_key], 2)
    current_month_released_amount = round(monthly_released[current_month_key], 2)
    previous_month_released_amount = round(monthly_released[previous_month_key], 2)
    current_month_net_amount = round(
        current_month_billed_amount - current_month_released_amount,
        2,
    )
    previous_month_net_amount = round(
        previous_month_billed_amount - previous_month_released_amount,
        2,
    )
    payment_release_coverage_pct = (
        round(
            (current_month_released_amount * 100.0) / current_month_billed_amount,
            2,
        )
        if current_month_billed_amount > 0
        else 0.0
    )
    monthly_trend = [
        {
            "month": month_start.strftime("%Y-%m"),
            "label": _month_label(month_start),
            "billed_amount": round(monthly_billed[month_start.strftime("%Y-%m")], 2),
            "released_amount": round(monthly_released[month_start.strftime("%Y-%m")], 2),
            "retention_amount": round(monthly_retention[month_start.strftime("%Y-%m")], 2),
            "net_amount": round(
                monthly_billed[month_start.strftime("%Y-%m")]
                - monthly_released[month_start.strftime("%Y-%m")],
                2,
            ),
        }
        for month_start in month_starts
    ]
    status_mix = [
        {"status": status_name, "count": count}
        for status_name, count in sorted(status_counter.items())
    ]
    top_outstanding_projects.sort(
        key=lambda row: (
            float(row["outstanding_amount"]),
            row["project_name"],
        ),
        reverse=True,
    )

    return {
        "summary": {
            "current_month": current_month_key,
            "current_month_label": _month_label(current_month_start),
            "previous_month": previous_month_key,
            "previous_month_label": _month_label(previous_month_start),
            "project_count": project_count,
            "active_project_count": active_project_count,
            "active_contract_count": active_contract_count,
            "current_month_billed_amount": current_month_billed_amount,
            "previous_month_billed_amount": previous_month_billed_amount,
            "current_month_released_amount": current_month_released_amount,
            "previous_month_released_amount": previous_month_released_amount,
            "current_month_net_amount": current_month_net_amount,
            "previous_month_net_amount": previous_month_net_amount,
            "payment_release_coverage_pct": payment_release_coverage_pct,
            "outstanding_payable": round(outstanding_payable, 2),
            "overdue_vendor_bill_amount": round(overdue_vendor_bill_amount, 2),
            "overdue_pending_payment_amount": round(overdue_pending_payment_amount, 2),
            "retention_held_amount": round(retention_held_amount, 2),
            "secured_advance_outstanding": round(secured_advance_outstanding, 2),
        },
        "monthly_trend": monthly_trend,
        "status_mix": status_mix,
        "top_outstanding_projects": top_outstanding_projects[:row_limit],
    }


def get_cash_flow_forecast(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
    search: str | None = None,
    top_limit: int = 6,
    horizon_weeks: int = 8,
    collection_days: int = 30,
) -> dict[str, object]:
    scoped_company_id = resolve_company_scope(current_user, company_id)
    today = date.today()
    horizon_weeks = max(horizon_weeks, 1)
    top_limit = max(top_limit, 1)
    collection_days = max(collection_days, 0)
    horizon_end = today + timedelta(days=(horizon_weeks * 7) - 1)

    bucket_ranges: list[tuple[date, date]] = []
    buckets: list[dict[str, object]] = []
    for index in range(horizon_weeks):
        bucket_start = today + timedelta(days=index * 7)
        bucket_end = bucket_start + timedelta(days=6)
        bucket_ranges.append((bucket_start, bucket_end))
        buckets.append(
            {
                "bucket_start": bucket_start,
                "bucket_end": bucket_end,
                "label": _forecast_bucket_label(bucket_start, bucket_end),
                "receivable_amount": 0.0,
                "payable_amount": 0.0,
                "net_amount": 0.0,
                "cumulative_net_amount": 0.0,
            }
        )

    receivable_query = (
        db.query(
            RABill.id.label("bill_id"),
            RABill.contract_id.label("contract_id"),
            Project.name.label("project_name"),
            Contract.contract_no.label("contract_no"),
            Contract.title.label("contract_title"),
            RABill.bill_no.label("bill_no"),
            RABill.bill_date.label("bill_date"),
            RABill.status.label("status"),
            (
                func.coalesce(RABill.net_payable, 0)
                - func.coalesce(
                    db.query(func.sum(PaymentAllocation.amount))
                    .filter(PaymentAllocation.ra_bill_id == RABill.id)
                    .correlate(RABill)
                    .scalar_subquery(),
                    0,
                )
            ).label("outstanding_amount"),
        )
        .join(Contract, Contract.id == RABill.contract_id)
        .join(Project, Project.id == Contract.project_id)
        .join(Company, Company.id == Project.company_id)
        .outerjoin(Vendor, Vendor.id == Contract.vendor_id)
        .filter(
            Contract.is_deleted.is_(False),
            Project.is_deleted.is_(False),
            RABill.is_archived.is_(False),
            RABill.status.in_(CASH_FLOW_RECEIVABLE_STATUSES),
        )
    )
    receivable_query = apply_project_company_scope(receivable_query, scoped_company_id)

    payment_query = (
        db.query(
            Payment.id.label("payment_id"),
            Payment.contract_id.label("contract_id"),
            Project.name.label("project_name"),
            Contract.contract_no.label("contract_no"),
            Payment.payment_date.label("payment_date"),
            Payment.status.label("status"),
            Payment.amount.label("pending_amount"),
        )
        .join(Contract, Contract.id == Payment.contract_id)
        .join(Project, Project.id == Contract.project_id)
        .join(Company, Company.id == Project.company_id)
        .outerjoin(Vendor, Vendor.id == Contract.vendor_id)
        .filter(
            Contract.is_deleted.is_(False),
            Project.is_deleted.is_(False),
            Payment.is_archived.is_(False),
            Payment.status.in_(PENDING_PAYMENT_STATUSES),
        )
    )
    payment_query = apply_project_company_scope(payment_query, scoped_company_id)

    if search:
        search_term = f"%{search.strip()}%"
        search_filter = or_(
            Contract.contract_no.ilike(search_term),
            Contract.title.ilike(search_term),
            Project.name.ilike(search_term),
            Vendor.name.ilike(search_term),
            Company.name.ilike(search_term),
        )
        receivable_query = receivable_query.filter(search_filter)
        payment_query = payment_query.filter(search_filter)

    total_receivable_pipeline = 0.0
    overdue_receivables = 0.0
    receivables_within_horizon = 0.0
    upcoming_receivables: list[dict[str, object]] = []

    for row in receivable_query.all():
        outstanding_amount = round(float(row.outstanding_amount or 0), 2)
        if outstanding_amount <= 0:
            continue

        total_receivable_pipeline += outstanding_amount
        expected_collection_date = row.bill_date + timedelta(days=collection_days)
        is_overdue = expected_collection_date < today
        forecast_date = today if is_overdue else expected_collection_date

        if is_overdue:
            overdue_receivables += outstanding_amount

        if forecast_date <= horizon_end:
            receivables_within_horizon += outstanding_amount
            for index, (bucket_start, bucket_end) in enumerate(bucket_ranges):
                if bucket_start <= forecast_date <= bucket_end:
                    buckets[index]["receivable_amount"] = round(
                        float(buckets[index]["receivable_amount"]) + outstanding_amount,
                        2,
                    )
                    break

            upcoming_receivables.append(
                {
                    "bill_id": row.bill_id,
                    "contract_id": row.contract_id,
                    "project_name": row.project_name,
                    "contract_no": row.contract_no,
                    "contract_title": row.contract_title,
                    "bill_no": row.bill_no,
                    "bill_date": row.bill_date,
                    "forecast_date": forecast_date,
                    "status": row.status,
                    "outstanding_amount": outstanding_amount,
                    "is_overdue": is_overdue,
                }
            )

    total_payable_pipeline = 0.0
    overdue_payables = 0.0
    payables_within_horizon = 0.0
    upcoming_payments: list[dict[str, object]] = []

    for row in payment_query.all():
        pending_amount = round(float(row.pending_amount or 0), 2)
        if pending_amount <= 0:
            continue

        total_payable_pipeline += pending_amount
        is_overdue = row.payment_date < today
        forecast_date = today if is_overdue else row.payment_date

        if is_overdue:
            overdue_payables += pending_amount

        if forecast_date <= horizon_end:
            payables_within_horizon += pending_amount
            for index, (bucket_start, bucket_end) in enumerate(bucket_ranges):
                if bucket_start <= forecast_date <= bucket_end:
                    buckets[index]["payable_amount"] = round(
                        float(buckets[index]["payable_amount"]) + pending_amount,
                        2,
                    )
                    break

            upcoming_payments.append(
                {
                    "payment_id": row.payment_id,
                    "contract_id": row.contract_id,
                    "project_name": row.project_name,
                    "contract_no": row.contract_no,
                    "payment_date": row.payment_date,
                    "forecast_date": forecast_date,
                    "status": row.status,
                    "pending_amount": pending_amount,
                    "is_overdue": is_overdue,
                }
            )

    upcoming_receivables.sort(
        key=lambda row: (
            row["forecast_date"],
            -float(row["outstanding_amount"]),
            row["project_name"],
            row["contract_no"],
        )
    )
    upcoming_payments.sort(
        key=lambda row: (
            row["forecast_date"],
            -float(row["pending_amount"]),
            row["project_name"],
            row["contract_no"],
        )
    )

    running_net = 0.0
    projected_peak_deficit = 0.0
    projected_peak_surplus = 0.0
    for bucket in buckets:
        receivable_amount = round(float(bucket["receivable_amount"]), 2)
        payable_amount = round(float(bucket["payable_amount"]), 2)
        net_amount = round(receivable_amount - payable_amount, 2)
        running_net = round(running_net + net_amount, 2)
        bucket["receivable_amount"] = receivable_amount
        bucket["payable_amount"] = payable_amount
        bucket["net_amount"] = net_amount
        bucket["cumulative_net_amount"] = running_net
        projected_peak_deficit = min(projected_peak_deficit, running_net)
        projected_peak_surplus = max(projected_peak_surplus, running_net)

    return {
        "summary": {
            "total_receivable_pipeline": round(total_receivable_pipeline, 2),
            "overdue_receivables": round(overdue_receivables, 2),
            "receivables_within_horizon": round(receivables_within_horizon, 2),
            "total_payable_pipeline": round(total_payable_pipeline, 2),
            "overdue_payables": round(overdue_payables, 2),
            "payables_within_horizon": round(payables_within_horizon, 2),
            "projected_net_flow": round(
                receivables_within_horizon - payables_within_horizon, 2
            ),
            "projected_peak_deficit": round(projected_peak_deficit, 2),
            "projected_peak_surplus": round(projected_peak_surplus, 2),
        },
        "buckets": buckets,
        "upcoming_receivables": upcoming_receivables[:top_limit],
        "upcoming_payments": upcoming_payments[:top_limit],
    }


def _material_consumption_rows(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
) -> list[dict[str, object]]:
    scoped_company_id = resolve_company_scope(current_user, company_id)
    search_term = f"%{search.strip()}%" if search and search.strip() else None

    def _apply_project_filters(query):
        query = apply_project_company_scope(query, scoped_company_id)
        if status_filter:
            query = query.filter(Project.status == status_filter.strip().lower())
        if search_term:
            query = query.filter(
                or_(
                    Project.name.ilike(search_term),
                    Project.code.ilike(search_term),
                    Company.name.ilike(search_term),
                    Material.item_code.ilike(search_term),
                    Material.item_name.ilike(search_term),
                    Material.category.ilike(search_term),
                )
            )
        return query

    requisition_rows = _apply_project_filters(
        db.query(
            Company.name.label("company_name"),
            Project.id.label("project_id"),
            Project.name.label("project_name"),
            Project.code.label("project_code"),
            Material.id.label("material_id"),
            Material.item_code.label("material_code"),
            Material.item_name.label("material_name"),
            Material.category.label("category"),
            Material.unit.label("unit"),
            Material.default_rate.label("default_rate"),
            func.coalesce(func.sum(MaterialRequisitionItem.requested_qty), 0).label("requested_qty"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            MaterialRequisition.status.in_(
                                MATERIAL_REQUIRED_REQUISITION_STATUSES
                            ),
                            MaterialRequisitionItem.approved_qty,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("required_qty"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            MaterialRequisition.status.in_(
                                MATERIAL_REQUIRED_REQUISITION_STATUSES
                            ),
                            MaterialRequisitionItem.issued_qty,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("requisition_issued_qty"),
        )
        .join(
            MaterialRequisitionItem,
            MaterialRequisitionItem.requisition_id == MaterialRequisition.id,
        )
        .join(Project, Project.id == MaterialRequisition.project_id)
        .join(Company, Company.id == Project.company_id)
        .join(Material, Material.id == MaterialRequisitionItem.material_id)
        .filter(
            Project.is_deleted.is_(False),
            MaterialRequisition.status.notin_(["rejected", "cancelled"]),
        )
        .group_by(
            Company.name,
            Project.id,
            Project.name,
            Project.code,
            Material.id,
            Material.item_code,
            Material.item_name,
            Material.category,
            Material.unit,
            Material.default_rate,
        )
    ).all()

    issue_rows = _apply_project_filters(
        db.query(
            Company.name.label("company_name"),
            Project.id.label("project_id"),
            Project.name.label("project_name"),
            Project.code.label("project_code"),
            Material.id.label("material_id"),
            Material.item_code.label("material_code"),
            Material.item_name.label("material_name"),
            Material.category.label("category"),
            Material.unit.label("unit"),
            Material.default_rate.label("default_rate"),
            func.coalesce(func.sum(MaterialIssueItem.issued_qty), 0).label("issued_qty"),
            func.coalesce(func.sum(MaterialIssueItem.line_amount), 0).label("issued_amount"),
        )
        .join(MaterialIssueItem, MaterialIssueItem.issue_id == MaterialIssue.id)
        .join(Project, Project.id == MaterialIssue.project_id)
        .join(Company, Company.id == Project.company_id)
        .join(Material, Material.id == MaterialIssueItem.material_id)
        .filter(
            Project.is_deleted.is_(False),
            MaterialIssue.status == "issued",
        )
        .group_by(
            Company.name,
            Project.id,
            Project.name,
            Project.code,
            Material.id,
            Material.item_code,
            Material.item_name,
            Material.category,
            Material.unit,
            Material.default_rate,
        )
    ).all()

    wastage_rows = _apply_project_filters(
        db.query(
            Company.name.label("company_name"),
            Project.id.label("project_id"),
            Project.name.label("project_name"),
            Project.code.label("project_code"),
            Material.id.label("material_id"),
            Material.item_code.label("material_code"),
            Material.item_name.label("material_name"),
            Material.category.label("category"),
            Material.unit.label("unit"),
            Material.default_rate.label("default_rate"),
            func.coalesce(func.sum(-MaterialStockAdjustmentItem.qty_change), 0).label(
                "wastage_qty"
            ),
            func.coalesce(func.sum(MaterialStockAdjustmentItem.line_amount), 0).label(
                "wastage_amount"
            ),
        )
        .join(
            MaterialStockAdjustmentItem,
            MaterialStockAdjustmentItem.adjustment_id == MaterialStockAdjustment.id,
        )
        .join(Project, Project.id == MaterialStockAdjustment.project_id)
        .join(Company, Company.id == Project.company_id)
        .join(Material, Material.id == MaterialStockAdjustmentItem.material_id)
        .filter(
            Project.is_deleted.is_(False),
            MaterialStockAdjustment.status == "posted",
            MaterialStockAdjustmentItem.qty_change < 0,
        )
        .group_by(
            Company.name,
            Project.id,
            Project.name,
            Project.code,
            Material.id,
            Material.item_code,
            Material.item_name,
            Material.category,
            Material.unit,
            Material.default_rate,
        )
    ).all()

    details_by_key: dict[tuple[int, int], dict[str, object]] = {}
    requisition_by_key: dict[tuple[int, int], dict[str, float]] = {}
    issue_by_key: dict[tuple[int, int], dict[str, float]] = {}
    wastage_by_key: dict[tuple[int, int], dict[str, float]] = {}

    def _capture_details(row) -> tuple[int, int]:
        key = (int(row.project_id), int(row.material_id))
        details_by_key.setdefault(
            key,
            {
                "company_name": row.company_name,
                "project_id": int(row.project_id),
                "project_name": row.project_name,
                "project_code": row.project_code,
                "material_id": int(row.material_id),
                "material_code": row.material_code,
                "material_name": row.material_name,
                "category": row.category,
                "unit": row.unit,
                "default_rate": round(float(row.default_rate or 0), 2),
            },
        )
        return key

    for row in requisition_rows:
        key = _capture_details(row)
        requisition_by_key[key] = {
            "requested_qty": round(float(row.requested_qty or 0), 3),
            "required_qty": round(float(row.required_qty or 0), 3),
            "requisition_issued_qty": round(float(row.requisition_issued_qty or 0), 3),
        }

    for row in issue_rows:
        key = _capture_details(row)
        issue_by_key[key] = {
            "issued_qty": round(float(row.issued_qty or 0), 3),
            "issued_amount": round(float(row.issued_amount or 0), 2),
        }

    for row in wastage_rows:
        key = _capture_details(row)
        wastage_by_key[key] = {
            "wastage_qty": round(float(row.wastage_qty or 0), 3),
            "wastage_amount": round(float(row.wastage_amount or 0), 2),
        }

    rows: list[dict[str, object]] = []
    for key, details in details_by_key.items():
        requisition_metrics = requisition_by_key.get(key, {})
        issue_metrics = issue_by_key.get(key, {})
        wastage_metrics = wastage_by_key.get(key, {})

        requested_qty = float(requisition_metrics.get("requested_qty", 0))
        required_qty = float(requisition_metrics.get("required_qty", 0))
        requisition_issued_qty = float(requisition_metrics.get("requisition_issued_qty", 0))
        issued_qty = float(issue_metrics.get("issued_qty", 0))
        wastage_qty = float(wastage_metrics.get("wastage_qty", 0))
        issued_amount = float(issue_metrics.get("issued_amount", 0))
        wastage_amount = float(wastage_metrics.get("wastage_amount", 0))
        default_rate = float(details["default_rate"])
        required_amount = round(required_qty * default_rate, 2)
        balance_to_issue_qty = round(max(required_qty - issued_qty, 0), 3)
        excess_issue_qty = round(max(issued_qty - required_qty, 0), 3)
        issue_coverage_pct = round((issued_qty * 100.0) / required_qty, 2) if required_qty > 0 else 0.0
        wastage_pct = round((wastage_qty * 100.0) / issued_qty, 2) if issued_qty > 0 else 0.0

        if (
            requested_qty <= 0
            and required_qty <= 0
            and issued_qty <= 0
            and wastage_qty <= 0
        ):
            continue

        rows.append(
            {
                "company_name": details["company_name"],
                "project_id": details["project_id"],
                "project_name": details["project_name"],
                "project_code": details["project_code"],
                "material_id": details["material_id"],
                "material_code": details["material_code"],
                "material_name": details["material_name"],
                "category": details["category"],
                "unit": details["unit"],
                "requested_qty": round(requested_qty, 3),
                "required_qty": round(required_qty, 3),
                "requisition_issued_qty": round(requisition_issued_qty, 3),
                "issued_qty": round(issued_qty, 3),
                "wastage_qty": round(wastage_qty, 3),
                "balance_to_issue_qty": balance_to_issue_qty,
                "excess_issue_qty": excess_issue_qty,
                "issue_coverage_pct": issue_coverage_pct,
                "wastage_pct": wastage_pct,
                "required_amount": required_amount,
                "issued_amount": round(issued_amount, 2),
                "wastage_amount": round(wastage_amount, 2),
            }
        )

    return rows


def get_material_consumption_report(
    db: Session,
    *,
    current_user: User,
    pagination: PaginationParams,
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: SortDirection = SortDirection.DESC,
) -> dict[str, object]:
    rows = _sort_material_consumption_rows(
        _material_consumption_rows(
            db,
            current_user=current_user,
            company_id=company_id,
            status_filter=status_filter,
            search=search,
        ),
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

    total_required_qty = round(sum(float(row["required_qty"]) for row in rows), 3)
    total_issued_qty = round(sum(float(row["issued_qty"]) for row in rows), 3)
    total_wastage_qty = round(sum(float(row["wastage_qty"]) for row in rows), 3)
    total_balance_to_issue_qty = round(
        sum(float(row["balance_to_issue_qty"]) for row in rows), 3
    )
    total_excess_issue_qty = round(
        sum(float(row["excess_issue_qty"]) for row in rows), 3
    )
    total_required_amount = round(
        sum(float(row["required_amount"]) for row in rows), 2
    )
    total_issued_amount = round(sum(float(row["issued_amount"]) for row in rows), 2)
    total_wastage_amount = round(
        sum(float(row["wastage_amount"]) for row in rows), 2
    )
    overall_wastage_pct = (
        round((total_wastage_qty * 100.0) / total_issued_qty, 2)
        if total_issued_qty > 0
        else 0.0
    )

    project_rollup_map: dict[int, dict[str, object]] = {}
    for row in rows:
        project_id = int(row["project_id"])
        rollup = project_rollup_map.setdefault(
            project_id,
            {
                "project_id": project_id,
                "company_name": row["company_name"],
                "project_name": row["project_name"],
                "project_code": row["project_code"],
                "required_qty": 0.0,
                "issued_qty": 0.0,
                "wastage_qty": 0.0,
                "required_amount": 0.0,
                "issued_amount": 0.0,
                "wastage_amount": 0.0,
            },
        )
        for field in (
            "required_qty",
            "issued_qty",
            "wastage_qty",
            "required_amount",
            "issued_amount",
            "wastage_amount",
        ):
            rollup[field] = round(
                float(rollup[field]) + float(row[field]),
                3 if field.endswith("_qty") else 2,
            )

    top_wastage_projects = sorted(
        project_rollup_map.values(),
        key=lambda row: (
            float(row["wastage_amount"]),
            float(row["issued_amount"]),
            _material_string(row["project_name"]),
        ),
        reverse=True,
    )[:6]
    watchlist = sorted(
        rows,
        key=lambda row: (
            float(row["wastage_amount"]),
            float(row["excess_issue_qty"]),
            _material_string(row["project_name"]),
            _material_string(row["material_name"]),
        ),
        reverse=True,
    )[:5]
    paginated = paginate_sequence(rows, pagination=pagination)

    return {
        "summary": {
            "total_required_qty": total_required_qty,
            "total_issued_qty": total_issued_qty,
            "total_wastage_qty": total_wastage_qty,
            "total_balance_to_issue_qty": total_balance_to_issue_qty,
            "total_excess_issue_qty": total_excess_issue_qty,
            "total_required_amount": total_required_amount,
            "total_issued_amount": total_issued_amount,
            "total_wastage_amount": total_wastage_amount,
            "overall_wastage_pct": overall_wastage_pct,
        },
        "top_wastage_projects": top_wastage_projects,
        "watchlist": watchlist,
        "items": paginated["items"],
        "total": paginated["total"],
        "page": paginated["page"],
        "limit": paginated["limit"],
    }


def list_material_consumption_report_for_export(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: SortDirection = SortDirection.DESC,
) -> list[dict[str, object]]:
    return _sort_material_consumption_rows(
        _material_consumption_rows(
            db,
            current_user=current_user,
            company_id=company_id,
            status_filter=status_filter,
            search=search,
        ),
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


def _labour_productivity_status(gap_pct: float) -> str:
    if gap_pct <= -LABOUR_PRODUCTIVITY_BENCHMARK_VARIANCE_THRESHOLD:
        return "below_benchmark"
    if gap_pct >= LABOUR_PRODUCTIVITY_BENCHMARK_VARIANCE_THRESHOLD:
        return "above_benchmark"
    return "near_benchmark"


def _labour_output_trend_status(recent_output_qty: float, prior_output_qty: float) -> str:
    if prior_output_qty <= 0 and recent_output_qty > 0:
        return "new_activity"

    baseline = prior_output_qty if prior_output_qty > 0 else 1.0
    change_pct = ((recent_output_qty - prior_output_qty) * 100.0) / baseline
    if change_pct >= 10:
        return "up"
    if change_pct <= -10:
        return "down"
    return "flat"


def _sort_labour_productivity_rows(
    rows: list[dict[str, object]],
    *,
    sort_by: str | None,
    sort_dir: SortDirection,
) -> list[dict[str, object]]:
    selected = sort_by or "productivity_gap_pct"
    reverse = sort_dir == SortDirection.DESC
    string_fields = {
        "trade",
        "unit",
        "trade_label",
        "benchmark_status",
        "output_trend_status",
    }
    numeric_fields = {
        "record_count",
        "project_count",
        "contract_count",
        "recent_output_qty",
        "prior_output_qty",
        "output_change_pct",
        "recent_labour_count",
        "benchmark_labour_count",
        "recent_productivity",
        "benchmark_productivity",
        "productivity_gap",
        "productivity_gap_pct",
        "productivity_index",
    }

    if selected in string_fields:
        return sorted(
            rows,
            key=lambda row: (
                _material_string(row.get(selected)),
                _material_string(row.get("trade_label")),
            ),
            reverse=reverse,
        )

    if selected == "last_entry_date":
        return sorted(
            rows,
            key=lambda row: (
                row.get("last_entry_date") or date.min,
                _material_string(row.get("trade_label")),
            ),
            reverse=reverse,
        )

    if selected in numeric_fields:
        return sorted(
            rows,
            key=lambda row: (
                float(row.get(selected) or 0),
                float(row.get("recent_labour_count") or 0),
                _material_string(row.get("trade_label")),
            ),
            reverse=reverse,
        )

    return sorted(
        rows,
        key=lambda row: (
            float(row.get("productivity_gap_pct") or 0),
            -float(row.get("recent_labour_count") or 0),
            _material_string(row.get("trade_label")),
        ),
    )


def _labour_productivity_rollup(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    window_days: int = 56,
    benchmark_days: int = 84,
) -> dict[str, object]:
    scoped_company_id = resolve_company_scope(current_user, company_id)
    search_term = f"%{search.strip()}%" if search and search.strip() else None

    current_period_end = date.today()
    current_period_start = current_period_end - timedelta(days=max(window_days, 1) - 1)
    benchmark_period_end = current_period_start - timedelta(days=1)
    benchmark_period_start = benchmark_period_end - timedelta(days=max(benchmark_days, 1) - 1)
    prior_period_start = current_period_start - timedelta(days=max(window_days, 1))
    prior_period_end = current_period_start - timedelta(days=1)

    query = (
        db.query(
            Project.id.label("project_id"),
            Contract.id.label("contract_id"),
            Company.name.label("company_name"),
            Project.name.label("project_name"),
            Project.code.label("project_code"),
            Contract.contract_no.label("contract_no"),
            Contract.title.label("contract_title"),
            LabourProductivity.trade.label("trade"),
            LabourProductivity.unit.label("unit"),
            LabourProductivity.remarks.label("remarks"),
            LabourProductivity.productivity_date.label("productivity_date"),
            LabourProductivity.quantity_done.label("quantity_done"),
            LabourProductivity.labour_count.label("labour_count"),
        )
        .join(Project, Project.id == LabourProductivity.project_id)
        .join(Company, Company.id == Project.company_id)
        .outerjoin(Contract, Contract.id == LabourProductivity.contract_id)
        .filter(
            Project.is_deleted.is_(False),
            LabourProductivity.productivity_date >= benchmark_period_start,
            LabourProductivity.productivity_date <= current_period_end,
        )
    )
    query = apply_project_company_scope(query, scoped_company_id)
    if status_filter:
        query = query.filter(Project.status == status_filter.strip().lower())
    if search_term:
        query = query.filter(
            or_(
                Company.name.ilike(search_term),
                Project.name.ilike(search_term),
                Project.code.ilike(search_term),
                Contract.contract_no.ilike(search_term),
                Contract.title.ilike(search_term),
                LabourProductivity.trade.ilike(search_term),
                LabourProductivity.unit.ilike(search_term),
                LabourProductivity.remarks.ilike(search_term),
            )
        )

    grouped_rows: dict[tuple[str, str], dict[str, object]] = {}
    recent_project_ids: set[int] = set()
    recent_records_logged = 0
    recent_crew_days_logged = 0

    for record in query.all():
        productivity_date = record.productivity_date
        if productivity_date is None:
            continue

        trade_display = (record.trade or "").strip()
        if not trade_display:
            continue
        unit_display = (record.unit or "").strip() or "unit"
        key = (trade_display.lower(), unit_display.lower())
        row = grouped_rows.setdefault(
            key,
            {
                "trade": trade_display,
                "unit": unit_display,
                "trade_label": f"{trade_display} ({unit_display})",
                "record_count": 0,
                "recent_output_qty": 0.0,
                "prior_output_qty": 0.0,
                "recent_labour_count": 0,
                "benchmark_labour_count": 0,
                "last_entry_date": productivity_date,
                "_benchmark_output_qty": 0.0,
                "_project_ids": set(),
                "_contract_ids": set(),
                "_recent_record_count": 0,
            },
        )

        if productivity_date >= row["last_entry_date"]:
            row["trade"] = trade_display
            row["unit"] = unit_display
            row["trade_label"] = f"{trade_display} ({unit_display})"
            row["last_entry_date"] = productivity_date

        row["record_count"] = int(row["record_count"]) + 1
        cast_project_ids = row["_project_ids"]
        if isinstance(cast_project_ids, set):
            cast_project_ids.add(int(record.project_id))
        if record.contract_id is not None:
            cast_contract_ids = row["_contract_ids"]
            if isinstance(cast_contract_ids, set):
                cast_contract_ids.add(int(record.contract_id))

        quantity_done = round(float(record.quantity_done or 0), 3)
        labour_count = int(record.labour_count or 0)

        if productivity_date >= current_period_start:
            row["recent_output_qty"] = round(
                float(row["recent_output_qty"]) + quantity_done,
                3,
            )
            row["recent_labour_count"] = int(row["recent_labour_count"]) + labour_count
            row["_recent_record_count"] = int(row["_recent_record_count"]) + 1
            recent_project_ids.add(int(record.project_id))
            recent_records_logged += 1
            recent_crew_days_logged += labour_count
        else:
            row["_benchmark_output_qty"] = round(
                float(row["_benchmark_output_qty"]) + quantity_done,
                3,
            )
            row["benchmark_labour_count"] = (
                int(row["benchmark_labour_count"]) + labour_count
            )

        if prior_period_start <= productivity_date <= prior_period_end:
            row["prior_output_qty"] = round(
                float(row["prior_output_qty"]) + quantity_done,
                3,
            )

    rows: list[dict[str, object]] = []
    for grouped in grouped_rows.values():
        recent_record_count = int(grouped.pop("_recent_record_count"))
        if recent_record_count <= 0:
            continue

        project_ids = grouped.pop("_project_ids")
        contract_ids = grouped.pop("_contract_ids")
        benchmark_output_qty = float(grouped.pop("_benchmark_output_qty"))
        recent_output_qty = float(grouped["recent_output_qty"])
        prior_output_qty = float(grouped["prior_output_qty"])
        recent_labour_count = int(grouped["recent_labour_count"])
        benchmark_labour_count = int(grouped["benchmark_labour_count"])
        recent_productivity = (
            round(recent_output_qty / recent_labour_count, 3)
            if recent_labour_count > 0
            else 0.0
        )
        benchmark_productivity = (
            round(benchmark_output_qty / benchmark_labour_count, 3)
            if benchmark_labour_count > 0
            else recent_productivity
        )
        productivity_gap = round(
            recent_productivity - benchmark_productivity,
            3,
        )
        productivity_gap_pct = (
            round((productivity_gap * 100.0) / benchmark_productivity, 2)
            if benchmark_productivity > 0
            else 0.0
        )
        productivity_index = (
            round((recent_productivity * 100.0) / benchmark_productivity, 2)
            if benchmark_productivity > 0
            else 100.0
        )
        if prior_output_qty > 0:
            output_change_pct = round(
                ((recent_output_qty - prior_output_qty) * 100.0) / prior_output_qty,
                2,
            )
        elif recent_output_qty > 0:
            output_change_pct = 100.0
        else:
            output_change_pct = 0.0

        rows.append(
            {
                "trade": grouped["trade"],
                "unit": grouped["unit"],
                "trade_label": grouped["trade_label"],
                "record_count": int(grouped["record_count"]),
                "project_count": len(project_ids) if isinstance(project_ids, set) else 0,
                "contract_count": len(contract_ids) if isinstance(contract_ids, set) else 0,
                "recent_output_qty": round(recent_output_qty, 3),
                "prior_output_qty": round(prior_output_qty, 3),
                "output_change_pct": output_change_pct,
                "recent_labour_count": recent_labour_count,
                "benchmark_labour_count": benchmark_labour_count,
                "recent_productivity": recent_productivity,
                "benchmark_productivity": benchmark_productivity,
                "productivity_gap": productivity_gap,
                "productivity_gap_pct": productivity_gap_pct,
                "productivity_index": productivity_index,
                "benchmark_status": _labour_productivity_status(productivity_gap_pct),
                "output_trend_status": _labour_output_trend_status(
                    recent_output_qty,
                    prior_output_qty,
                ),
                "last_entry_date": grouped["last_entry_date"],
            }
        )

    return {
        "current_period_start": current_period_start,
        "current_period_end": current_period_end,
        "benchmark_period_start": benchmark_period_start,
        "benchmark_period_end": benchmark_period_end,
        "records_logged": recent_records_logged,
        "crew_days_logged": recent_crew_days_logged,
        "projects_covered": len(recent_project_ids),
        "rows": rows,
    }


def get_labour_productivity_report(
    db: Session,
    *,
    current_user: User,
    pagination: PaginationParams,
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    window_days: int = 56,
    benchmark_days: int = 84,
    sort_by: str | None = None,
    sort_dir: SortDirection = SortDirection.ASC,
) -> dict[str, object]:
    rollup = _labour_productivity_rollup(
        db,
        current_user=current_user,
        company_id=company_id,
        status_filter=status_filter,
        search=search,
        window_days=window_days,
        benchmark_days=benchmark_days,
    )
    rows = _sort_labour_productivity_rows(
        rollup["rows"],
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    below_benchmark_groups = sum(
        1 for row in rows if row["benchmark_status"] == "below_benchmark"
    )
    active_trade_groups = len(rows)
    benchmark_hit_rate_pct = (
        round(
            ((active_trade_groups - below_benchmark_groups) * 100.0)
            / active_trade_groups,
            2,
        )
        if active_trade_groups > 0
        else 0.0
    )
    benchmark_focus = sorted(
        rows,
        key=lambda row: (
            float(row["recent_labour_count"]),
            float(row["record_count"]),
            _material_string(row["trade_label"]),
        ),
        reverse=True,
    )[:6]
    watchlist = sorted(
        [
            row
            for row in rows
            if row["benchmark_status"] == "below_benchmark"
        ],
        key=lambda row: (
            float(row["productivity_gap_pct"]),
            -float(row["recent_labour_count"]),
            _material_string(row["trade_label"]),
        ),
    )[:5]
    paginated = paginate_sequence(rows, pagination=pagination)

    return {
        "summary": {
            "current_period_start": rollup["current_period_start"],
            "current_period_end": rollup["current_period_end"],
            "benchmark_period_start": rollup["benchmark_period_start"],
            "benchmark_period_end": rollup["benchmark_period_end"],
            "records_logged": rollup["records_logged"],
            "crew_days_logged": rollup["crew_days_logged"],
            "active_trade_groups": active_trade_groups,
            "projects_covered": rollup["projects_covered"],
            "below_benchmark_groups": below_benchmark_groups,
            "benchmark_hit_rate_pct": benchmark_hit_rate_pct,
        },
        "benchmark_focus": benchmark_focus,
        "watchlist": watchlist,
        "items": paginated["items"],
        "total": paginated["total"],
        "page": paginated["page"],
        "limit": paginated["limit"],
    }


def list_labour_productivity_report_for_export(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    window_days: int = 56,
    benchmark_days: int = 84,
    sort_by: str | None = None,
    sort_dir: SortDirection = SortDirection.ASC,
) -> list[dict[str, object]]:
    rollup = _labour_productivity_rollup(
        db,
        current_user=current_user,
        company_id=company_id,
        status_filter=status_filter,
        search=search,
        window_days=window_days,
        benchmark_days=benchmark_days,
    )
    return _sort_labour_productivity_rows(
        rollup["rows"],
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


# ===========================================================================
# WBS (Work Breakdown Structure) report
# ===========================================================================

from app.models.boq import BOQItem
from app.models.ra_bill_item import RABillItem
from app.models.work_done import WorkDoneItem

_WBS_SORT_NUMERIC_COLS = {
    "boq_quantity",
    "boq_rate",
    "boq_amount",
    "work_done_quantity",
    "work_done_amount",
    "billed_quantity",
    "billed_amount",
    "remaining_quantity",
    "remaining_amount",
    "completion_pct",
}
_WBS_SORT_STRING_COLS = {
    "company_name",
    "project_name",
    "project_code",
    "contract_no",
    "contract_title",
    "vendor_name",
    "item_code",
    "description",
    "unit",
    "category",
}


def _wbs_report_rows(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
    contract_id: int | None = None,
    search: str | None = None,
) -> list[dict[str, object]]:
    """Build flat WBS rows with BOQ + work-done + billed quantities per item."""
    scope_company_id = company_id or resolve_company_scope(current_user)

    # Work-done cumulative by BOQ item (latest cumulative_quantity per boq_item_id)
    wd_sub = (
        db.query(
            WorkDoneItem.boq_item_id,
            func.max(WorkDoneItem.cumulative_quantity).label("wd_cumulative_qty"),
            func.sum(WorkDoneItem.amount).label("wd_amount"),
        )
        .group_by(WorkDoneItem.boq_item_id)
        .subquery("wd_sub")
    )

    # Billed cumulative by BOQ item (latest cumulative from RA bill items)
    billed_sub = (
        db.query(
            RABillItem.boq_item_id,
            func.max(RABillItem.cumulative_quantity).label("billed_cumulative_qty"),
            func.sum(RABillItem.amount).label("billed_amount"),
        )
        .group_by(RABillItem.boq_item_id)
        .subquery("billed_sub")
    )

    query = (
        db.query(
            BOQItem.id.label("boq_item_id"),
            BOQItem.contract_id,
            BOQItem.item_code,
            BOQItem.description,
            BOQItem.unit,
            BOQItem.category,
            BOQItem.quantity.label("boq_quantity"),
            BOQItem.rate.label("boq_rate"),
            BOQItem.amount.label("boq_amount"),
            func.coalesce(wd_sub.c.wd_cumulative_qty, 0).label("work_done_quantity"),
            func.coalesce(wd_sub.c.wd_amount, 0).label("work_done_amount"),
            func.coalesce(billed_sub.c.billed_cumulative_qty, 0).label("billed_quantity"),
            func.coalesce(billed_sub.c.billed_amount, 0).label("billed_amount"),
            Contract.id.label("contract_id_fk"),
            Contract.contract_no,
            Contract.title.label("contract_title"),
            Project.id.label("project_id"),
            Project.name.label("project_name"),
            Project.code.label("project_code"),
            Company.name.label("company_name"),
            func.coalesce(Vendor.name, Contract.client_name, "Client contract").label("vendor_name"),
        )
        .join(Contract, Contract.id == BOQItem.contract_id)
        .join(Project, Project.id == Contract.project_id)
        .join(Company, Company.id == Project.company_id)
        .outerjoin(Vendor, Vendor.id == Contract.vendor_id)
        .outerjoin(wd_sub, wd_sub.c.boq_item_id == BOQItem.id)
        .outerjoin(billed_sub, billed_sub.c.boq_item_id == BOQItem.id)
    )

    query = apply_project_company_scope(query, scope_company_id)

    if contract_id:
        query = query.filter(Contract.id == contract_id)

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                BOQItem.item_code.ilike(term),
                BOQItem.description.ilike(term),
                BOQItem.category.ilike(term),
                Contract.contract_no.ilike(term),
                Project.name.ilike(term),
            )
        )

    raw_rows = query.all()

    rows: list[dict[str, object]] = []
    for r in raw_rows:
        boq_qty = float(r.boq_quantity or 0)
        boq_rate = float(r.boq_rate or 0)
        boq_amount = float(r.boq_amount or 0)
        wd_qty = float(r.work_done_quantity or 0)
        wd_amount = float(r.work_done_amount or 0)
        billed_qty = float(r.billed_quantity or 0)
        billed_amount = float(r.billed_amount or 0)
        remaining_qty = max(boq_qty - wd_qty, 0.0)
        remaining_amount = max(boq_amount - wd_amount, 0.0)
        completion_pct = round((wd_qty / boq_qty) * 100.0, 2) if boq_qty > 0 else 0.0

        rows.append(
            {
                "boq_item_id": r.boq_item_id,
                "contract_id": r.contract_id,
                "project_id": r.project_id,
                "company_name": str(r.company_name or ""),
                "project_name": str(r.project_name or ""),
                "project_code": r.project_code,
                "contract_no": str(r.contract_no or ""),
                "contract_title": str(r.contract_title or ""),
                "vendor_name": str(r.vendor_name or ""),
                "item_code": r.item_code,
                "description": str(r.description or ""),
                "unit": str(r.unit or ""),
                "category": r.category or "Uncategorised",
                "boq_quantity": round(boq_qty, 3),
                "boq_rate": round(boq_rate, 2),
                "boq_amount": round(boq_amount, 2),
                "work_done_quantity": round(wd_qty, 3),
                "work_done_amount": round(wd_amount, 2),
                "billed_quantity": round(billed_qty, 3),
                "billed_amount": round(billed_amount, 2),
                "remaining_quantity": round(remaining_qty, 3),
                "remaining_amount": round(remaining_amount, 2),
                "completion_pct": completion_pct,
            }
        )

    return rows


def _sort_wbs_rows(
    rows: list[dict[str, object]],
    *,
    sort_by: str | None,
    sort_dir: SortDirection,
) -> list[dict[str, object]]:
    selected = sort_by or "remaining_amount"
    reverse = sort_dir == SortDirection.DESC

    if selected in _WBS_SORT_NUMERIC_COLS:
        return sorted(rows, key=lambda r: float(r.get(selected, 0) or 0), reverse=reverse)
    if selected in _WBS_SORT_STRING_COLS:
        return sorted(rows, key=lambda r: str(r.get(selected, "")).lower(), reverse=reverse)
    return sorted(rows, key=lambda r: float(r.get("remaining_amount", 0) or 0), reverse=reverse)


def _wbs_category_rollup(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Group WBS rows by category for hierarchical rollup."""
    cats: dict[str, dict[str, object]] = {}
    for r in rows:
        cat = str(r.get("category", "Uncategorised") or "Uncategorised")
        if cat not in cats:
            cats[cat] = {
                "category": cat,
                "item_count": 0,
                "boq_amount": 0.0,
                "work_done_amount": 0.0,
                "billed_amount": 0.0,
                "remaining_amount": 0.0,
            }
        c = cats[cat]
        c["item_count"] = int(c["item_count"]) + 1
        c["boq_amount"] = round(float(c["boq_amount"]) + float(r["boq_amount"]), 2)
        c["work_done_amount"] = round(float(c["work_done_amount"]) + float(r["work_done_amount"]), 2)
        c["billed_amount"] = round(float(c["billed_amount"]) + float(r["billed_amount"]), 2)
        c["remaining_amount"] = round(float(c["remaining_amount"]) + float(r["remaining_amount"]), 2)

    result: list[dict[str, object]] = []
    for c in cats.values():
        boq_amt = float(c["boq_amount"])
        wd_amt = float(c["work_done_amount"])
        c["completion_pct"] = round((wd_amt / boq_amt) * 100.0, 2) if boq_amt > 0 else 0.0
        result.append(c)
    return sorted(result, key=lambda c: float(c["remaining_amount"]), reverse=True)


def get_wbs_report(
    db: Session,
    *,
    current_user: User,
    pagination: PaginationParams,
    company_id: int | None = None,
    contract_id: int | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: SortDirection = SortDirection.ASC,
) -> dict[str, object]:
    all_rows = _wbs_report_rows(
        db,
        current_user=current_user,
        company_id=company_id,
        contract_id=contract_id,
        search=search,
    )

    sorted_rows = _sort_wbs_rows(all_rows, sort_by=sort_by, sort_dir=sort_dir)
    category_rollup = _wbs_category_rollup(all_rows)

    total_boq = sum(float(r["boq_amount"]) for r in all_rows)
    total_wd = sum(float(r["work_done_amount"]) for r in all_rows)
    total_billed = sum(float(r["billed_amount"]) for r in all_rows)
    total_remaining = sum(float(r["remaining_amount"]) for r in all_rows)

    contract_ids = {r["contract_id"] for r in all_rows}
    project_ids = {r["project_id"] for r in all_rows}

    total = len(sorted_rows)
    start = (pagination.page - 1) * pagination.limit
    end = start + pagination.limit
    page_rows = sorted_rows[start:end]

    return {
        "summary": {
            "total_boq_amount": round(total_boq, 2),
            "total_work_done_amount": round(total_wd, 2),
            "total_billed_amount": round(total_billed, 2),
            "total_remaining_amount": round(total_remaining, 2),
            "overall_completion_pct": round((total_wd / total_boq) * 100.0, 2) if total_boq > 0 else 0.0,
            "total_items": total,
            "categories_count": len(category_rollup),
            "contracts_covered": len(contract_ids),
            "projects_covered": len(project_ids),
        },
        "category_rollup": category_rollup,
        "items": page_rows,
        "total": total,
        "page": pagination.page,
        "limit": pagination.limit,
    }


def list_wbs_report_for_export(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
    contract_id: int | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: SortDirection = SortDirection.ASC,
) -> list[dict[str, object]]:
    all_rows = _wbs_report_rows(
        db,
        current_user=current_user,
        company_id=company_id,
        contract_id=contract_id,
        search=search,
    )
    return _sort_wbs_rows(all_rows, sort_by=sort_by, sort_dir=sort_dir)


# ===========================================================================
# Export helpers for ageing, cash-flow, MIS
# ===========================================================================


def get_ageing_analysis_for_export(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
    top_limit: int = 500,
) -> dict[str, object]:
    return get_ageing_analysis(
        db,
        current_user=current_user,
        company_id=company_id,
        top_limit=top_limit,
    )


def get_cash_flow_forecast_for_export(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
    search: str | None = None,
    top_limit: int = 500,
    horizon_weeks: int = 8,
    collection_days: int = 30,
) -> dict[str, object]:
    return get_cash_flow_forecast(
        db,
        current_user=current_user,
        company_id=company_id,
        search=search,
        top_limit=top_limit,
        horizon_weeks=horizon_weeks,
        collection_days=collection_days,
    )


def get_mis_summary_for_export(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    months: int = 6,
    top_limit: int = 50,
) -> dict[str, object]:
    return get_mis_summary(
        db,
        current_user=current_user,
        company_id=company_id,
        status_filter=status_filter,
        search=search,
        months=months,
        top_limit=top_limit,
    )
