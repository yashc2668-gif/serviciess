"""Contract schemas."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.boq import BOQItemOut
from app.schemas.vendor import VendorOut


class ContractRevisionOut(BaseModel):
    id: int
    revision_no: str
    revised_value: float
    effective_date: Optional[date]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ContractCreate(BaseModel):
    project_id: int
    vendor_id: int
    contract_no: str = Field(..., min_length=2, max_length=100)
    title: str = Field(..., min_length=2, max_length=255)
    scope_of_work: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    original_value: float = 0
    revised_value: float = 0
    retention_percentage: float = 0
    status: str = "active"


class ContractUpdate(BaseModel):
    lock_version: Optional[int] = Field(default=None, ge=1)
    vendor_id: Optional[int] = None
    contract_no: Optional[str] = Field(default=None, min_length=2, max_length=100)
    title: Optional[str] = Field(default=None, min_length=2, max_length=255)
    scope_of_work: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    original_value: Optional[float] = None
    revised_value: Optional[float] = None
    retention_percentage: Optional[float] = None
    status: Optional[str] = None


class ContractOut(BaseModel):
    id: int
    project_id: int
    vendor_id: int
    contract_no: str
    title: str
    scope_of_work: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    original_value: float
    revised_value: float
    retention_percentage: float
    status: str
    lock_version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ContractDetailOut(ContractOut):
    vendor: VendorOut
    revisions: list[ContractRevisionOut] = []
    boq_items: list[BOQItemOut] = []
