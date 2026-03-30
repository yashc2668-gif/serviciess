from uuid import uuid4

from fastapi import Request
from slowapi import Limiter

from app.core.config import settings


def get_rate_limit_key(request: Request) -> str:
    hostname = request.url.hostname or ""
    if hostname == "testserver" and request.headers.get("X-RateLimit-Test") != "1":
        return f"test-{uuid4()}"

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    client = getattr(request, "client", None)
    if client and client.host:
        return client.host

    return "anonymous"


limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=[settings.AUTH_RATE_LIMIT_GLOBAL] if settings.AUTH_RATE_LIMIT_ENABLED else [],
    enabled=settings.AUTH_RATE_LIMIT_ENABLED,
)
