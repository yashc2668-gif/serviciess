"""Labour contractor schemas."""

from datetime import datetime
from typing import Optional

from pydantic import AliasChoices, BaseModel, Field


class LabourContractorCreate(BaseModel):
    company_id: Optional[int] = Field(default=None, ge=1)
    contractor_code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    contractor_name: str = Field(..., min_length=2, max_length=255)
    contact_person: Optional[str] = Field(
        default=None,
        max_length=255,
        validation_alias=AliasChoices("contact_person", "gang_name"),
    )
    phone: Optional[str] = Field(default=None, max_length=20)
    address: Optional[str] = None
    is_active: bool = True


class LabourContractorUpdate(BaseModel):
    lock_version: Optional[int] = Field(default=None, ge=1)
    company_id: Optional[int] = Field(default=None, ge=1)
    contractor_code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    contractor_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    contact_person: Optional[str] = Field(
        default=None,
        max_length=255,
        validation_alias=AliasChoices("contact_person", "gang_name"),
    )
    phone: Optional[str] = Field(default=None, max_length=20)
    address: Optional[str] = None
    is_active: Optional[bool] = None


class LabourContractorOut(BaseModel):
    id: int
    company_id: Optional[int]
    contractor_code: str
    contractor_name: str
    contact_person: Optional[str]
    address: Optional[str]
    # Backward-compatible output field.
    gang_name: Optional[str]
    phone: Optional[str]
    is_active: bool
    lock_version: int
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}
