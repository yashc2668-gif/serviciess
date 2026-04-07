"""Bar bending schedule schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BBSCreate(BaseModel):
    contract_id: int
    drawing_no: str = Field(..., min_length=1, max_length=120)
    member_location: str = Field(..., min_length=1, max_length=255)
    bar_mark: str = Field(..., min_length=1, max_length=80)
    dia_mm: float = Field(..., ge=0)
    cut_length_mm: float = Field(..., ge=0)
    shape_code: Optional[str] = Field(default=None, max_length=60)
    nos: int = Field(..., ge=0)
    unit_weight: float = Field(..., ge=0)
    total_weight: Optional[float] = Field(default=None, ge=0)
    remarks: Optional[str] = Field(default=None, max_length=1000)


class BBSUpdate(BaseModel):
    drawing_no: Optional[str] = Field(default=None, min_length=1, max_length=120)
    member_location: Optional[str] = Field(default=None, min_length=1, max_length=255)
    bar_mark: Optional[str] = Field(default=None, min_length=1, max_length=80)
    dia_mm: Optional[float] = Field(default=None, ge=0)
    cut_length_mm: Optional[float] = Field(default=None, ge=0)
    shape_code: Optional[str] = Field(default=None, max_length=60)
    nos: Optional[int] = Field(default=None, ge=0)
    unit_weight: Optional[float] = Field(default=None, ge=0)
    total_weight: Optional[float] = Field(default=None, ge=0)
    remarks: Optional[str] = Field(default=None, max_length=1000)
    lock_version: Optional[int] = Field(default=None, ge=1)


class BBSOut(BaseModel):
    id: int
    contract_id: int
    drawing_no: str
    member_location: str
    bar_mark: str
    dia_mm: float
    cut_length_mm: float
    shape_code: Optional[str]
    nos: int
    unit_weight: float
    total_weight: float
    remarks: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    lock_version: int

    model_config = {"from_attributes": True}
