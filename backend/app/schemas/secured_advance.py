"""Secured advance schemas."""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

SecuredAdvanceStatus = Literal["active", "fully_recovered", "written_off"]


class SecuredAdvanceIssueCreate(BaseModel):
    contract_id: int
    advance_date: date
    description: Optional[str] = Field(default=None, max_length=500)
    advance_amount: float = Field(..., gt=0)


class SecuredAdvanceRecoveryApply(BaseModel):
    secured_advance_id: int
    amount: float = Field(..., gt=0)
    reason: Optional[str] = Field(default=None, max_length=500)


class SecuredAdvanceRecoveryOut(BaseModel):
    id: int
    secured_advance_id: int
    ra_bill_id: int
    recovery_date: date
    amount: float
    remarks: Optional[str]
    created_by: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class SecuredAdvanceUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=500)
    status: Optional[SecuredAdvanceStatus] = None


class SecuredAdvanceOut(BaseModel):
    id: int
    contract_id: int
    advance_date: date
    description: Optional[str]
    advance_amount: float
    recovered_amount: float
    balance: float
    status: SecuredAdvanceStatus
    issued_by: Optional[int]
    recovery_count: int = 0
    recoveries: list[SecuredAdvanceRecoveryOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}
