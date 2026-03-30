"""M2N Construction ERP FastAPI entry point."""

from contextlib import asynccontextmanager
import json
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from starlette import status as http_status
from starlette.responses import Response

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import (
    configure_logging,
    get_logger,
    reset_request_id,
    set_request_id,
)
from app.core.rate_limit import limiter
from app.db.seed import run_seed
from app.db.session import engine, get_db
from app.services.idempotency_service import (
    abandon_request,
    build_idempotency_context,
    build_replay_response,
    claim_request,
    complete_request,
    ensure_request_matches,
    get_existing_record,
    should_apply_idempotency,
)
from app.utils.pagination import validate_pagination_query_params

configure_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


def _apply_security_headers(response: Response, request: Request) -> None:
    if not settings.SECURITY_HEADERS_ENABLED:
        return
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "accelerometer=(), camera=(), geolocation=(), gyroscope=(), microphone=()",
    )
    response.headers.setdefault("Content-Security-Policy", settings.CONTENT_SECURITY_POLICY)
    response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
    response.headers.setdefault("X-DNS-Prefetch-Control", "off")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    if request.url.scheme == "https" or settings.ENVIRONMENT in {"production", "prod"}:
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=63072000; includeSubDomains; preload",
        )
    if request.url.path.startswith("/api/v1/auth"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"


def _error_payload(
    *,
    request: Request,
    status_code: int,
    error_type: str,
    message: str,
    details=None,
) -> dict:
    payload = {
        "success": False,
        "error": {
            "type": error_type,
            "message": message,
        },
        "request_id": getattr(request.state, "request_id", None),
        "path": request.url.path,
        "status_code": status_code,
    }
    if details is not None:
        payload["error"]["details"] = details
    return payload


def _http_error_type(status_code: int) -> str:
    if status_code == http_status.HTTP_401_UNAUTHORIZED:
        return "authentication_error"
    if status_code == http_status.HTTP_403_FORBIDDEN:
        return "permission_denied"
    if status_code == http_status.HTTP_404_NOT_FOUND:
        return "not_found"
    if status_code in {
        http_status.HTTP_400_BAD_REQUEST,
        http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        http_status.HTTP_409_CONFLICT,
        http_status.HTTP_422_UNPROCESSABLE_ENTITY,
    }:
        return "validation_error"
    if status_code == http_status.HTTP_503_SERVICE_UNAVAILABLE:
        return "service_unavailable"
    return "http_error"


def _database_health_payload() -> dict:
    try:
        with engine.connect() as connection:
            ping = connection.execute(text("SELECT 1")).scalar_one()
            backend_name = connection.engine.url.get_backend_name()
            if backend_name == "sqlite":
                db_name = connection.engine.url.database or "sqlite"
                db_user = "sqlite"
            else:
                db_name = connection.execute(text("SELECT current_database()")).scalar_one()
                db_user = connection.execute(text("SELECT current_user")).scalar_one()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc

    return {
        "status": "ok",
        "database": db_name,
        "user": db_user,
        "ping": ping,
    }


def _open_aux_db_session(request: Request):
    db_dependency = request.app.dependency_overrides.get(get_db, get_db)
    db_resource = db_dependency()
    if hasattr(db_resource, "__next__"):
        return next(db_resource), db_resource
    return db_resource, None


async def _consume_response_body(response: Response) -> bytes:
    body = b""
    async for chunk in response.body_iterator:
        body += chunk
    return body


def _extract_replayable_payload(response: Response, response_body: bytes):
    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type.lower():
        return None
    if not response_body:
        return None
    return json.loads(response_body.decode("utf-8"))


def _rebuild_response(response: Response, response_body: bytes) -> Response:
    return Response(
        content=response_body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(
        "application.startup",
        extra={
            "event": "application.startup",
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "storage_backend": settings.STORAGE_BACKEND,
            "ai_enabled": settings.AI_ENABLED,
            "ai_mode": settings.AI_MODE,
        },
    )
    _database_health_payload()
    run_seed()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SlowAPIMiddleware)

app.include_router(api_router, prefix="/api/v1")


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    token = set_request_id(request_id)
    started_at = perf_counter()
    response = None
    idempotency_db = None
    idempotency_db_resource = None
    idempotency_record = None

    try:
        validate_pagination_query_params(request)
        if should_apply_idempotency(request):
            request_body = await request.body()
            body_sent = False

            async def receive():
                nonlocal body_sent
                if body_sent:
                    return {"type": "http.request", "body": b"", "more_body": False}
                body_sent = True
                return {"type": "http.request", "body": request_body, "more_body": False}

            request._receive = receive
            idempotency_context = build_idempotency_context(request, request_body)
            idempotency_db, idempotency_db_resource = _open_aux_db_session(request)
            existing_record = get_existing_record(idempotency_db, idempotency_context)
            if existing_record is not None:
                ensure_request_matches(existing_record, idempotency_context)
                if existing_record.status == "completed" and existing_record.response_body is not None:
                    response = build_replay_response(existing_record)
                    return response
                raise HTTPException(
                    status_code=http_status.HTTP_409_CONFLICT,
                    detail="A request with this Idempotency-Key is already in progress",
                )
            idempotency_record = claim_request(idempotency_db, idempotency_context)

        response = await call_next(request)
        if idempotency_db is not None and idempotency_record is not None:
            response_body = await _consume_response_body(response)
            replayable_payload = _extract_replayable_payload(response, response_body)
            response = _rebuild_response(response, response_body)
            if 200 <= response.status_code < 300 and replayable_payload is not None:
                complete_request(
                    idempotency_db,
                    idempotency_record,
                    response_status_code=response.status_code,
                    response_body=replayable_payload,
                )
            else:
                abandon_request(idempotency_db, idempotency_record)
                idempotency_record = None
        return response
    except HTTPException as exc:
        if idempotency_db is not None and idempotency_record is not None:
            abandon_request(idempotency_db, idempotency_record)
            idempotency_record = None
        response = await http_exception_handler(request, exc)
        return response
    except Exception:
        if idempotency_db is not None and idempotency_record is not None:
            abandon_request(idempotency_db, idempotency_record)
            idempotency_record = None
        logger.exception(
            "request.unhandled_exception",
            extra={
                "event": "request.unhandled_exception",
                "request_id": request_id,
                "method": request.method,
                "endpoint": request.url.path,
            },
        )
        raise
    finally:
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        status_code = response.status_code if response is not None else 500
        if response is not None:
            _apply_security_headers(response, request)
            response.headers["X-Request-ID"] = request_id
        logger.info(
            "request.completed",
            extra={
                "event": "request.completed",
                "request_id": request_id,
                "method": request.method,
                "endpoint": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )
        if idempotency_db_resource is not None:
            idempotency_db_resource.close()
        elif idempotency_db is not None:
            idempotency_db.close()
        reset_request_id(token)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        "request.validation_error",
        extra={
            "event": "request.validation_error",
            "request_id": getattr(request.state, "request_id", None),
            "endpoint": request.url.path,
            "method": request.method,
            "status_code": 422,
        },
    )
    return JSONResponse(
        status_code=422,
        content=_error_payload(
            request=request,
            status_code=422,
            error_type="validation_error",
            message="Validation failed",
            details=exc.errors(),
        ),
        headers={"X-Request-ID": getattr(request.state, "request_id", "")},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    status_code = exc.status_code
    error_type = _http_error_type(status_code)
    log_method = logger.warning if status_code < 500 else logger.error
    log_method(
        "request.http_error",
        extra={
            "event": "request.http_error",
            "request_id": getattr(request.state, "request_id", None),
            "endpoint": request.url.path,
            "method": request.method,
            "status_code": status_code,
            "error_type": error_type,
        },
    )
    payload = _error_payload(
        request=request,
        status_code=status_code,
        error_type=error_type,
        message=str(exc.detail),
    )
    headers = dict(exc.headers or {})
    headers["X-Request-ID"] = getattr(request.state, "request_id", "")
    return JSONResponse(status_code=status_code, content=payload, headers=headers)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(
        "request.rate_limited",
        extra={
            "event": "request.rate_limited",
            "request_id": getattr(request.state, "request_id", None),
            "endpoint": request.url.path,
            "method": request.method,
            "status_code": 429,
            "error_type": "rate_limit_exceeded",
        },
    )
    headers = {"X-Request-ID": getattr(request.state, "request_id", "")}
    retry_after = getattr(exc, "retry_after", None)
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    response = JSONResponse(
        status_code=429,
        content=_error_payload(
            request=request,
            status_code=429,
            error_type="rate_limit_exceeded",
            message="Too many requests. Please try again later",
        ),
        headers=headers,
    )
    _apply_security_headers(response, request)
    return response


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.warning(
        "request.db_conflict",
        extra={
            "event": "request.db_conflict",
            "request_id": getattr(request.state, "request_id", None),
            "endpoint": request.url.path,
            "method": request.method,
            "status_code": 409,
            "error_type": "db_conflict",
        },
        exc_info=exc,
    )
    return JSONResponse(
        status_code=409,
        content=_error_payload(
            request=request,
            status_code=409,
            error_type="db_conflict",
            message="Database conflict detected",
        ),
        headers={"X-Request-ID": getattr(request.state, "request_id", "")},
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    logger.error(
        "request.db_error",
        extra={
            "event": "request.db_error",
            "request_id": getattr(request.state, "request_id", None),
            "endpoint": request.url.path,
            "method": request.method,
            "status_code": 500,
            "error_type": "database_error",
        },
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content=_error_payload(
            request=request,
            status_code=500,
            error_type="database_error",
            message="A database error occurred while processing the request",
        ),
        headers={"X-Request-ID": getattr(request.state, "request_id", "")},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(
        "request.server_error",
        extra={
            "event": "request.server_error",
            "request_id": getattr(request.state, "request_id", None),
            "endpoint": request.url.path,
            "method": request.method,
            "status_code": 500,
            "error_type": "internal_server_error",
        },
        exc_info=exc,
    )
    message = str(exc) if settings.DEBUG else "An unexpected server error occurred"
    return JSONResponse(
        status_code=500,
        content=_error_payload(
            request=request,
            status_code=500,
            error_type="internal_server_error",
            message=message,
        ),
        headers={"X-Request-ID": getattr(request.state, "request_id", "")},
    )


@app.get("/")
def root():
    return {"message": "M2N Construction ERP API is running", "docs": "/docs"}


@app.get("/health")
def health():
    """Simple healthcheck - does not require database connection.
    Used by Railway for deployment healthchecks."""
    return {
        "status": "ok",
        "app": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/db")
def health_db():
    return _database_health_payload()


@app.get("/health/ready")
def health_ready():
    db_status = _database_health_payload()
    return {
        "status": "ready",
        "app": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
    }
