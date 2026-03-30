"""Authentication endpoints."""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    ProtectedRouteResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.user import UserOut
from app.services.auth_service import (
    authenticate_user,
    logout_user,
    refresh_session,
    register_user,
    reset_password,
    send_password_reset_code,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut, status_code=201)
@limiter.limit(settings.AUTH_RATE_LIMIT_REGISTER)
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    return register_user(db, payload)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.AUTH_RATE_LIMIT_LOGIN)
def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    return authenticate_user(db, payload, request=request, response=response)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(settings.AUTH_RATE_LIMIT_REFRESH)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    return refresh_session(db, request=request, response=response)


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    payload: LogoutRequest,
    db: Session = Depends(get_db),
):
    return logout_user(db, request=request, response=response, payload=payload)


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit(settings.AUTH_RATE_LIMIT_FORGOT_PASSWORD)
def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    return send_password_reset_code(db, payload, request=request)


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit(settings.AUTH_RATE_LIMIT_RESET_PASSWORD)
def reset_password_route(request: Request, payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    return reset_password(db, payload)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/protected-test", response_model=ProtectedRouteResponse)
def protected_test(current_user: User = Depends(get_current_user)):
    return ProtectedRouteResponse(
        message="Authenticated request successful",
        user=UserOut.model_validate(current_user),
    )
