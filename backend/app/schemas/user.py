"""User schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    company_id: Optional[int] = None
    full_name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None
    role: str = "viewer"


class UserUpdate(BaseModel):
    company_id: Optional[int] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserOut(BaseModel):
    id: int
    company_id: Optional[int]
    full_name: str
    email: str
    phone: Optional[str]
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
