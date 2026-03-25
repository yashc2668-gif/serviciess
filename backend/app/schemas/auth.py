"""Authentication schemas."""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserOut


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    phone: Optional[str] = Field(default=None, max_length=20)
    role: str = Field(default="viewer", max_length=30)
    company_id: Optional[int] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class TokenPayload(BaseModel):
    sub: str
    email: EmailStr
    role: str
    exp: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class ProtectedRouteResponse(BaseModel):
    message: str
    user: UserOut
