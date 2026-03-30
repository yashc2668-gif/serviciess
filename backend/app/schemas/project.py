"""Project schemas."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    company_id: int
    name: str = Field(..., min_length=2, max_length=300)
    code: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    client_name: Optional[str] = Field(default=None, max_length=255)
    location: Optional[str] = Field(default=None, max_length=300)
    original_value: float = 0
    revised_value: float = 0
    start_date: Optional[date] = None
    expected_end_date: Optional[date] = None
    status: str = "active"


class ProjectUpdate(BaseModel):
    lock_version: Optional[int] = Field(default=None, ge=1)
    company_id: Optional[int] = None
    name: Optional[str] = Field(default=None, min_length=2, max_length=300)
    code: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    client_name: Optional[str] = Field(default=None, max_length=255)
    location: Optional[str] = Field(default=None, max_length=300)
    original_value: Optional[float] = None
    revised_value: Optional[float] = None
    start_date: Optional[date] = None
    expected_end_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    status: Optional[str] = None


class ProjectOut(BaseModel):
    id: int
    company_id: int
    name: str
    code: Optional[str]
    description: Optional[str]
    client_name: Optional[str]
    location: Optional[str]
    original_value: float
    revised_value: float
    start_date: Optional[date]
    expected_end_date: Optional[date]
    actual_end_date: Optional[date]
    status: str
    lock_version: int
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}
