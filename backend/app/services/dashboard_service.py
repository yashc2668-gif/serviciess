"""Finance-focused dashboard helpers."""

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.models.contract import Contract
from app.models.deduction import Deduction
from app.models.labour_bill import LabourBill
from app.models.material_issue import MaterialIssue
from app.models.payment import Payment
from app.models.project import Project
from app.models.ra_bill import RABill
from app.models.secured_advance import SecuredAdvance
from app.schemas.dashboard import (
    ContractRecentPaymentOut,
    ContractRecentRABillOut,
    ContractDashboardOut,
    ContractOutstandingOut,
    DashboardFinanceOut,
    DashboardSummaryOut,
    DeductionSummaryOut,
    MonthlyTrendPointOut,
    ProjectDashboardOut,
    ProjectFinanceSummaryOut,
    RetentionOutstandingSummaryOut,
    StatusCountOut,
)

BILLED_RA_BILL_STATUSES = {
    "submitted",
    "verified",
    "finance_hold",
    "approved",
    "partially_paid",
    "paid",
}
PAYABLE_RA_BILL_STATUSES = {"approved", "partially_paid", "paid"}
PENDING_RA_BILL_STATUSES = {
    "draft",
    "submitted",
    "verified",
    "finance_hold",
}
PENDING_PAYMENT_STATUSES = {"draft", "approved"}
ACTUAL_COST_LABOUR_STATUSES = {"approved", "paid"}


def _to_decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def _to_float(value) -> float:
    return float(_to_decimal(value))


def _month_key(value: date | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m")


def _status_counts(counter: Counter[str]) -> list[StatusCountOut]:
    return [
        StatusCountOut(status=status_name, count=count)
        for status_name, count in sorted(counter.items())
    ]


def _trend_points(amounts: dict[str, Decimal]) -> list[MonthlyTrendPointOut]:
    return [
        MonthlyTrendPointOut(month=month, amount=_to_float(amount))
        for month, amount in sorted(amounts.items())
    ]


def _deduction_summaries(amounts: dict[str, Decimal]) -> list[DeductionSummaryOut]:
    return [
        DeductionSummaryOut(deduction_type=deduction_type, amount=_to_float(amount))
        for deduction_type, amount in sorted(amounts.items())
    ]


def _project_query(db: Session):
    return db.query(Project).options(
        selectinload(Project.contracts)
        .selectinload(Contract.ra_bills)
        .selectinload(RABill.payment_allocations),
        selectinload(Project.contracts)
        .selectinload(Contract.ra_bills)
        .selectinload(RABill.deductions),
        selectinload(Project.contracts).selectinload(Contract.payments),
        selectinload(Project.contracts).selectinload(Contract.secured_advances),
    )


def _get_project_or_404(db: Session, project_id: int) -> Project:
    project = _project_query(db).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def _get_contract_or_404(db: Session, contract_id: int) -> Contract:
    contract = (
        db.query(Contract)
        .options(
            selectinload(Contract.project).selectinload(Project.company),
            selectinload(Contract.vendor),
            selectinload(Contract.ra_bills).selectinload(RABill.payment_allocations),
            selectinload(Contract.ra_bills).selectinload(RABill.deductions),
            selectinload(Contract.payments),
            selectinload(Contract.secured_advances),
        )
        .filter(Contract.id == contract_id)
        .first()
    )
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found",
        )
    return contract


def _ra_bill_paid_amount(bill: RABill) -> Decimal:
    return sum(
        (_to_decimal(allocation.amount) for allocation in bill.payment_allocations or []),
        Decimal("0"),
    )


