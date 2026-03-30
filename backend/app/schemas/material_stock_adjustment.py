"""Material stock adjustment schemas."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class MaterialStockAdjustmentItemCreate(BaseModel):
    material_id: int = Field(..., ge=1)
    qty_change: float
    unit_rate: float = Field(default=0, ge=0)


class MaterialStockAdjustmentItemUpdate(BaseModel):
    id: int = Field(..., ge=1)
    qty_change: Optional[float] = None
    unit_rate: Optional[float] = Field(default=None, ge=0)


class MaterialStockAdjustmentCreate(BaseModel):
    adjustment_no: str = Field(..., min_length=1, max_length=100)
    project_id: int = Field(..., ge=1)
    adjusted_by: Optional[int] = Field(default=None, ge=1)
    adjustment_date: date
    status: str = Field(default="posted", max_length=30)
    reason: Optional[str] = Field(default=None, max_length=255)
    remarks: Optional[str] = None
    items: list[MaterialStockAdjustmentItemCreate] = Field(..., min_length=1)


class MaterialStockAdjustmentUpdate(BaseModel):
    adjustment_no: Optional[str] = Field(default=None, min_length=1, max_length=100)
    project_id: Optional[int] = Field(default=None, ge=1)
    adjusted_by: Optional[int] = Field(default=None, ge=1)
    adjustment_date: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=30)
    reason: Optional[str] = Field(default=None, max_length=255)
    remarks: Optional[str] = None
    items: Optional[list[MaterialStockAdjustmentItemUpdate]] = None


class MaterialStockAdjustmentItemOut(BaseModel):
    id: int
    material_id: int
    qty_change: float
    unit_rate: float
    line_amount: float
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class MaterialStockAdjustmentOut(BaseModel):
    id: int
    adjustment_no: str
    project_id: int
    adjusted_by: int
    adjustment_date: date
    status: str
    reason: Optional[str]
    remarks: Optional[str]
    total_amount: float
    created_at: datetime
    updated_at: Optional[datetime]
    items: list[MaterialStockAdjustmentItemOut]

    model_config = {"from_attributes": True}
