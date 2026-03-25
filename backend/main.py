"""M2N Construction ERP FastAPI entry point."""

from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from starlette import status as http_status

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import (
    configure_logging,
    get_logger,
    reset_request_id,
    set_request_id,
)
from app.db.seed import run_seed
from app.db.session import engine

configure_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


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


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(
        "application.startup",
        extra={
            "event": "application.startup",
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "storage_backend": settings.STORAGE_BACKEND,
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    token = set_request_id(request_id)
    started_at = perf_counter()
    response = None

    try:
        response = await call_next(request)
        return response
    except Exception:
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
    return {
        "status": "ok",
        "app": settings.PROJECT_NAME,
        "debug": settings.DEBUG,
        "database_host": settings.POSTGRES_HOST,
        "database_name": settings.POSTGRES_DB,
        "cors_origins": settings.ALLOWED_ORIGINS,
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
