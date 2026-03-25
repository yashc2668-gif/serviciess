"""Logging configuration helpers."""

from __future__ import annotations

import contextvars
import json
import logging
from datetime import datetime, timezone

_request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id",
    default=None,
)

_STANDARD_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = getattr(record, "request_id", None) or get_request_id()
        if request_id:
            payload["request_id"] = request_id

        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_FIELDS or key.startswith("_"):
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    root_logger = logging.getLogger()
    if getattr(root_logger, "_m2n_logging_configured", False):
        root_logger.setLevel(level.upper())
        return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level.upper())
    root_logger._m2n_logging_configured = True  # type: ignore[attr-defined]


def set_request_id(request_id: str):
    return _request_id_ctx.set(request_id)


def reset_request_id(token) -> None:
    _request_id_ctx.reset(token)


def get_request_id() -> str | None:
    return _request_id_ctx.get()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_business_event(event: str, **fields) -> None:
    get_logger("app.business").info(event, extra={"event": event, **fields})