def _contract_metrics(contract: Contract) -> dict:
    billed_amount = Decimal("0")
    paid_amount = Decimal("0")
    outstanding_amount = Decimal("0")
    ra_bill_statuses: Counter[str] = Counter()
    payment_statuses: Counter[str] = Counter()
    billing_trend: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    payment_trend: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    deductions_summary: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    retention_total = Decimal("0")
    retention_bill_ids: set[int] = set()

    for bill in contract.ra_bills or []:
        if bill.status in PENDING_RA_BILL_STATUSES:
            ra_bill_statuses[bill.status] += 1
        if bill.status in BILLED_RA_BILL_STATUSES:
            billed_amount += _to_decimal(bill.net_payable)
            paid_for_bill = _ra_bill_paid_amount(bill)
            paid_amount += paid_for_bill
            if bill.status in PAYABLE_RA_BILL_STATUSES:
                outstanding_amount += max(_to_decimal(bill.net_payable) - paid_for_bill, Decimal("0"))
            month = _month_key(bill.bill_date)
            if month is not None:
                billing_trend[month] += _to_decimal(bill.net_payable)

            for deduction in bill.deductions or []:
                deductions_summary[deduction.deduction_type] += _to_decimal(deduction.amount)
                if deduction.deduction_type == "retention":
                    retention_total += _to_decimal(deduction.amount)
                    retention_bill_ids.add(bill.id)

    for payment in contract.payments or []:
        if payment.status in PENDING_PAYMENT_STATUSES:
            payment_statuses[payment.status] += 1
        if payment.status == "released":
            month = _month_key(payment.payment_date)
            if month is not None:
                payment_trend[month] += _to_decimal(payment.amount)

    secured_advance_outstanding = sum(
        (_to_decimal(advance.balance) for advance in contract.secured_advances or []),
        Decimal("0"),
    )

    return {
        "billed_amount": billed_amount,
        "paid_amount": paid_amount,
        "outstanding_amount": outstanding_amount,
        "secured_advance_outstanding": secured_advance_outstanding,
        "ra_bill_statuses": ra_bill_statuses,
        "payment_statuses": payment_statuses,
        "billing_trend": billing_trend,
        "payment_trend": payment_trend,
        "deductions_summary": deductions_summary,
        "retention_total": retention_total,
        "retention_bill_count": len(retention_bill_ids),
    }


def _aggregate_projects(projects: list[Project]) -> dict:
    total_projects = len(projects)
    active_contracts = 0
    total_billed_amount = Decimal("0")
    total_paid_amount = Decimal("0")
    outstanding_payable = Decimal("0")
    secured_advance_outstanding = Decimal("0")
    ra_bill_statuses: Counter[str] = Counter()
    payment_statuses: Counter[str] = Counter()
    project_summaries: list[ProjectFinanceSummaryOut] = []
    contract_outstandings: list[ContractOutstandingOut] = []
    billing_trend: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    payment_trend: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    deductions_summary: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    retention_total = Decimal("0")
    retention_contract_ids: set[int] = set()
    retention_bill_count = 0

    for project in projects:
        project_billed = Decimal("0")
        project_paid = Decimal("0")
        project_outstanding = Decimal("0")
        project_active_contracts = 0

        for contract in project.contracts or []:
            if contract.status == "active":
                active_contracts += 1
                project_active_contracts += 1

            metrics = _contract_metrics(contract)
            project_billed += metrics["billed_amount"]
            project_paid += metrics["paid_amount"]
            project_outstanding += metrics["outstanding_amount"]

            total_billed_amount += metrics["billed_amount"]
            total_paid_amount += metrics["paid_amount"]
            outstanding_payable += metrics["outstanding_amount"]
            secured_advance_outstanding += metrics["secured_advance_outstanding"]
            ra_bill_statuses.update(metrics["ra_bill_statuses"])
            payment_statuses.update(metrics["payment_statuses"])
            retention_total += metrics["retention_total"]
            if metrics["retention_total"] > 0:
                retention_contract_ids.add(contract.id)
            retention_bill_count += metrics["retention_bill_count"]

            for month, amount in metrics["billing_trend"].items():
                billing_trend[month] += amount
            for month, amount in metrics["payment_trend"].items():
                payment_trend[month] += amount
            for deduction_type, amount in metrics["deductions_summary"].items():
                deductions_summary[deduction_type] += amount

            contract_outstandings.append(
                ContractOutstandingOut(
                    contract_id=contract.id,
                    project_id=project.id,
                    project_name=project.name,
                    contract_no=contract.contract_no,
                    contract_title=contract.title,
                    status=contract.status,
                    billed_amount=_to_float(metrics["billed_amount"]),
                    paid_amount=_to_float(metrics["paid_amount"]),
                    outstanding_amount=_to_float(metrics["outstanding_amount"]),
                    secured_advance_outstanding=_to_float(
                        metrics["secured_advance_outstanding"]
                    ),
                )
            )

        project_summaries.append(
            ProjectFinanceSummaryOut(
                project_id=project.id,
                project_name=project.name,
                project_code=project.code,
                billed_amount=_to_float(project_billed),
                paid_amount=_to_float(project_paid),
                outstanding_amount=_to_float(project_outstanding),
                contract_count=len(project.contracts or []),
                active_contract_count=project_active_contracts,
            )
        )

    contract_outstandings.sort(
        key=lambda item: (-item.outstanding_amount, item.project_name, item.contract_no)
    )
    project_summaries.sort(key=lambda item: (-item.outstanding_amount, item.project_name))

    return {
        "summary": DashboardSummaryOut(
            total_projects=total_projects,
            active_contracts=active_contracts,
            total_billed_amount=_to_float(total_billed_amount),
            total_paid_amount=_to_float(total_paid_amount),
            outstanding_payable=_to_float(outstanding_payable),
            secured_advance_outstanding=_to_float(secured_advance_outstanding),
            pending_ra_bills_by_status=_status_counts(ra_bill_statuses),
            pending_payments_by_status=_status_counts(payment_statuses),
        ),
        "finance": DashboardFinanceOut(
            total_billed_amount=_to_float(total_billed_amount),
            total_paid_amount=_to_float(total_paid_amount),
            outstanding_payable=_to_float(outstanding_payable),
            secured_advance_outstanding=_to_float(secured_advance_outstanding),
            project_wise_finance_summary=project_summaries,
            contract_wise_finance_summary=contract_outstandings,
            project_wise_billed_vs_paid=project_summaries,
            contract_wise_outstanding=contract_outstandings,
            monthly_billing_trend=_trend_points(billing_trend),
            monthly_payment_trend=_trend_points(payment_trend),
            deductions_summary=_deduction_summaries(deductions_summary),
            retention_outstanding_summary=RetentionOutstandingSummaryOut(
                total_retention_deducted=_to_float(retention_total),
                outstanding_retention_amount=_to_float(retention_total),
                affected_bill_count=retention_bill_count,
                affected_contract_count=len(retention_contract_ids),
            ),
        ),
    }


