"""Labour schemas."""

from datetime import datetime
from typing import Optional

from pydantic import AliasChoices, BaseModel, Field


class LabourCreate(BaseModel):
    company_id: Optional[int] = Field(default=None, ge=1)
    labour_code: str = Field(..., min_length=1, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=255)
    trade: Optional[str] = Field(
        default=None,
        max_length=100,
        validation_alias=AliasChoices("trade", "skill_type"),
    )
    skill_level: Optional[str] = Field(default=None, max_length=50)
    daily_rate: float = Field(
        default=0,
        ge=0,
        validation_alias=AliasChoices("daily_rate", "default_wage_rate"),
    )
    unit: str = Field(default="day", min_length=1, max_length=20)
    contractor_id: Optional[int] = Field(default=None, ge=1)
    is_active: bool = True


class LabourUpdate(BaseModel):
    lock_version: Optional[int] = Field(default=None, ge=1)
    company_id: Optional[int] = Field(default=None, ge=1)
    labour_code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    trade: Optional[str] = Field(
        default=None,
        max_length=100,
        validation_alias=AliasChoices("trade", "skill_type"),
    )
    skill_level: Optional[str] = Field(default=None, max_length=50)
    daily_rate: Optional[float] = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("daily_rate", "default_wage_rate"),
    )
    unit: Optional[str] = Field(default=None, min_length=1, max_length=20)
    contractor_id: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None


class LabourOut(BaseModel):
    id: int
    company_id: Optional[int]
    labour_code: str
    full_name: str
    trade: Optional[str]
    skill_level: Optional[str]
    daily_rate: float
    # Backward-compatible output fields.
    skill_type: Optional[str]
    default_wage_rate: float
    unit: str
    contractor_id: Optional[int]
    is_active: bool
    lock_version: int
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}
