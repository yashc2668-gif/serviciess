"""Site expense schemas."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

SiteExpenseStatus = Literal["draft", "approved", "paid"]


class SiteExpenseCreate(BaseModel):
    expense_no: str = Field(..., min_length=1, max_length=100)
    project_id: int = Field(..., ge=1)
    vendor_id: int | None = Field(default=None, ge=1)
    expense_date: date
    expense_head: str = Field(..., min_length=2, max_length=100)
    payee_name: str | None = Field(default=None, max_length=255)
    amount: float = Field(..., gt=0)
    payment_mode: str | None = Field(default=None, max_length=30)
    reference_no: str | None = Field(default=None, max_length=100)
    remarks: str | None = None


class SiteExpenseUpdate(BaseModel):
    lock_version: int | None = Field(default=None, ge=1)
    expense_no: str | None = Field(default=None, min_length=1, max_length=100)
    project_id: int | None = Field(default=None, ge=1)
    vendor_id: int | None = Field(default=None, ge=1)
    expense_date: date | None = None
    expense_head: str | None = Field(default=None, min_length=2, max_length=100)
    payee_name: str | None = Field(default=None, max_length=255)
    amount: float | None = Field(default=None, gt=0)
    payment_mode: str | None = Field(default=None, max_length=30)
    reference_no: str | None = Field(default=None, max_length=100)
    remarks: str | None = None


class SiteExpenseActionRequest(BaseModel):
    lock_version: int | None = Field(default=None, ge=1)
    remarks: str | None = Field(default=None, max_length=500)


class SiteExpenseOut(BaseModel):
    id: int
    expense_no: str
    project_id: int
    vendor_id: int | None
    expense_date: date
    expense_head: str
    payee_name: str | None
    amount: float
    payment_mode: str | None
    reference_no: str | None
    status: SiteExpenseStatus
    remarks: str | None
    created_by: int | None
    approved_by: int | None
    approved_at: datetime | None
    paid_by: int | None
    paid_at: datetime | None
    lock_version: int
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}
