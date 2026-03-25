"""Payment schemas."""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

PaymentStatus = Literal["draft", "approved", "released", "cancelled"]


class PaymentAllocationCreate(BaseModel):
    ra_bill_id: int
    amount: float = Field(..., gt=0)
    remarks: Optional[str] = Field(default=None, max_length=500)


class PaymentAllocationOut(BaseModel):
    id: int
    payment_id: int
    ra_bill_id: int
    amount: float
    remarks: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentCreate(BaseModel):
    contract_id: int
    payment_date: date
    amount: float = Field(..., gt=0)
    ra_bill_id: Optional[int] = None
    payment_mode: Optional[str] = Field(default=None, max_length=30)
    reference_no: Optional[str] = Field(default=None, max_length=100)
    remarks: Optional[str] = Field(default=None, max_length=500)


class PaymentActionRequest(BaseModel):
    remarks: Optional[str] = Field(default=None, max_length=500)


class OutstandingBillOut(BaseModel):
    ra_bill_id: int
    bill_no: int
    status: str
    net_payable: float
    paid_amount: float
    outstanding_amount: float


class PaymentOut(BaseModel):
    id: int
    contract_id: int
    payment_date: date
    amount: float
    status: PaymentStatus
    ra_bill_id: Optional[int]
    payment_mode: Optional[str]
    reference_no: Optional[str]
    remarks: Optional[str]
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    released_by: Optional[int]
    released_at: Optional[datetime]
    allocated_amount: float = 0
    available_amount: float = 0
    allocations: list[PaymentAllocationOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}
