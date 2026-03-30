"""Shared API dependencies."""

from app.db.session import get_db
from app.services.auth_service import get_current_user


get_db_session = get_db

__all__ = ["get_db_session", "get_current_user"]


# Re-export commonly used helpers so endpoints can import from deps
from app.services.company_scope_service import resolve_company_scope, require_company_scope  # noqa: E402,F401
