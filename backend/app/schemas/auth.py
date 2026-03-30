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


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=4, max_length=10)
    new_password: str = Field(..., min_length=8, max_length=128)


class LogoutRequest(BaseModel):
    revoke_all_sessions: bool = False


class TokenPayload(BaseModel):
    sub: str
    email: EmailStr | None = None
    role: str | None = None
    exp: int
    type: str = "access"
    jti: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int
    csrf_token: str
    user: UserOut


class MessageResponse(BaseModel):
    message: str


class ProtectedRouteResponse(BaseModel):
    message: str
    user: UserOut
