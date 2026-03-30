"""Auth service for register, login, refresh, logout, and password recovery."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.permissions import validate_role
from app.core.security import (
    constant_time_compare,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    generate_csrf_token,
    generate_otp_code,
    generate_token_id,
    hash_password,
    hash_token,
    utc_now,
    validate_password_policy,
    verify_password,
)
from app.db.session import get_db
from app.integrations.email import send_password_reset_otp_email
from app.models.password_reset_otp import PasswordResetOTP
from app.models.refresh_token_session import RefreshTokenSession
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenPayload,
    TokenResponse,
)
from app.schemas.user import UserOut
from app.services.audit_service import log_audit_event

logger = get_logger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def _log_auth_audit(
    db: Session,
    *,
    user_id: int,
    action: str,
    after_data: dict | None = None,
    remarks: str | None = None,
) -> None:
    """Record an auth event in the audit_logs table for compliance."""
    try:
        log_audit_event(
            db,
            entity_type="auth",
            entity_id=user_id,
            action=action,
            performed_by=user_id,
            after_data=after_data,
            remarks=remarks,
        )
    except Exception:
        logger.warning("audit.auth_event_failed", extra={"action": action, "user_id": user_id})


def _auth_exception(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _locked_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_423_LOCKED,
        detail=(
            f"Too many failed login attempts. Account locked for "
            f"{settings.LOGIN_LOCKOUT_MINUTES} minutes"
        ),
    )


def _password_reset_message() -> MessageResponse:
    return MessageResponse(
        message="If an account exists for that email, a reset code has been sent"
    )


def _get_client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    if request.client and request.client.host:
        return request.client.host
    return None


def _get_user_agent(request: Request) -> str | None:
    return request.headers.get("User-Agent")


def _set_auth_cookies(response: Response, *, refresh_token: str, csrf_token: str) -> None:
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    cookie_kwargs = {
        "max_age": max_age,
        "secure": settings.AUTH_COOKIE_SECURE,
        "samesite": settings.AUTH_COOKIE_SAMESITE,
        "path": "/api/v1/auth",
    }
    response.set_cookie(
        settings.REFRESH_TOKEN_COOKIE_NAME,
        refresh_token,
        httponly=True,
        **cookie_kwargs,
    )
    response.set_cookie(
        settings.CSRF_COOKIE_NAME,
        csrf_token,
        httponly=False,
        **cookie_kwargs,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.REFRESH_TOKEN_COOKIE_NAME, path="/api/v1/auth")
    response.delete_cookie(settings.CSRF_COOKIE_NAME, path="/api/v1/auth")


def _build_token_response(user: User, *, access_token: str, csrf_token: str) -> TokenResponse:
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_expires_in=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        csrf_token=csrf_token,
        user=UserOut.model_validate(user),
    )


def _get_user_or_none(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _current_utc() -> datetime:
    return _as_utc(utc_now()) or datetime.now(timezone.utc)


def _revoke_active_refresh_sessions(
    db: Session,
    *,
    user_id: int | None = None,
    family_id: str | None = None,
) -> None:
    if user_id is None and family_id is None:
        return
    query = db.query(RefreshTokenSession).filter(RefreshTokenSession.revoked_at.is_(None))
    if user_id is not None:
        query = query.filter(RefreshTokenSession.user_id == user_id)
    if family_id is not None:
        query = query.filter(RefreshTokenSession.family_id == family_id)
    now = utc_now()
    for session in query.all():
        session.revoked_at = now
        if family_id is not None:
            session.reuse_detected_at = now


def _reset_failed_login_state(user: User) -> None:
    user.failed_login_attempts = 0
    user.last_failed_login_at = None
    user.locked_until = None


def _prepare_user_for_auth(user: User | None) -> None:
    if user is None:
        return
    locked_until = _as_utc(user.locked_until)
    if locked_until and locked_until <= _current_utc():
        _reset_failed_login_state(user)


def _record_failed_login(db: Session, user: User) -> HTTPException | None:
    now = _current_utc()
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    user.last_failed_login_at = now
    if user.failed_login_attempts >= settings.LOGIN_LOCKOUT_THRESHOLD:
        user.locked_until = now + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
        _log_auth_audit(
            db,
            user_id=user.id,
            action="account_locked",
            after_data={"attempts": user.failed_login_attempts},
            remarks=f"Account locked after {user.failed_login_attempts} failed attempts",
        )
        db.commit()
        return _locked_exception()
    _log_auth_audit(
        db,
        user_id=user.id,
        action="login_failed",
        after_data={"attempts": user.failed_login_attempts},
    )
    db.commit()
    return None


def _assert_user_can_login(user: User) -> None:
    locked_until = _as_utc(user.locked_until)
    if locked_until and locked_until > _current_utc():
        raise _locked_exception()
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )


def _create_refresh_session(
    db: Session,
    *,
    user: User,
    request: Request,
    family_id: str | None = None,
) -> tuple[RefreshTokenSession, str, str]:
    family_id = family_id or generate_token_id()
    refresh_jti = generate_token_id()
    csrf_token = generate_csrf_token()
    refresh_token = create_refresh_token(
        {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "family_id": family_id,
        },
        jti=refresh_jti,
    )
    refresh_session = RefreshTokenSession(
        user_id=user.id,
        family_id=family_id,
        token_jti=refresh_jti,
        token_hash=hash_token(refresh_token),
        csrf_token_hash=hash_token(csrf_token),
        user_agent=_get_user_agent(request),
        ip_address=_get_client_ip(request),
        expires_at=utc_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_session)
    db.flush()
    return refresh_session, refresh_token, csrf_token


def _issue_session(
    db: Session,
    *,
    user: User,
    request: Request,
    response: Response,
    family_id: str | None = None,
) -> TokenResponse:
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
        }
    )
    _, refresh_token, csrf_token = _create_refresh_session(
        db,
        user=user,
        request=request,
        family_id=family_id,
    )
    db.commit()
    db.refresh(user)
    _set_auth_cookies(response, refresh_token=refresh_token, csrf_token=csrf_token)
    return _build_token_response(user, access_token=access_token, csrf_token=csrf_token)


def _extract_refresh_context(request: Request) -> tuple[str, str, str]:
    refresh_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    csrf_cookie = request.cookies.get(settings.CSRF_COOKIE_NAME)
    csrf_header = request.headers.get(settings.CSRF_HEADER_NAME)
    if not refresh_token:
        raise _auth_exception("Refresh session not found")
    if not csrf_cookie or not csrf_header or not constant_time_compare(csrf_cookie, csrf_header):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed",
        )
    return refresh_token, csrf_cookie, csrf_header


def _get_refresh_session_or_revoke_family(
    db: Session,
    *,
    token_payload: TokenPayload,
    refresh_token: str,
) -> RefreshTokenSession:
    session = (
        db.query(RefreshTokenSession)
        .filter(RefreshTokenSession.token_jti == token_payload.jti)
        .first()
    )
    if session is None:
        raise _auth_exception("Invalid or expired refresh token")

    if not constant_time_compare(session.token_hash, hash_token(refresh_token)):
        _revoke_active_refresh_sessions(db, family_id=session.family_id)
        db.commit()
        raise _auth_exception("Invalid or expired refresh token")

    now = _current_utc()
    if _as_utc(session.expires_at) <= now:
        session.revoked_at = session.revoked_at or now
        db.commit()
        raise _auth_exception("Invalid or expired refresh token")

    if session.revoked_at is not None:
        session.reuse_detected_at = now
        _log_auth_audit(
            db,
            user_id=session.user_id,
            action="token_reuse_detected",
            after_data={"family_id": session.family_id, "jti": token_payload.jti},
            remarks="Refresh token reuse detected — entire token family revoked",
        )
        _revoke_active_refresh_sessions(db, family_id=session.family_id)
        db.commit()
        raise _auth_exception("Invalid or expired refresh token")

    return session


def _verify_refresh_csrf(session: RefreshTokenSession, csrf_cookie: str) -> None:
    if not constant_time_compare(session.csrf_token_hash, hash_token(csrf_cookie)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed",
        )


def register_user(db: Session, payload: RegisterRequest) -> User:
    requested_role = validate_role(payload.role)
    if requested_role != "viewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration only allows the viewer role",
        )

    existing = _get_user_or_none(db, payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    validate_password_policy(payload.password, email=payload.email)
    user = User(
        company_id=payload.company_id,
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        phone=payload.phone,
        role="viewer",
        is_active=True,
        password_changed_at=utc_now(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(
    db: Session,
    payload: LoginRequest,
    *,
    request: Request,
    response: Response,
) -> TokenResponse:
    user = _get_user_or_none(db, payload.email)
    _prepare_user_for_auth(user)
    if user is not None:
        _assert_user_can_login(user)

    if not user or not verify_password(payload.password, user.hashed_password):
        if user is not None:
            exception = _record_failed_login(db, user)
            if exception is not None:
                raise exception
        raise _auth_exception("Invalid email or password")

    _reset_failed_login_state(user)
    token_response = _issue_session(db, user=user, request=request, response=response)
    _log_auth_audit(
        db,
        user_id=user.id,
        action="login_success",
        after_data={"ip": _get_client_ip(request), "user_agent": _get_user_agent(request)},
    )
    db.commit()
    return token_response


def refresh_session(db: Session, *, request: Request, response: Response) -> TokenResponse:
    refresh_token, csrf_cookie, _ = _extract_refresh_context(request)
    payload = decode_refresh_token(refresh_token)
    if payload is None:
        clear_auth_cookies(response)
        raise _auth_exception("Invalid or expired refresh token")

    try:
        token_payload = TokenPayload.model_validate(payload)
        user_id = int(token_payload.sub)
    except (ValueError, TypeError):
        clear_auth_cookies(response)
        raise _auth_exception("Invalid token payload")

    refresh_session_record = _get_refresh_session_or_revoke_family(
        db,
        token_payload=token_payload,
        refresh_token=refresh_token,
    )
    _verify_refresh_csrf(refresh_session_record, csrf_cookie)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        clear_auth_cookies(response)
        raise _auth_exception("User not found")

    _prepare_user_for_auth(user)
    _assert_user_can_login(user)

    now = _current_utc()
    refresh_session_record.rotated_at = now
    refresh_session_record.revoked_at = now

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
        }
    )
    new_session, new_refresh_token, new_csrf_token = _create_refresh_session(
        db,
        user=user,
        request=request,
        family_id=refresh_session_record.family_id,
    )
    refresh_session_record.replaced_by_jti = new_session.token_jti
    db.commit()
    db.refresh(user)

    _set_auth_cookies(response, refresh_token=new_refresh_token, csrf_token=new_csrf_token)
    return _build_token_response(user, access_token=access_token, csrf_token=new_csrf_token)


def logout_user(
    db: Session,
    *,
    request: Request,
    response: Response,
    payload: LogoutRequest,
) -> MessageResponse:
    refresh_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    csrf_cookie = request.cookies.get(settings.CSRF_COOKIE_NAME)
    csrf_header = request.headers.get(settings.CSRF_HEADER_NAME)
    clear_auth_cookies(response)
    if not refresh_token:
        return MessageResponse(message="Session closed")
    if not csrf_cookie or not csrf_header or not constant_time_compare(csrf_cookie, csrf_header):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")

    token_payload = decode_refresh_token(refresh_token)
    if token_payload is None:
        return MessageResponse(message="Session closed")

    try:
        parsed = TokenPayload.model_validate(token_payload)
        user_id = int(parsed.sub)
    except (ValueError, TypeError):
        return MessageResponse(message="Session closed")

    session = (
        db.query(RefreshTokenSession)
        .filter(RefreshTokenSession.token_jti == parsed.jti)
        .first()
    )
    now = _current_utc()
    if payload.revoke_all_sessions:
        _revoke_active_refresh_sessions(db, user_id=user_id)
    elif session is not None and session.revoked_at is None:
        session.revoked_at = now
    db.commit()
    return MessageResponse(message="Session closed")


def send_password_reset_code(
    db: Session,
    payload: ForgotPasswordRequest,
    *,
    request: Request,
) -> MessageResponse:
    user = _get_user_or_none(db, payload.email)
    if user is None or not user.is_active:
        return _password_reset_message()

    now = utc_now()
    (
        db.query(PasswordResetOTP)
        .filter(
            PasswordResetOTP.user_id == user.id,
            PasswordResetOTP.consumed_at.is_(None),
            PasswordResetOTP.expires_at > now,
        )
        .update({PasswordResetOTP.consumed_at: now}, synchronize_session=False)
    )

    otp_code = generate_otp_code()
    reset_code = PasswordResetOTP(
        user_id=user.id,
        otp_hash=hash_token(otp_code),
        expires_at=now + timedelta(minutes=settings.PASSWORD_RESET_OTP_EXPIRE_MINUTES),
        requested_ip=_get_client_ip(request),
        requested_user_agent=_get_user_agent(request),
    )
    db.add(reset_code)
    db.commit()

    send_password_reset_otp_email(recipient_email=user.email, otp_code=otp_code)
    return _password_reset_message()


def reset_password(db: Session, payload: ResetPasswordRequest) -> MessageResponse:
    user = _get_user_or_none(db, payload.email)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code",
        )

    now = utc_now()
    reset_record = (
        db.query(PasswordResetOTP)
        .filter(
            PasswordResetOTP.user_id == user.id,
            PasswordResetOTP.consumed_at.is_(None),
        )
        .order_by(PasswordResetOTP.created_at.desc(), PasswordResetOTP.id.desc())
        .first()
    )
    if reset_record is None or _as_utc(reset_record.expires_at) <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code",
        )

    if not constant_time_compare(reset_record.otp_hash, hash_token(payload.otp_code)):
        reset_record.attempts_count += 1
        if reset_record.attempts_count >= settings.LOGIN_LOCKOUT_THRESHOLD:
            reset_record.consumed_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code",
        )

    validate_password_policy(payload.new_password, email=payload.email)
    user.hashed_password = hash_password(payload.new_password)
    user.password_changed_at = now
    _reset_failed_login_state(user)
    reset_record.consumed_at = now
    _revoke_active_refresh_sessions(db, user_id=user.id)
    _log_auth_audit(
        db,
        user_id=user.id,
        action="password_reset",
        remarks="Password reset via OTP — all sessions revoked",
    )
    db.commit()

    logger.info(
        "auth.password_reset_completed",
        extra={
            "event": "auth.password_reset_completed",
            "user_id": user.id,
            "email": user.email,
        },
    )
    return MessageResponse(message="Password has been reset successfully")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise _auth_exception("Invalid or expired token")

    try:
        token_payload = TokenPayload.model_validate(payload)
        user_id = int(token_payload.sub)
    except (ValueError, TypeError):
        raise _auth_exception("Invalid token payload")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise _auth_exception("User not found")
    if not user.is_active:
        raise _auth_exception("User account is inactive")
    return user