def get_dashboard_summary(db: Session) -> DashboardSummaryOut:
    data = _aggregate_projects(_project_query(db).order_by(Project.id.asc()).all())
    return data["summary"]


def get_dashboard_finance(db: Session) -> DashboardFinanceOut:
    data = _aggregate_projects(_project_query(db).order_by(Project.id.asc()).all())
    return data["finance"]


def get_project_dashboard(db: Session, project_id: int) -> ProjectDashboardOut:
    project = _get_project_or_404(db, project_id)
    project_data = _aggregate_projects([project])
    summary = project_data["summary"]
    finance = project_data["finance"]
    return ProjectDashboardOut(
        project_id=project.id,
        project_name=project.name,
        project_code=project.code,
        status=project.status,
        original_value=_to_float(project.original_value),
        revised_value=_to_float(project.revised_value),
        contract_count=len(project.contracts or []),
        active_contract_count=summary.active_contracts,
        total_billed_amount=summary.total_billed_amount,
        total_paid_amount=summary.total_paid_amount,
        outstanding_payable=summary.outstanding_payable,
        secured_advance_outstanding=summary.secured_advance_outstanding,
        pending_ra_bills_by_status=summary.pending_ra_bills_by_status,
        pending_payments_by_status=summary.pending_payments_by_status,
        contract_wise_finance_summary=finance.contract_wise_finance_summary,
        monthly_billing_trend=finance.monthly_billing_trend,
        monthly_payment_trend=finance.monthly_payment_trend,
        deductions_summary=finance.deductions_summary,
        contract_wise_outstanding=finance.contract_wise_outstanding,
    )


