"""Shared API dependencies."""

from app.db.session import get_db
from app.services.auth_service import get_current_user


get_db_session = get_db

__all__ = ["get_db_session", "get_current_user"]
