"""Material master schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MaterialCreate(BaseModel):
    item_code: str = Field(..., min_length=1, max_length=50)
    item_name: str = Field(..., min_length=2, max_length=255)
    category: Optional[str] = Field(default=None, max_length=100)
    unit: str = Field(..., min_length=1, max_length=30)
    reorder_level: float = Field(default=0, ge=0)
    default_rate: float = Field(default=0, ge=0)
    current_stock: float = Field(default=0, ge=0)
    is_active: bool = True
    company_id: Optional[int] = Field(default=None, ge=1)
    project_id: Optional[int] = Field(default=None, ge=1)


class MaterialUpdate(BaseModel):
    lock_version: Optional[int] = Field(default=None, ge=1)
    item_code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    item_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    category: Optional[str] = Field(default=None, max_length=100)
    unit: Optional[str] = Field(default=None, min_length=1, max_length=30)
    reorder_level: Optional[float] = Field(default=None, ge=0)
    default_rate: Optional[float] = Field(default=None, ge=0)
    current_stock: Optional[float] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    company_id: Optional[int] = Field(default=None, ge=1)
    project_id: Optional[int] = Field(default=None, ge=1)


class MaterialOut(BaseModel):
    id: int
    item_code: str
    item_name: str
    category: Optional[str]
    unit: str
    reorder_level: float
    default_rate: float
    current_stock: float
    is_active: bool
    company_id: Optional[int]
    project_id: Optional[int]
    lock_version: int
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class MaterialStockSummaryOut(BaseModel):
    scope_type: str
    scope_id: Optional[int]
    scope_name: Optional[str]
    material_count: int
    total_stock: float
