"""Reporting schemas for management and cost intelligence."""

from datetime import date

from pydantic import BaseModel


class ProjectCostReportRowOut(BaseModel):
    project_id: int
    company_id: int
    company_name: str
    project_name: str
    project_code: str | None = None
    status: str
    original_budget_amount: float
    budget_amount: float
    contract_count: int
    active_contract_count: int
    committed_amount: float
    billed_cost_amount: float
    paid_cost_amount: float
    material_issued_amount: float
    labour_billed_amount: float
    actual_cost_amount: float
    secured_advance_outstanding: float
    actual_variance_amount: float
    committed_variance_amount: float
    actual_utilization_pct: float
    committed_utilization_pct: float

    model_config = {"from_attributes": True}


class ContractCommercialReportRowOut(BaseModel):
    contract_id: int
    project_id: int
    company_name: str
    project_name: str
    vendor_name: str
    contract_no: str
    contract_title: str
    status: str
    end_date: date | None = None
    contract_value: float
    billed_amount: float
    paid_amount: float
    material_cost_amount: float
    labour_cost_amount: float
    actual_cost_amount: float
    outstanding_payable: float
    retention_held_amount: float
    secured_advance_outstanding: float
    commercial_headroom_amount: float
    billed_margin_amount: float
    headroom_pct: float

    model_config = {"from_attributes": True}


class AgeingBucketOut(BaseModel):
    bucket: str
    label: str
    count: int
    amount: float


class OutstandingRABillAgeingRowOut(BaseModel):
    bill_id: int
    contract_id: int
    project_name: str
    contract_no: str
    contract_title: str
    bill_no: int
    bill_date: date
    status: str
    outstanding_amount: float
    age_days: int
    bucket: str


class PendingPaymentAgeingRowOut(BaseModel):
    payment_id: int
    contract_id: int
    project_name: str
    contract_no: str
    payment_date: date
    status: str
    pending_amount: float
    age_days: int
    bucket: str


class AgeingAnalysisOut(BaseModel):
    ra_bill_buckets: list[AgeingBucketOut]
    payment_buckets: list[AgeingBucketOut]
    overdue_ra_bills: list[OutstandingRABillAgeingRowOut]
    overdue_payments: list[PendingPaymentAgeingRowOut]


class RetentionTrackingRowOut(BaseModel):
    contract_id: int
    project_id: int
    company_name: str
    project_name: str
    vendor_name: str
    contract_no: str
    contract_title: str
    status: str
    scheduled_release_date: date | None = None
    retention_percentage: float
    contract_value: float
    billed_amount: float
    estimated_retention_cap: float
    total_retention_deducted: float
    outstanding_retention_amount: float
    progress_pct: float
    release_status: str

    model_config = {"from_attributes": True}


class CashFlowForecastSummaryOut(BaseModel):
    total_receivable_pipeline: float
    overdue_receivables: float
    receivables_within_horizon: float
    total_payable_pipeline: float
    overdue_payables: float
    payables_within_horizon: float
    projected_net_flow: float
    projected_peak_deficit: float
    projected_peak_surplus: float


class CashFlowBucketOut(BaseModel):
    bucket_start: date
    bucket_end: date
    label: str
    receivable_amount: float
    payable_amount: float
    net_amount: float
    cumulative_net_amount: float


class CashFlowReceivableRowOut(BaseModel):
    bill_id: int
    contract_id: int
    project_name: str
    contract_no: str
    contract_title: str
    bill_no: int
    bill_date: date
    forecast_date: date
    status: str
    outstanding_amount: float
    is_overdue: bool


class CashFlowPaymentRowOut(BaseModel):
    payment_id: int
    contract_id: int
    project_name: str
    contract_no: str
    payment_date: date
    forecast_date: date
    status: str
    pending_amount: float
    is_overdue: bool


class CashFlowForecastOut(BaseModel):
    summary: CashFlowForecastSummaryOut
    buckets: list[CashFlowBucketOut]
    upcoming_receivables: list[CashFlowReceivableRowOut]
    upcoming_payments: list[CashFlowPaymentRowOut]


class MaterialConsumptionSummaryOut(BaseModel):
    total_required_qty: float
    total_issued_qty: float
    total_wastage_qty: float
    total_balance_to_issue_qty: float
    total_excess_issue_qty: float
    total_required_amount: float
    total_issued_amount: float
    total_wastage_amount: float
    overall_wastage_pct: float


class MaterialConsumptionProjectRollupOut(BaseModel):
    project_id: int
    company_name: str
    project_name: str
    project_code: str | None = None
    required_qty: float
    issued_qty: float
    wastage_qty: float
    required_amount: float
    issued_amount: float
    wastage_amount: float


