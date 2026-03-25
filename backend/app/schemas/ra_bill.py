"""RA bill schemas."""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.secured_advance import SecuredAdvanceRecoveryApply

RABillStatus = Literal[
    "draft",
    "submitted",
    "verified",
    "approved",
    "rejected",
    "cancelled",
    "finance_hold",
    "partially_paid",
    "paid",
]


class DeductionCreate(BaseModel):
    deduction_type: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = Field(default=None, max_length=300)
    reason: Optional[str] = Field(default=None, max_length=500)
    percentage: Optional[float] = Field(default=None, ge=0, le=100)
    amount: float = 0
    secured_advance_id: Optional[int] = None
    is_system_generated: bool = False


class DeductionOut(BaseModel):
    id: int
    ra_bill_id: int
    deduction_type: str
    description: Optional[str]
    reason: Optional[str]
    percentage: Optional[float]
    amount: float
    secured_advance_id: Optional[int]
    is_system_generated: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RABillItemOut(BaseModel):
    id: int
    ra_bill_id: int
    work_done_item_id: int
    measurement_id: int
    boq_item_id: int
    item_code_snapshot: Optional[str]
    description_snapshot: str
    unit_snapshot: str
    prev_quantity: float
    curr_quantity: float
    cumulative_quantity: float
    rate: float
    amount: float
    created_at: datetime

    model_config = {"from_attributes": True}


class RABillCreate(BaseModel):
    contract_id: int
    bill_date: date
    bill_no: Optional[int] = Field(default=None, ge=1)
    period_from: Optional[date] = None
    period_to: Optional[date] = None
    remarks: Optional[str] = Field(default=None, max_length=500)
    deductions: list[DeductionCreate] = Field(default_factory=list)


class RABillGenerateRequest(BaseModel):
    tds_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    apply_contract_retention: bool = True
    deductions: list[DeductionCreate] = Field(default_factory=list)
    secured_advance_recoveries: list[SecuredAdvanceRecoveryApply] = Field(default_factory=list)


class RABillSubmitRequest(BaseModel):
    remarks: Optional[str] = Field(default=None, max_length=500)


class RABillTransitionRequest(BaseModel):
    remarks: Optional[str] = Field(default=None, max_length=1000)


class RABillStatusLogOut(BaseModel):
    id: int
    ra_bill_id: int
    from_status: Optional[str]
    to_status: str
    action: str
    remarks: Optional[str]
    actor_user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class RABillOut(BaseModel):
    id: int
    contract_id: int
    bill_no: int
    bill_date: date
    period_from: Optional[date]
    period_to: Optional[date]
    gross_amount: float
    total_deductions: float
    net_payable: float
    paid_amount: float = 0
    outstanding_amount: float = 0
    status: RABillStatus
    remarks: Optional[str]
    submitted_by: Optional[int]
    submitted_at: Optional[datetime]
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    items: list[RABillItemOut] = Field(default_factory=list)
    deductions: list[DeductionOut] = Field(default_factory=list)
    status_logs: list[RABillStatusLogOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}
