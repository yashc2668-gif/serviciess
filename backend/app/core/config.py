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
    POSTGRES_DB: str = "m2n_db"
    POSTGRES_USER: str = "m2n_app"
    POSTGRES_PASSWORD: str = "m2n_app_123"

    # JWT
    SECRET_KEY: str = "CHANGE-ME"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # App
    PROJECT_NAME: str = "M2N Construction ERP"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
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
    def parse_allowed_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed.startswith("["):
                return trimmed
            return [item.strip() for item in trimmed.split(",") if item.strip()]
        return value

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

    @field_validator("ENVIRONMENT", "LOG_LEVEL", mode="before")
    @classmethod
    def normalize_simple_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
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
            dotenv_settings,
            env_settings,
            file_secret_settings,
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
