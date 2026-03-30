"""Material receipt schemas."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class MaterialReceiptItemCreate(BaseModel):
    material_id: int = Field(..., ge=1)
    received_qty: float = Field(..., gt=0)
    unit_rate: float = Field(default=0, ge=0)


class MaterialReceiptItemUpdate(BaseModel):
    id: int = Field(..., ge=1)
    received_qty: Optional[float] = Field(default=None, gt=0)
    unit_rate: Optional[float] = Field(default=None, ge=0)


class MaterialReceiptCreate(BaseModel):
    receipt_no: str = Field(..., min_length=1, max_length=100)
    vendor_id: int = Field(..., ge=1)
    project_id: int = Field(..., ge=1)
    received_by: Optional[int] = Field(default=None, ge=1)
    receipt_date: date
    status: str = Field(default="received", max_length=30)
    remarks: Optional[str] = None
    items: list[MaterialReceiptItemCreate] = Field(..., min_length=1)


class MaterialReceiptUpdate(BaseModel):
    receipt_no: Optional[str] = Field(default=None, min_length=1, max_length=100)
    vendor_id: Optional[int] = Field(default=None, ge=1)
    project_id: Optional[int] = Field(default=None, ge=1)
    received_by: Optional[int] = Field(default=None, ge=1)
    receipt_date: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=30)
    remarks: Optional[str] = None
    items: Optional[list[MaterialReceiptItemUpdate]] = None


class MaterialReceiptItemOut(BaseModel):
    id: int
    material_id: int
    received_qty: float
    unit_rate: float
    line_amount: float
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class MaterialReceiptOut(BaseModel):
    id: int
    receipt_no: str
    vendor_id: int
    project_id: int
    received_by: int
    receipt_date: date
    status: str
    remarks: Optional[str]
    total_amount: float
    created_at: datetime
    updated_at: Optional[datetime]
    items: list[MaterialReceiptItemOut]

    model_config = {"from_attributes": True}
