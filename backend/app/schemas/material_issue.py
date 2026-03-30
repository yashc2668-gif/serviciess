"""Material issue schemas."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class MaterialIssueItemCreate(BaseModel):
    material_id: int = Field(..., ge=1)
    issued_qty: float = Field(..., gt=0)
    unit_rate: float = Field(default=0, ge=0)


class MaterialIssueItemUpdate(BaseModel):
    id: int = Field(..., ge=1)
    issued_qty: Optional[float] = Field(default=None, gt=0)
    unit_rate: Optional[float] = Field(default=None, ge=0)


class MaterialIssueCreate(BaseModel):
    issue_no: str = Field(..., min_length=1, max_length=100)
    project_id: int = Field(..., ge=1)
    contract_id: Optional[int] = Field(default=None, ge=1)
    issued_by: Optional[int] = Field(default=None, ge=1)
    issue_date: date
    status: str = Field(default="issued", max_length=30)
    site_name: Optional[str] = Field(default=None, max_length=255)
    activity_name: Optional[str] = Field(default=None, max_length=255)
    remarks: Optional[str] = None
    items: list[MaterialIssueItemCreate] = Field(..., min_length=1)


class MaterialIssueUpdate(BaseModel):
    issue_no: Optional[str] = Field(default=None, min_length=1, max_length=100)
    project_id: Optional[int] = Field(default=None, ge=1)
    contract_id: Optional[int] = Field(default=None, ge=1)
    issued_by: Optional[int] = Field(default=None, ge=1)
    issue_date: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=30)
    site_name: Optional[str] = Field(default=None, max_length=255)
    activity_name: Optional[str] = Field(default=None, max_length=255)
    remarks: Optional[str] = None
    items: Optional[list[MaterialIssueItemUpdate]] = None


class MaterialIssueItemOut(BaseModel):
    id: int
    material_id: int
    issued_qty: float
    unit_rate: float
    line_amount: float
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class MaterialIssueOut(BaseModel):
    id: int
    issue_no: str
    project_id: int
    contract_id: Optional[int]
    issued_by: int
    issue_date: date
    status: str
    site_name: Optional[str]
    activity_name: Optional[str]
    remarks: Optional[str]
    total_amount: float
    created_at: datetime
    updated_at: Optional[datetime]
    items: list[MaterialIssueItemOut]

    model_config = {"from_attributes": True}
