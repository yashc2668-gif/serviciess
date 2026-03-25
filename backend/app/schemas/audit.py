"""Audit log schemas."""

from datetime import datetime, date
from typing import Any

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    action: str
    before_data: dict[str, Any] | None = None
    after_data: dict[str, Any] | None = None
    performed_by: int
    performed_at: datetime
    remarks: str | None = None
    request_id: str | None = None

    model_config = {"from_attributes": True}


class AuditLogFilterParams(BaseModel):
    entity_type: str | None = None
    entity_id: int | None = None
    action: str | None = None
    performed_by: int | None = None
    date_from: date | None = None
    date_to: date | None = None
