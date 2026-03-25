"""Company schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CompanyCreate(BaseModel):
    name: str
    address: Optional[str] = None
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class CompanyOut(BaseModel):
    id: int
    name: str
    address: Optional[str]
    gst_number: Optional[str]
    pan_number: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