def get_contract_dashboard(db: Session, contract_id: int) -> ContractDashboardOut:
    contract = _get_contract_or_404(db, contract_id)
    metrics = _contract_metrics(contract)
    material_cost_amount = _to_float(
        db.query(func.coalesce(func.sum(MaterialIssue.total_amount), 0))
        .filter(
            MaterialIssue.contract_id == contract.id,
            MaterialIssue.status == "issued",
        )
        .scalar()
    )
    labour_cost_amount = _to_float(
        db.query(func.coalesce(func.sum(LabourBill.net_payable), 0))
        .filter(
            LabourBill.contract_id == contract.id,
            LabourBill.status.in_(ACTUAL_COST_LABOUR_STATUSES),
        )
        .scalar()
    )
    actual_cost_amount = (
        _to_float(metrics["paid_amount"]) + material_cost_amount + labour_cost_amount
    )
    contract_value = _to_float(contract.revised_value)
    commercial_headroom_amount = contract_value - actual_cost_amount
    billed_margin_amount = _to_float(metrics["billed_amount"]) - actual_cost_amount
    headroom_pct = (
        (commercial_headroom_amount * 100.0) / contract_value
        if contract_value > 0
        else 0.0
    )

    recent_ra_bills = [
        ContractRecentRABillOut(
            bill_id=bill.id,
            bill_no=bill.bill_no,
            bill_date=bill.bill_date,
            status=bill.status,
            net_payable=_to_float(bill.net_payable),
            paid_amount=_to_float(_ra_bill_paid_amount(bill)),
            outstanding_amount=_to_float(
                max(_to_decimal(bill.net_payable) - _ra_bill_paid_amount(bill), Decimal("0"))
            ),
            retention_amount=_to_float(
                sum(
                    (
                        _to_decimal(deduction.amount)
                        for deduction in bill.deductions or []
                        if deduction.deduction_type == "retention"
                    ),
                    Decimal("0"),
                )
            ),
        )
        for bill in sorted(
            contract.ra_bills or [],
            key=lambda item: (item.bill_date, item.bill_no, item.id),
            reverse=True,
        )[:6]
    ]
    recent_payments = [
        ContractRecentPaymentOut(
            payment_id=payment.id,
            payment_date=payment.payment_date,
            status=payment.status,
            amount=_to_float(payment.amount),
            allocated_amount=_to_float(payment.allocated_amount),
            available_amount=_to_float(payment.available_amount),
            ra_bill_id=payment.ra_bill_id,
            reference_no=payment.reference_no,
        )
        for payment in sorted(
            contract.payments or [],
            key=lambda item: (item.payment_date, item.id),
            reverse=True,
        )[:6]
    ]

    return ContractDashboardOut(
        contract_id=contract.id,
        project_id=contract.project_id,
        company_name=contract.project.company.name if contract.project and contract.project.company else "",
        project_name=contract.project.name if contract.project else "",
        project_code=contract.project.code if contract.project else None,
        vendor_id=contract.vendor_id,
        vendor_name=contract.vendor.name if contract.vendor else (contract.client_name or "Client contract"),
        contract_no=contract.contract_no,
        contract_title=contract.title,
        status=contract.status,
        start_date=contract.start_date,
        end_date=contract.end_date,
        original_value=_to_float(contract.original_value),
        revised_value=contract_value,
        retention_percentage=_to_float(contract.retention_percentage),
        total_billed_amount=_to_float(metrics["billed_amount"]),
        total_paid_amount=_to_float(metrics["paid_amount"]),
        outstanding_payable=_to_float(metrics["outstanding_amount"]),
        secured_advance_outstanding=_to_float(metrics["secured_advance_outstanding"]),
        material_cost_amount=material_cost_amount,
        labour_cost_amount=labour_cost_amount,
        actual_cost_amount=actual_cost_amount,
        commercial_headroom_amount=commercial_headroom_amount,
        billed_margin_amount=billed_margin_amount,
        headroom_pct=headroom_pct,
        pending_ra_bills_by_status=_status_counts(metrics["ra_bill_statuses"]),
        pending_payments_by_status=_status_counts(metrics["payment_statuses"]),
        monthly_billing_trend=_trend_points(metrics["billing_trend"]),
        monthly_payment_trend=_trend_points(metrics["payment_trend"]),
        deductions_summary=_deduction_summaries(metrics["deductions_summary"]),
        retention_outstanding_amount=_to_float(metrics["retention_total"]),
        recent_ra_bills=recent_ra_bills,
        recent_payments=recent_payments,
    )
