"""Authentication endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    ProtectedRouteResponse,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserOut
from app.services.auth_service import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    return register_user(db, payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return authenticate_user(db, payload)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/protected-test", response_model=ProtectedRouteResponse)
def protected_test(current_user: User = Depends(get_current_user)):
    return ProtectedRouteResponse(
        message="Authenticated request successful",
        user=UserOut.model_validate(current_user),
    )
