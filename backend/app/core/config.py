import json
from urllib.parse import urlsplit, urlunsplit
from typing import Any, List, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    # Database
    DATABASE_URL: Optional[str] = None
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "marco_db"
    POSTGRES_USER: str = "marco_app"
    POSTGRES_PASSWORD: str = "marco_app_123"

    # JWT
    SECRET_KEY: str = "CHANGE-ME"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_TOKEN_COOKIE_NAME: str = "marco_refresh_token"
    CSRF_COOKIE_NAME: str = "marco_csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    AUTH_COOKIE_SAMESITE: str = "lax"
    AUTH_COOKIE_SECURE: bool = False
    AUTH_RATE_LIMIT_ENABLED: bool = True
    AUTH_RATE_LIMIT_GLOBAL: str = "100/minute"
    AUTH_RATE_LIMIT_LOGIN: str = "5/minute"
    AUTH_RATE_LIMIT_REGISTER: str = "3/minute"
    AUTH_RATE_LIMIT_FORGOT_PASSWORD: str = "3/minute"
    AUTH_RATE_LIMIT_RESET_PASSWORD: str = "5/minute"
    AUTH_RATE_LIMIT_REFRESH: str = "10/minute"
    LOGIN_LOCKOUT_THRESHOLD: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_NUMBER: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    PASSWORD_RESET_OTP_EXPIRE_MINUTES: int = 10
    PASSWORD_RESET_OTP_LENGTH: int = 6
    EMAIL_SENDER: str = "no-reply@marcoenterprises.local"
    PASSWORD_RESET_EMAIL_SUBJECT: str = "Your Marco Enterprises password reset code"

    # App
    PROJECT_NAME: str = "Marco Enterprises Construction ERP"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # File storage
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_ROOT: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_DOCUMENT_MIME_TYPES: List[str] = [
        "application/pdf",
        "image/png",
        "image/jpeg",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ]
    ALLOWED_DOCUMENT_EXTENSIONS: List[str] = [
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
    ]

    # Optional bootstrap admin
    ADMIN_EMAIL: Optional[str] = None
    ADMIN_PASSWORD: Optional[str] = None
    ADMIN_FULL_NAME: str = "Platform Admin"
    ADMIN_PHONE: Optional[str] = None
    ADMIN_ROLE: str = "admin"

    # AI boundary
    AI_ENABLED: bool = False
    AI_MODE: str = "disabled"
    AI_REQUIRE_HUMAN_REVIEW: bool = True
    AI_REQUIRE_BACKEND_VALIDATION: bool = True
    SECURITY_HEADERS_ENABLED: bool = True
    CONTENT_SECURITY_POLICY: str = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "connect-src 'self' http://localhost:5173 http://localhost:8000 "
        "https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app "
        "https://m2n-frontend-jel4ixehf-yashs-projects-8e52d41e.vercel.app; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, value: Any) -> Any:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "dev", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return value

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: Any) -> List[str]:
        """
        Parse ALLOWED_ORIGINS from various formats to a list of strings.
        
        Supports:
        1. Proper JSON array: ["http://localhost:5173","https://example.com"]
        2. Bracket-wrapped CSV: [http://localhost:5173,https://example.com] (Railway format)
        3. Plain comma-separated: http://localhost:5173,https://example.com
        4. Already a list: returns as-is
        5. Single URL string: returns as single-item list
        
        Args:
            value: The raw ALLOWED_ORIGINS value from env var or config
            
        Returns:
            List[str]: List of origin URLs
        """
        def normalize_origin(origin: Any) -> str:
            text = str(origin).strip().strip("\"'")
            if not text:
                return ""
            parsed = urlsplit(text)
            if parsed.scheme and parsed.netloc:
                normalized_path = parsed.path.rstrip("/")
                return urlunsplit(
                    (parsed.scheme.lower(), parsed.netloc.lower(), normalized_path, "", "")
                )
            return text.rstrip("/")

        def normalize_many(origins: list[Any]) -> List[str]:
            normalized: List[str] = []
            for origin in origins:
                cleaned = normalize_origin(origin)
                if cleaned and cleaned not in normalized:
                    normalized.append(cleaned)
            return normalized

        # Already a list - return as-is
        if isinstance(value, list):
            return normalize_many(value)
        
        # Not a string - return empty list
        if not isinstance(value, str):
            return []
        
        trimmed = value.strip().strip("\"'")
        
        # Empty string - return empty list
        if not trimmed:
            return []
        
        # Handle bracket-wrapped formats (JSON or Railway-style)
        if trimmed.startswith("["):
            # Try proper JSON first
            try:
                parsed = json.loads(trimmed)
                if isinstance(parsed, list):
                    return normalize_many(parsed)
                return []
            except json.JSONDecodeError:
                # Not valid JSON - treat as bracket-wrapped comma-separated
                # Remove opening '[' and trailing ']'
                inner = trimmed[1:].rstrip("]").strip()
                if not inner:
                    return []
                # Split by comma and clean each item
                return normalize_many(inner.split(","))

        # Plain comma-separated without brackets
        return normalize_many(trimmed.split(","))

    @field_validator(
        "DATABASE_URL",
        "ADMIN_EMAIL",
        "ADMIN_PASSWORD",
        "ADMIN_PHONE",
        mode="before",
    )
    @classmethod
    def empty_strings_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("ENVIRONMENT", "LOG_LEVEL", "AI_MODE", "AUTH_COOKIE_SAMESITE", mode="before")
    @classmethod
    def normalize_simple_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator(
        "ALLOWED_DOCUMENT_MIME_TYPES",
        "ALLOWED_DOCUMENT_EXTENSIONS",
        mode="before",
    )
    @classmethod
    def parse_list_settings(cls, value: Any) -> Any:
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed.startswith("["):
                return trimmed
            return [item.strip() for item in trimmed.split(",") if item.strip()]
        return value

    @field_validator("STORAGE_BACKEND", mode="before")
    @classmethod
    def normalize_storage_backend(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @model_validator(mode="after")
    def validate_runtime_settings(self):
        if self.APP_PORT <= 0 or self.APP_PORT > 65535:
            raise ValueError("APP_PORT must be between 1 and 65535")
        if self.ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than 0")
        if self.REFRESH_TOKEN_EXPIRE_DAYS <= 0:
            raise ValueError("REFRESH_TOKEN_EXPIRE_DAYS must be greater than 0")
        if self.LOGIN_LOCKOUT_THRESHOLD <= 0:
            raise ValueError("LOGIN_LOCKOUT_THRESHOLD must be greater than 0")
        if self.LOGIN_LOCKOUT_MINUTES <= 0:
            raise ValueError("LOGIN_LOCKOUT_MINUTES must be greater than 0")
        if self.PASSWORD_MIN_LENGTH < 8:
            raise ValueError("PASSWORD_MIN_LENGTH must be at least 8")
        if self.PASSWORD_RESET_OTP_EXPIRE_MINUTES <= 0:
            raise ValueError("PASSWORD_RESET_OTP_EXPIRE_MINUTES must be greater than 0")
        if self.PASSWORD_RESET_OTP_LENGTH < 4:
            raise ValueError("PASSWORD_RESET_OTP_LENGTH must be at least 4")
        if self.MAX_UPLOAD_SIZE_MB <= 0:
            raise ValueError("MAX_UPLOAD_SIZE_MB must be greater than 0")
        if self.ENVIRONMENT.lower() in {"production", "prod"} and self.SECRET_KEY == "CHANGE-ME":
            raise ValueError("SECRET_KEY must be changed before running in production")
        if self.ENVIRONMENT.lower() in {"production", "prod"} and self.DEBUG:
            raise ValueError("DEBUG must be disabled in production")
        if bool(self.ADMIN_EMAIL) ^ bool(self.ADMIN_PASSWORD):
            raise ValueError("ADMIN_EMAIL and ADMIN_PASSWORD must be provided together")
        if self.STORAGE_BACKEND not in {"local"}:
            raise ValueError("STORAGE_BACKEND must be one of: local")
        if self.ENVIRONMENT.lower() in {"production", "prod"}:
            if not self.ALLOWED_ORIGINS:
                raise ValueError("ALLOWED_ORIGINS must be configured in production")
            normalized_origins = {origin.strip().lower() for origin in self.ALLOWED_ORIGINS}
            if "*" in normalized_origins:
                raise ValueError("Wildcard CORS origins are not allowed in production")
            if any(
                "localhost" in origin or "127.0.0.1" in origin
                for origin in normalized_origins
            ):
                raise ValueError("Localhost CORS origins are not allowed in production")
        if self.AI_MODE not in {"disabled", "suggestion_only"}:
            raise ValueError("AI_MODE must be one of: disabled, suggestion_only")
        if not self.AI_ENABLED and self.AI_MODE != "disabled":
            raise ValueError("AI_MODE must be disabled when AI_ENABLED is false")
        if self.AI_ENABLED and self.AI_MODE != "suggestion_only":
            raise ValueError("AI_MODE must be suggestion_only when AI_ENABLED is true")
        if self.AI_ENABLED and not self.AI_REQUIRE_HUMAN_REVIEW:
            raise ValueError("AI_REQUIRE_HUMAN_REVIEW must stay enabled when AI is enabled")
        if self.AI_ENABLED and not self.AI_REQUIRE_BACKEND_VALIDATION:
            raise ValueError(
                "AI_REQUIRE_BACKEND_VALIDATION must stay enabled when AI is enabled"
            )
        if self.AUTH_COOKIE_SAMESITE not in {"lax", "strict", "none"}:
            raise ValueError("AUTH_COOKIE_SAMESITE must be one of: lax, strict, none")
        return self

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
