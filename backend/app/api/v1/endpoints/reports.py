"""Reporting endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.reporting import (
    AgeingAnalysisOut,
    CashFlowForecastOut,
    ContractCommercialReportRowOut,
    LabourProductivityReportOut,
    MISSummaryReportOut,
    MaterialConsumptionReportOut,
    ProjectCostReportRowOut,
    RetentionTrackingRowOut,
    WBSReportOut,
)
from app.services.reporting_service import (
    get_ageing_analysis_for_export,
    get_cash_flow_forecast,
    get_ageing_analysis,
    get_cash_flow_forecast_for_export,
    get_labour_productivity_report,
    get_mis_summary,
    get_mis_summary_for_export,
    get_material_consumption_report,
    get_wbs_report,
    list_contract_commercial_report,
    list_contract_commercial_report_for_export,
    list_labour_productivity_report_for_export,
    list_material_consumption_report_for_export,
    list_project_cost_report,
    list_project_cost_report_for_export,
    list_retention_tracking_report,
    list_retention_tracking_report_for_export,
    list_wbs_report_for_export,
)
from app.utils.csv_export import build_csv_response
from app.utils.pagination import PaginationParams, get_pagination_params
from app.utils.sorting import SortParams, get_sort_params

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/project-costs", response_model=PaginatedResponse[ProjectCostReportRowOut])
def get_project_cost_report(
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    sorting: SortParams = Depends(get_sort_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("dashboard:read")),
):
    return list_project_cost_report(
        db,
        current_user=current_user,
        pagination=pagination,
        company_id=company_id,
        status_filter=status_filter,
        search=search,
        sort_by=sorting.sort_by,
        sort_dir=sorting.sort_dir,
    )


@router.get("/project-costs/export")
def export_project_cost_report(
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    sorting: SortParams = Depends(get_sort_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("dashboard:read")),
):
    rows = list_project_cost_report_for_export(
        db,
        current_user=current_user,
        company_id=company_id,
        status_filter=status_filter,
        search=search,
        sort_by=sorting.sort_by,
        sort_dir=sorting.sort_dir,
    )
    return build_csv_response(
        filename="project-cost-report",
        headers=[
            "Company",
            "Project",
            "Code",
            "Status",
            "Original Budget",
            "Revised Budget",
            "Contracts",
            "Active Contracts",
            "Committed Cost",
            "Vendor Billed",
            "Vendor Paid",
            "Material Issued",
            "Labour Billed",
            "Actual Cost",
            "Secured Advance Outstanding",
            "Actual Variance",
            "Committed Variance",
            "Actual Utilization %",
            "Committed Utilization %",
        ],
        rows=[
            [
                row.company_name,
                row.project_name,
                row.project_code,
                row.status,
                row.original_budget_amount,
                row.budget_amount,
                row.contract_count,
                row.active_contract_count,
                row.committed_amount,
                row.billed_cost_amount,
                row.paid_cost_amount,
                row.material_issued_amount,
                row.labour_billed_amount,
                row.actual_cost_amount,
                row.secured_advance_outstanding,
                row.actual_variance_amount,
                row.committed_variance_amount,
                row.actual_utilization_pct,
                row.committed_utilization_pct,
            ]
            for row in rows
        ],
    )


@router.get(
    "/contract-commercials",
    response_model=PaginatedResponse[ContractCommercialReportRowOut],
)
def get_contract_commercial_report(
    company_id: int | None = None,
    search: str | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    sorting: SortParams = Depends(get_sort_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("dashboard:read")),
):
    return list_contract_commercial_report(
        db,
        current_user=current_user,
        pagination=pagination,
        company_id=company_id,
        search=search,
        sort_by=sorting.sort_by,
        sort_dir=sorting.sort_dir,
    )


@router.get("/contract-commercials/export")
def export_contract_commercial_report(
    company_id: int | None = None,
    search: str | None = None,
    sorting: SortParams = Depends(get_sort_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("dashboard:read")),
):
    rows = list_contract_commercial_report_for_export(
        db,
        current_user=current_user,
        company_id=company_id,
        search=search,
        sort_by=sorting.sort_by,
        sort_dir=sorting.sort_dir,
    )
    return build_csv_response(
        filename="contract-commercial-report",
        headers=[
            "Company",
            "Project",
            "Vendor",
            "Contract No",
            "Title",
            "Status",
            "Contract Value",
            "Billed Amount",
            "Paid Amount",
            "Material Cost",
            "Labour Cost",
            "Actual Cost",
            "Outstanding Payable",
            "Retention Held",
            "Secured Advance Outstanding",
            "Commercial Headroom",
            "Billed Margin",
            "Headroom %",
        ],
        rows=[
            [
                row.company_name,
                row.project_name,
                row.vendor_name,
                row.contract_no,
                row.contract_title,
                row.status,
                row.contract_value,
                row.billed_amount,
                row.paid_amount,
                row.material_cost_amount,
                row.labour_cost_amount,
                row.actual_cost_amount,
                row.outstanding_payable,
                row.retention_held_amount,
                row.secured_advance_outstanding,
                row.commercial_headroom_amount,
                row.billed_margin_amount,
                row.headroom_pct,
            ]
            for row in rows
        ],
    )


@router.get("/mis-summary", response_model=MISSummaryReportOut)
def get_mis_summary_report(
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    months: int = 6,
    top_limit: int = 6,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("dashboard:read")),
):
    return get_mis_summary(
        db,
        current_user=current_user,
        company_id=company_id,
        status_filter=status_filter,
        search=search,
        months=months,
        top_limit=top_limit,
    )


@router.get("/cash-flow-forecast", response_model=CashFlowForecastOut)
def get_cash_flow_forecast_report(
    company_id: int | None = None,
    search: str | None = None,
    top_limit: int = 6,
    horizon_weeks: int = 8,
    collection_days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("dashboard:read")),
):
    return get_cash_flow_forecast(
        db,
        current_user=current_user,
        company_id=company_id,
        search=search,
        top_limit=top_limit,
        horizon_weeks=horizon_weeks,
        collection_days=collection_days,
    )


@router.get("/material-consumption", response_model=MaterialConsumptionReportOut)
def get_material_consumption_report_view(
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    sorting: SortParams = Depends(get_sort_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("dashboard:read")),
):
    return get_material_consumption_report(
        db,
        current_user=current_user,
        pagination=pagination,
        company_id=company_id,
        status_filter=status_filter,
        search=search,
        sort_by=sorting.sort_by,
        sort_dir=sorting.sort_dir,
    )


@router.get("/material-consumption/export")
def export_material_consumption_report(
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    sorting: SortParams = Depends(get_sort_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("dashboard:read")),
):
    rows = list_material_consumption_report_for_export(
        db,
        current_user=current_user,
        company_id=company_id,
        status_filter=status_filter,
        search=search,
        sort_by=sorting.sort_by,
        sort_dir=sorting.sort_dir,
    )
    return build_csv_response(
        filename="material-consumption-report",
        headers=[
            "Company",
            "Project",
            "Project Code",
            "Material Code",
            "Material Name",
            "Category",
            "Unit",
            "Requested Qty",
            "Required Qty",
            "Requisition Issued Qty",
            "Actual Issued Qty",
            "Wastage Qty",
            "Balance To Issue Qty",
            "Excess Issue Qty",
            "Issue Coverage %",
            "Wastage %",
            "Required Amount",
            "Issued Amount",
            "Wastage Amount",
        ],
        rows=[
            [
                row["company_name"],
                row["project_name"],
                row["project_code"],
                row["material_code"],
                row["material_name"],
                row["category"],
                row["unit"],
                row["requested_qty"],
                row["required_qty"],
                row["requisition_issued_qty"],
                row["issued_qty"],
                row["wastage_qty"],
                row["balance_to_issue_qty"],
                row["excess_issue_qty"],
                row["issue_coverage_pct"],
                row["wastage_pct"],
                row["required_amount"],
                row["issued_amount"],
                row["wastage_amount"],
            ]
            for row in rows
        ],
    )


@router.get("/labour-productivity", response_model=LabourProductivityReportOut)
def get_labour_productivity_report_view(
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    window_days: int = 56,
    benchmark_days: int = 84,
    pagination: PaginationParams = Depends(get_pagination_params),
    sorting: SortParams = Depends(get_sort_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("dashboard:read")),
):
    return get_labour_productivity_report(
        db,
        current_user=current_user,
        pagination=pagination,
        company_id=company_id,
        status_filter=status_filter,
        search=search,
        window_days=window_days,
        benchmark_days=benchmark_days,
        sort_by=sorting.sort_by,
        sort_dir=sorting.sort_dir,
    )


@router.get("/labour-productivity/export")
def export_labour_productivity_report(
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    window_days: int = 56,
    benchmark_days: int = 84,
    sorting: SortParams = Depends(get_sort_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("dashboard:read")),
):
    rows = list_labour_productivity_report_for_export(
        db,
        current_user=current_user,
        company_id=company_id,
        status_filter=status_filter,
        search=search,
        window_days=window_days,
        benchmark_days=benchmark_days,
        sort_by=sorting.sort_by,
        sort_dir=sorting.sort_dir,
    )
    return build_csv_response(
        filename="labour-productivity-report",
        headers=[
            "Trade",
            "Unit",
            "Trade Label",
            "Records",
            "Projects",
            "Contracts",
            "Recent Output Qty",
            "Prior Output Qty",
            "Output Change %",
            "Recent Crew Days",
            "Benchmark Crew Days",
            "Recent Productivity",
            "Benchmark Productivity",
            "Productivity Gap",
            "Productivity Gap %",
            "Productivity Index",
            "Benchmark Status",
            "Output Trend Status",
            "Last Entry Date",
        ],
        rows=[
            [
                row["trade"],
                row["unit"],
                row["trade_label"],
                row["record_count"],
                row["project_count"],
                row["contract_count"],
                row["recent_output_qty"],
                row["prior_output_qty"],
                row["output_change_pct"],
                row["recent_labour_count"],
                row["benchmark_labour_count"],
                row["recent_productivity"],
                row["benchmark_productivity"],
                row["productivity_gap"],
                row["productivity_gap_pct"],
                row["productivity_index"],
                row["benchmark_status"],
                row["output_trend_status"],
                row["last_entry_date"],
            ]
            for row in rows
        ],
    )


@router.get("/ageing-analysis", response_model=AgeingAnalysisOut)
def get_ageing_report(
    company_id: int | None = None,
    top_limit: int = 8,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("dashboard:read")),
):
    return get_ageing_analysis(
        db,
        current_user=current_user,
        company_id=company_id,
        top_limit=top_limit,
    )


@router.get(
    "/retention-tracking",
    response_model=PaginatedResponse[RetentionTrackingRowOut],
)
def get_retention_tracking_report(
    company_id: int | None = None,
    search: str | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    sorting: SortParams = Depends(get_sort_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("dashboard:read")),
):
    return list_retention_tracking_report(
        db,
        current_user=current_user,
        pagination=pagination,
        company_id=company_id,
        search=search,
        sort_by=sorting.sort_by,
        sort_dir=sorting.sort_dir,
    )


@router.get("/retention-tracking/export")
def export_retention_tracking_report(
    company_id: int | None = None,
    search: str | None = None,
    sorting: SortParams = Depends(get_sort_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("dashboard:read")),
):
    rows = list_retention_tracking_report_for_export(
        db,
        current_user=current_user,
        company_id=company_id,
        search=search,
        sort_by=sorting.sort_by,
        sort_dir=sorting.sort_dir,
    )
    return build_csv_response(
        filename="retention-tracking-report",
        headers=[
            "Company",
            "Project",
            "Vendor",
            "Contract No",
            "Title",
            "Status",
            "Scheduled Release Date",
            "Retention %",
            "Contract Value",
            "Billed Amount",
            "Estimated Retention Cap",
            "Retention Held",
            "Outstanding Retention",
            "Progress %",
            "Release Status",
        ],
        rows=[
            [
                row.company_name,
                row.project_name,
                row.vendor_name,
                row.contract_no,
                row.contract_title,
                row.status,
                row.scheduled_release_date,
                row.retention_percentage,
                row.contract_value,
                row.billed_amount,
                row.estimated_retention_cap,
                row.total_retention_deducted,
                row.outstanding_retention_amount,
                row.progress_pct,
                row.release_status,
            ]
            for row in rows
        ],
    )


# ---------------------------------------------------------------------------
# WBS (Work Breakdown Structure) report
# ---------------------------------------------------------------------------


@router.get("/wbs", response_model=WBSReportOut)
def get_wbs_report_view(
    company_id: int | None = None,
    contract_id: int | None = None,
    search: str | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    sorting: SortParams = Depends(get_sort_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("dashboard:read")),
):
    return get_wbs_report(
        db,
        current_user=current_user,
        pagination=pagination,
        company_id=company_id,
        contract_id=contract_id,
        search=search,
        sort_by=sorting.sort_by,
        sort_dir=sorting.sort_dir,
    )


@router.get("/wbs/export")
def export_wbs_report(
    company_id: int | None = None,
    contract_id: int | None = None,
    search: str | None = None,
    sorting: SortParams = Depends(get_sort_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("dashboard:read")),
):
    rows = list_wbs_report_for_export(
        db,
        current_user=current_user,
        company_id=company_id,
        contract_id=contract_id,
        search=search,
        sort_by=sorting.sort_by,
        sort_dir=sorting.sort_dir,
    )
    return build_csv_response(
        filename="wbs-work-breakdown-report",
        headers=[
            "Company",
            "Project",
            "Project Code",
            "Contract No",
            "Contract Title",
            "Vendor",
            "Item Code",
            "Description",
            "Unit",
            "Category",
            "BOQ Qty",
            "BOQ Rate",
            "BOQ Amount",
            "Work Done Qty",
            "Work Done Amount",
            "Billed Qty",
            "Billed Amount",
            "Remaining Qty",
            "Remaining Amount",
            "Completion %",
        ],
        rows=[
            [
                row["company_name"],
                row["project_name"],
                row["project_code"],
                row["contract_no"],
                row["contract_title"],
                row["vendor_name"],
                row["item_code"],
                row["description"],
                row["unit"],
                row["category"],
                row["boq_quantity"],
                row["boq_rate"],
                row["boq_amount"],
                row["work_done_quantity"],
                row["work_done_amount"],
                row["billed_quantity"],
                row["billed_amount"],
                row["remaining_quantity"],
                row["remaining_amount"],
                row["completion_pct"],
            ]
            for row in rows
        ],
    )


# ---------------------------------------------------------------------------
# Export endpoints for ageing, cash-flow, MIS
# ---------------------------------------------------------------------------


@router.get("/ageing-analysis/export")
def export_ageing_report(
    company_id: int | None = None,
    top_limit: int = 500,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("dashboard:read")),
):
    data = get_ageing_analysis_for_export(
        db,
        current_user=current_user,
        company_id=company_id,
        top_limit=top_limit,
    )

    ra_rows = [
        [
            b.bill_no,
            b.project_name,
            b.contract_no,
            b.contract_title,
            b.bill_date.isoformat() if hasattr(b.bill_date, "isoformat") else b.bill_date,
            b.status,
            b.outstanding_amount,
            b.age_days,
            b.bucket,
        ]
        for b in data.overdue_ra_bills
    ]
    pay_rows = [
        [
            p.payment_id,
            p.project_name,
            p.contract_no,
            p.payment_date.isoformat() if hasattr(p.payment_date, "isoformat") else p.payment_date,
            p.status,
            p.pending_amount,
            p.age_days,
            p.bucket,
        ]
        for p in data.overdue_payments
    ]

    all_rows: list[list[object]] = []
    all_rows.append(["--- Outstanding RA Bills ---", "", "", "", "", "", "", "", ""])
    all_rows.extend(ra_rows)
    all_rows.append(["", "", "", "", "", "", "", "", ""])
    all_rows.append(["--- Pending Payments ---", "", "", "", "", "", "", "", ""])
    all_rows.extend(pay_rows)

    return build_csv_response(
        filename="ageing-analysis-report",
        headers=[
            "Reference",
            "Project",
            "Contract No",
            "Title / Date",
            "Status",
            "Outstanding / Pending",
            "Age Days",
            "Bucket",
            "",
        ],
        rows=all_rows,
    )


@router.get("/cash-flow-forecast/export")
def export_cash_flow_forecast_report(
    company_id: int | None = None,
    search: str | None = None,
    top_limit: int = 500,
    horizon_weeks: int = 8,
    collection_days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("dashboard:read")),
):
    data = get_cash_flow_forecast_for_export(
        db,
        current_user=current_user,
        company_id=company_id,
        search=search,
        top_limit=top_limit,
        horizon_weeks=horizon_weeks,
        collection_days=collection_days,
    )

    bucket_rows = [
        [
            b.label,
            b.receivable_amount,
            b.payable_amount,
            b.net_amount,
            b.cumulative_net_amount,
        ]
        for b in data.buckets
    ]
    recv_rows = [
        [
            r.bill_no,
            r.project_name,
            r.contract_no,
            r.contract_title,
            r.bill_date.isoformat() if hasattr(r.bill_date, "isoformat") else r.bill_date,
            r.forecast_date.isoformat() if hasattr(r.forecast_date, "isoformat") else r.forecast_date,
            r.status,
            r.outstanding_amount,
            "Yes" if r.is_overdue else "No",
        ]
        for r in data.upcoming_receivables
    ]
    pay_rows = [
        [
            p.payment_id,
            p.project_name,
            p.contract_no,
            p.payment_date.isoformat() if hasattr(p.payment_date, "isoformat") else p.payment_date,
            p.forecast_date.isoformat() if hasattr(p.forecast_date, "isoformat") else p.forecast_date,
            p.status,
            p.pending_amount,
            "Yes" if p.is_overdue else "No",
            "",
        ]
        for p in data.upcoming_payments
    ]

    all_rows: list[list[object]] = []
    all_rows.append(["--- Weekly Forecast ---", "", "", "", "", "", "", "", ""])
    for br in bucket_rows:
        all_rows.append(br + ["", "", "", ""])
    all_rows.append(["", "", "", "", "", "", "", "", ""])
    all_rows.append(["--- Upcoming Receivables ---", "", "", "", "", "", "", "", ""])
    all_rows.extend(recv_rows)
    all_rows.append(["", "", "", "", "", "", "", "", ""])
    all_rows.append(["--- Upcoming Payments ---", "", "", "", "", "", "", "", ""])
    all_rows.extend(pay_rows)

    return build_csv_response(
        filename="cash-flow-forecast-report",
        headers=[
            "Reference",
            "Project",
            "Contract No",
            "Title / Date",
            "Forecast Date",
            "Status",
            "Amount",
            "Overdue",
            "",
        ],
        rows=all_rows,
    )


@router.get("/mis-summary/export")
def export_mis_summary_report(
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    months: int = 6,
    top_limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("dashboard:read")),
):
    data = get_mis_summary_for_export(
        db,
        current_user=current_user,
        company_id=company_id,
        status_filter=status_filter,
        search=search,
        months=months,
        top_limit=top_limit,
    )

    trend_rows = [
        [
            t.label,
            t.billed_amount,
            t.released_amount,
            t.retention_amount,
            t.net_amount,
        ]
        for t in data.monthly_trend
    ]
    project_rows = [
        [
            p.project_name,
            p.project_code or "",
            p.status,
            p.billed_amount,
            p.released_amount,
            p.outstanding_amount,
            p.active_contract_count,
        ]
        for p in data.top_outstanding_projects
    ]

    all_rows: list[list[object]] = []
    all_rows.append(["--- Summary ---", "", "", "", "", "", ""])
    all_rows.append([
        f"Projects: {data.summary.project_count}",
        f"Active: {data.summary.active_project_count}",
        f"Contracts: {data.summary.active_contract_count}",
        f"Outstanding: {data.summary.outstanding_payable}",
        f"Overdue Bills: {data.summary.overdue_vendor_bill_amount}",
        f"Retention Held: {data.summary.retention_held_amount}",
        "",
    ])
    all_rows.append(["", "", "", "", "", "", ""])
    all_rows.append(["--- Monthly Trend ---", "", "", "", "", "", ""])
    for tr in trend_rows:
        all_rows.append(tr + ["", ""])
    all_rows.append(["", "", "", "", "", "", ""])
    all_rows.append(["--- Top Outstanding Projects ---", "", "", "", "", "", ""])
    all_rows.extend(project_rows)

    return build_csv_response(
        filename="mis-summary-report",
        headers=[
            "Label / Project",
            "Code / Billed",
            "Status / Released",
            "Billed / Retention",
            "Released / Net",
            "Outstanding",
            "Active Contracts",
        ],
        rows=all_rows,
    )
