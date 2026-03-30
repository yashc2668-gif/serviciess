"""Labour advance schemas."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class LabourAdvanceRecoveryCreate(BaseModel):
    labour_bill_id: Optional[int] = Field(default=None, ge=1)
    recovery_date: date
    amount: float = Field(..., gt=0)
    remarks: Optional[str] = None


class LabourAdvanceCreate(BaseModel):
    advance_no: str = Field(..., min_length=1, max_length=100)
    project_id: int = Field(..., ge=1)
    contractor_id: int = Field(..., ge=1)
    advance_date: date
    amount: float = Field(..., gt=0)
    status: str = Field(default="active", max_length=30)
    remarks: Optional[str] = None


class LabourAdvanceUpdate(BaseModel):
    advance_no: Optional[str] = Field(default=None, min_length=1, max_length=100)
    contractor_id: Optional[int] = Field(default=None, ge=1)
    advance_date: Optional[date] = None
    amount: Optional[float] = Field(default=None, gt=0)
    status: Optional[str] = Field(default=None, max_length=30)
    remarks: Optional[str] = None


class LabourAdvanceRecoveryOut(BaseModel):
    id: int
    advance_id: int
    labour_bill_id: Optional[int]
    recovery_date: date
    amount: float
    remarks: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class LabourAdvanceOut(BaseModel):
    id: int
    advance_no: str
    project_id: int
    contractor_id: int
    advance_date: date
    amount: float
    recovered_amount: float
    balance_amount: float
    status: str
    remarks: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    recoveries: list[LabourAdvanceRecoveryOut]

    model_config = {"from_attributes": True}
