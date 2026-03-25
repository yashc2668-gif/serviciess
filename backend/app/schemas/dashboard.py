"""Dashboard schemas."""

from pydantic import BaseModel, Field


class StatusCountOut(BaseModel):
    status: str
    count: int


class MonthlyTrendPointOut(BaseModel):
    month: str
    amount: float


class DeductionSummaryOut(BaseModel):
    deduction_type: str
    amount: float


class ProjectFinanceSummaryOut(BaseModel):
    project_id: int
    project_name: str
    project_code: str | None = None
    billed_amount: float
    paid_amount: float
    outstanding_amount: float
    contract_count: int
    active_contract_count: int


class ContractOutstandingOut(BaseModel):
    contract_id: int
    project_id: int
    project_name: str
    contract_no: str
    contract_title: str
    status: str
    billed_amount: float
    paid_amount: float
    outstanding_amount: float
    secured_advance_outstanding: float


class RetentionOutstandingSummaryOut(BaseModel):
    total_retention_deducted: float
    outstanding_retention_amount: float
    affected_bill_count: int
    affected_contract_count: int


class DashboardSummaryOut(BaseModel):
    total_projects: int
    active_contracts: int
    total_billed_amount: float
    total_paid_amount: float
    outstanding_payable: float
    secured_advance_outstanding: float
    pending_ra_bills_by_status: list[StatusCountOut] = Field(default_factory=list)
    pending_payments_by_status: list[StatusCountOut] = Field(default_factory=list)


class DashboardFinanceOut(BaseModel):
    total_billed_amount: float
    total_paid_amount: float
    outstanding_payable: float
    secured_advance_outstanding: float
    project_wise_finance_summary: list[ProjectFinanceSummaryOut] = Field(default_factory=list)
    contract_wise_finance_summary: list[ContractOutstandingOut] = Field(default_factory=list)
    project_wise_billed_vs_paid: list[ProjectFinanceSummaryOut] = Field(default_factory=list)
    contract_wise_outstanding: list[ContractOutstandingOut] = Field(default_factory=list)
    monthly_billing_trend: list[MonthlyTrendPointOut] = Field(default_factory=list)
    monthly_payment_trend: list[MonthlyTrendPointOut] = Field(default_factory=list)
    deductions_summary: list[DeductionSummaryOut] = Field(default_factory=list)
    retention_outstanding_summary: RetentionOutstandingSummaryOut


class ProjectDashboardOut(BaseModel):
    project_id: int
    project_name: str
    project_code: str | None = None
    status: str
    original_value: float
    revised_value: float
    contract_count: int
    active_contract_count: int
    total_billed_amount: float
    total_paid_amount: float
    outstanding_payable: float
    secured_advance_outstanding: float
    pending_ra_bills_by_status: list[StatusCountOut] = Field(default_factory=list)
    pending_payments_by_status: list[StatusCountOut] = Field(default_factory=list)
    contract_wise_finance_summary: list[ContractOutstandingOut] = Field(default_factory=list)
    monthly_billing_trend: list[MonthlyTrendPointOut] = Field(default_factory=list)
    monthly_payment_trend: list[MonthlyTrendPointOut] = Field(default_factory=list)
    deductions_summary: list[DeductionSummaryOut] = Field(default_factory=list)
    contract_wise_outstanding: list[ContractOutstandingOut] = Field(default_factory=list)


class ContractDashboardOut(BaseModel):
    contract_id: int
    project_id: int
    project_name: str
    vendor_id: int
    contract_no: str
    contract_title: str
    status: str
    original_value: float
    revised_value: float
    total_billed_amount: float
    total_paid_amount: float
    outstanding_payable: float
    secured_advance_outstanding: float
    pending_ra_bills_by_status: list[StatusCountOut] = Field(default_factory=list)
    pending_payments_by_status: list[StatusCountOut] = Field(default_factory=list)
    monthly_billing_trend: list[MonthlyTrendPointOut] = Field(default_factory=list)
    monthly_payment_trend: list[MonthlyTrendPointOut] = Field(default_factory=list)
    deductions_summary: list[DeductionSummaryOut] = Field(default_factory=list)
    retention_outstanding_amount: float
