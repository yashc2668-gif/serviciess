"""Vendor schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VendorCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=50)
    vendor_type: str = Field(default="contractor", max_length=50)
    contact_person: Optional[str] = Field(default=None, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=255)
    gst_number: Optional[str] = Field(default=None, max_length=20)
    pan_number: Optional[str] = Field(default=None, max_length=15)
    address: Optional[str] = None


class VendorUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=50)
    vendor_type: Optional[str] = Field(default=None, max_length=50)
    contact_person: Optional[str] = Field(default=None, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=255)
    gst_number: Optional[str] = Field(default=None, max_length=20)
    pan_number: Optional[str] = Field(default=None, max_length=15)
    address: Optional[str] = None


class VendorOut(BaseModel):
    id: int
    name: str
    code: Optional[str]
    vendor_type: str
    contact_person: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    gst_number: Optional[str]
    pan_number: Optional[str]
    address: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
