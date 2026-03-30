"""Labour bill schemas."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class LabourBillItemCreate(BaseModel):
    attendance_id: Optional[int] = Field(default=None, ge=1)
    labour_id: Optional[int] = Field(default=None, ge=1)
    description: Optional[str] = Field(default=None, max_length=255)
    quantity: float = Field(default=0, ge=0)
    rate: float = Field(default=0, ge=0)
    amount: Optional[float] = Field(default=None, ge=0)


class LabourBillItemOut(BaseModel):
    id: int
    attendance_id: Optional[int]
    labour_id: Optional[int]
    description: Optional[str]
    quantity: float
    rate: float
    amount: float
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class LabourBillCreate(BaseModel):
    bill_no: str = Field(..., min_length=1, max_length=100)
    project_id: int = Field(..., ge=1)
    contract_id: Optional[int] = Field(default=None, ge=1)
    contractor_id: int = Field(..., ge=1)
    period_start: date
    period_end: date
    status: str = Field(default="draft", max_length=30)
    gross_amount: float = Field(default=0, ge=0)
    deductions: float = Field(default=0, ge=0)
    net_payable: Optional[float] = Field(default=None, ge=0)
    remarks: Optional[str] = None
    attendance_ids: Optional[list[int]] = Field(default=None, min_length=1)
    items: Optional[list[LabourBillItemCreate]] = Field(default=None, min_length=1)


class LabourBillUpdate(BaseModel):
    bill_no: Optional[str] = Field(default=None, min_length=1, max_length=100)
    project_id: Optional[int] = Field(default=None, ge=1)
    contract_id: Optional[int] = Field(default=None, ge=1)
    contractor_id: Optional[int] = Field(default=None, ge=1)
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=30)
    gross_amount: Optional[float] = Field(default=None, ge=0)
    deductions: Optional[float] = Field(default=None, ge=0)
    net_payable: Optional[float] = Field(default=None, ge=0)
    remarks: Optional[str] = None
    attendance_ids: Optional[list[int]] = Field(default=None, min_length=1)
    items: Optional[list[LabourBillItemCreate]] = Field(default=None, min_length=1)


class LabourBillTransitionRequest(BaseModel):
    remarks: Optional[str] = Field(default=None, max_length=1000)


class LabourBillOut(BaseModel):
    id: int
    bill_no: str
    project_id: int
    contract_id: Optional[int]
    contractor_id: int
    period_start: date
    period_end: date
    status: str
    gross_amount: float
    deductions: float
    net_payable: float
    # Backward-compatible output field.
    net_amount: float
    remarks: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    items: list[LabourBillItemOut]

    model_config = {"from_attributes": True}
