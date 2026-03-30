"""Password hashing, password policy, and JWT/token utilities."""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re
import secrets
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_PASSWORD_SPECIAL_PATTERN = re.compile(r"[^A-Za-z0-9]")

_COMMON_PASSWORDS = frozenset({
    "password", "password1", "password123", "12345678", "123456789",
    "1234567890", "qwerty123", "letmein1", "welcome1", "admin123",
    "abc12345", "monkey123", "master123", "dragon123", "login123",
    "princess1", "football1", "shadow123", "sunshine1", "trustno1",
    "iloveyou1", "batman123", "access123", "hello123", "charlie1",
    "donald123", "password1!", "qwerty1!", "changeme", "changeme1",
    "p@ssw0rd", "p@ssword1", "passw0rd", "passw0rd!", "welcome1!",
})


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def validate_password_policy(password: str, *, email: str | None = None) -> None:
    failures: list[str] = []
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        failures.append(f"at least {settings.PASSWORD_MIN_LENGTH} characters")
    if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
        failures.append("one uppercase letter")
    if settings.PASSWORD_REQUIRE_NUMBER and not re.search(r"\d", password):
        failures.append("one number")
    if settings.PASSWORD_REQUIRE_SPECIAL and not _PASSWORD_SPECIAL_PATTERN.search(password):
        failures.append("one special character")
    if failures:
        requirement_text = ", ".join(failures)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must include {requirement_text}",
        )
    if password.lower() in _COMMON_PASSWORDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password is too common. Please choose a stronger password",
        )
    if email:
        local_part = email.split("@")[0].lower()
        if len(local_part) >= 4 and local_part in password.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must not contain your email address",
            )


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def constant_time_compare(a: str, b: str) -> bool:
    """Compare two strings in constant time to prevent timing attacks."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def generate_token_id() -> str:
    return uuid4().hex


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def generate_otp_code() -> str:
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(settings.PASSWORD_RESET_OTP_LENGTH))


def _encode_token(
    data: dict,
    *,
    token_type: str,
    expires_delta: timedelta,
    jti: str | None = None,
) -> str:
    to_encode = data.copy()
    to_encode.update(
        {
            "type": token_type,
            "jti": jti or generate_token_id(),
            "exp": utc_now() + expires_delta,
        }
    )
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    return _encode_token(
        data,
        token_type="access",
        expires_delta=expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(data: dict, *, jti: str, expires_delta: Optional[timedelta] = None) -> str:
    return _encode_token(
        data,
        token_type="refresh",
        jti=jti,
        expires_delta=expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


def decode_access_token(token: str) -> Optional[dict]:
    payload = decode_token(token)
    if payload is None:
        return None
    if payload.get("type") not in {None, "access"}:
        return None
    return payload


def decode_refresh_token(token: str) -> Optional[dict]:
    payload = decode_token(token)
    if payload is None:
        return None
    if payload.get("type") != "refresh":
        return None
    return payload
