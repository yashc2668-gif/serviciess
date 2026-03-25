"""Measurement schemas."""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

MeasurementStatus = Literal["draft", "submitted", "approved"]


class MeasurementItemCreate(BaseModel):
    boq_item_id: int
    current_quantity: float = Field(..., ge=0)
    rate: Optional[float] = Field(default=None, ge=0)
    amount: float = Field(default=0, ge=0)
    allow_excess: bool = False
    remarks: Optional[str] = Field(default=None, max_length=500)


class MeasurementItemOut(BaseModel):
    id: int
    boq_item_id: int
    description_snapshot: str
    unit_snapshot: str
    previous_quantity: float
    current_quantity: float
    cumulative_quantity: float
    rate: float
    amount: float
    allow_excess: bool
    warning_message: Optional[str]
    remarks: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class MeasurementCreate(BaseModel):
    contract_id: int
    measurement_no: str = Field(..., min_length=2, max_length=100)
    measurement_date: date
    remarks: Optional[str] = None
    items: list[MeasurementItemCreate] = Field(default_factory=list)


class MeasurementUpdate(BaseModel):
    measurement_date: Optional[date] = None
    remarks: Optional[str] = None
    items: Optional[list[MeasurementItemCreate]] = None


class MeasurementOut(BaseModel):
    id: int
    contract_id: int
    measurement_no: str
    measurement_date: date
    status: MeasurementStatus
    remarks: Optional[str]
    created_by: Optional[int]
    submitted_by: Optional[int]
    approved_by: Optional[int]
    submitted_at: Optional[datetime]
    approved_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    items: list[MeasurementItemOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}
