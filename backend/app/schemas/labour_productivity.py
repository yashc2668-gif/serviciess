"""Labour productivity schemas."""

from datetime import date as dt_date
from datetime import datetime
from typing import Optional

from pydantic import AliasChoices, BaseModel, Field


class LabourProductivityCreate(BaseModel):
    project_id: int = Field(..., ge=1)
    contract_id: Optional[int] = Field(default=None, ge=1)
    date: dt_date = Field(
        ...,
        validation_alias=AliasChoices("date", "productivity_date"),
    )
    trade: str = Field(
        ...,
        min_length=2,
        max_length=100,
        validation_alias=AliasChoices("trade", "activity_name"),
    )
    quantity_done: float = Field(
        ...,
        gt=0,
        validation_alias=AliasChoices("quantity_done", "quantity"),
    )
    labour_count: int = Field(default=1, ge=1)
    productivity_value: Optional[float] = Field(default=None, ge=0)

    # Backward-compatible fields accepted and stored where applicable.
    labour_id: Optional[int] = Field(default=None, ge=1)
    unit: str = Field(default="unit", min_length=1, max_length=30)
    remarks: Optional[str] = None


class LabourProductivityUpdate(BaseModel):
    contract_id: Optional[int] = Field(default=None, ge=1)
    date: Optional[dt_date] = Field(
        default=None,
        validation_alias=AliasChoices("date", "productivity_date"),
    )
    trade: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
        validation_alias=AliasChoices("trade", "activity_name"),
    )
    quantity_done: Optional[float] = Field(
        default=None,
        gt=0,
        validation_alias=AliasChoices("quantity_done", "quantity"),
    )
    labour_count: Optional[int] = Field(default=None, ge=1)
    productivity_value: Optional[float] = Field(default=None, ge=0)

    labour_id: Optional[int] = Field(default=None, ge=1)
    unit: Optional[str] = Field(default=None, min_length=1, max_length=30)
    remarks: Optional[str] = None


class LabourProductivityOut(BaseModel):
    id: int
    project_id: int
    contract_id: Optional[int]
    date: Optional[dt_date]
    trade: Optional[str]
    quantity_done: float
    labour_count: int
    productivity_value: float

    # Backward-compatible output fields.
    labour_id: Optional[int]
    activity_name: str
    quantity: float
    unit: str
    productivity_date: dt_date
    remarks: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}