class MaterialConsumptionReportRowOut(BaseModel):
    company_name: str
    project_id: int
    project_name: str
    project_code: str | None = None
    material_id: int
    material_code: str
    material_name: str
    category: str | None = None
    unit: str
    requested_qty: float
    required_qty: float
    requisition_issued_qty: float
    issued_qty: float
    wastage_qty: float
    balance_to_issue_qty: float
    excess_issue_qty: float
    issue_coverage_pct: float
    wastage_pct: float
    required_amount: float
    issued_amount: float
    wastage_amount: float


class MaterialConsumptionReportOut(BaseModel):
    summary: MaterialConsumptionSummaryOut
    top_wastage_projects: list[MaterialConsumptionProjectRollupOut]
    watchlist: list[MaterialConsumptionReportRowOut]
    items: list[MaterialConsumptionReportRowOut]
    total: int
    page: int
    limit: int


class MISTrendPointOut(BaseModel):
    month: str
    label: str
    billed_amount: float
    released_amount: float
    retention_amount: float
    net_amount: float


class MISStatusMixOut(BaseModel):
    status: str
    count: int


class MISOutstandingProjectOut(BaseModel):
    project_id: int
    project_name: str
    project_code: str | None = None
    status: str
    billed_amount: float
    released_amount: float
    outstanding_amount: float
    active_contract_count: int


class MISMonthlySummaryOut(BaseModel):
    current_month: str
    current_month_label: str
    previous_month: str
    previous_month_label: str
    project_count: int
    active_project_count: int
    active_contract_count: int
    current_month_billed_amount: float
    previous_month_billed_amount: float
    current_month_released_amount: float
    previous_month_released_amount: float
    current_month_net_amount: float
    previous_month_net_amount: float
    payment_release_coverage_pct: float
    outstanding_payable: float
    overdue_vendor_bill_amount: float
    overdue_pending_payment_amount: float
    retention_held_amount: float
    secured_advance_outstanding: float


class MISSummaryReportOut(BaseModel):
    summary: MISMonthlySummaryOut
    monthly_trend: list[MISTrendPointOut]
    status_mix: list[MISStatusMixOut]
    top_outstanding_projects: list[MISOutstandingProjectOut]


class LabourProductivitySummaryOut(BaseModel):
    current_period_start: date
    current_period_end: date
    benchmark_period_start: date
    benchmark_period_end: date
    records_logged: int
    crew_days_logged: int
    active_trade_groups: int
    projects_covered: int
    below_benchmark_groups: int
    benchmark_hit_rate_pct: float


class LabourTradeProductivityRowOut(BaseModel):
    trade: str
    unit: str
    trade_label: str
    record_count: int
    project_count: int
    contract_count: int
    recent_output_qty: float
    prior_output_qty: float
    output_change_pct: float
    recent_labour_count: int
    benchmark_labour_count: int
    recent_productivity: float
    benchmark_productivity: float
    productivity_gap: float
    productivity_gap_pct: float
    productivity_index: float
    benchmark_status: str
    output_trend_status: str
    last_entry_date: date | None = None


class LabourProductivityReportOut(BaseModel):
    summary: LabourProductivitySummaryOut
    benchmark_focus: list[LabourTradeProductivityRowOut]
    watchlist: list[LabourTradeProductivityRowOut]
    items: list[LabourTradeProductivityRowOut]
    total: int
    page: int
    limit: int


# ---------------------------------------------------------------------------
# WBS (Work Breakdown Structure) report
# ---------------------------------------------------------------------------


class WBSItemRowOut(BaseModel):
    boq_item_id: int
    contract_id: int
    project_id: int
    company_name: str
    project_name: str
    project_code: str | None = None
    contract_no: str
    contract_title: str
    vendor_name: str
    item_code: str | None = None
    description: str
    unit: str
    category: str | None = None
    boq_quantity: float
    boq_rate: float
    boq_amount: float
    work_done_quantity: float
    work_done_amount: float
    billed_quantity: float
    billed_amount: float
    remaining_quantity: float
    remaining_amount: float
    completion_pct: float

    model_config = {"from_attributes": True}


class WBSCategoryRollupOut(BaseModel):
    category: str
    item_count: int
    boq_amount: float
    work_done_amount: float
    billed_amount: float
    remaining_amount: float
    completion_pct: float


class WBSSummaryOut(BaseModel):
    total_boq_amount: float
    total_work_done_amount: float
    total_billed_amount: float
    total_remaining_amount: float
    overall_completion_pct: float
    total_items: int
    categories_count: int
    contracts_covered: int
    projects_covered: int


class WBSReportOut(BaseModel):
    summary: WBSSummaryOut
    category_rollup: list[WBSCategoryRollupOut]
    items: list[WBSItemRowOut]
    total: int
    page: int
    limit: int
