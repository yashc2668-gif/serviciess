"""Reusable audit logging helpers."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy.orm import Session

from app.core.logging import get_request_id
from app.models.audit_log import AuditLog
from app.models.user import User
from app.utils.pagination import PaginationParams, paginate_query


def _json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return value


def serialize_model(instance: Any, *, exclude: set[str] | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for column in sa_inspect(instance.__class__).columns:
        if exclude and column.key in exclude:
            continue
        data[column.key] = _json_safe(getattr(instance, column.key))
    return data


def serialize_models(instances: list[Any]) -> list[dict[str, Any]]:
    return [serialize_model(instance) for instance in instances]


def log_audit_event(
    db: Session,
    *,
    entity_id: int,
    action: str,
    entity_type: str | None = None,
    entity_name: str | None = None,
    performed_by: User | int | None = None,
    actor_user: User | int | None = None,
    before_data: dict[str, Any] | None = None,
    after_data: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    remarks: str | None = None,
    request_id: str | None = None,
    **_: Any,
) -> AuditLog:
    user_ref = performed_by if performed_by is not None else actor_user
    if isinstance(user_ref, User):
        performed_by_id = user_ref.id
    else:
        performed_by_id = user_ref
    if performed_by_id is None:
        raise ValueError("performed_by or actor_user is required to record audit events")

    event = AuditLog(
        entity_type=entity_type or entity_name or "unknown",
        entity_id=entity_id,
        action=action,
        before_data=_json_safe(before_data),
        after_data=_json_safe(after_data if after_data is not None else payload),
        performed_by=performed_by_id,
        remarks=remarks,
        request_id=request_id or get_request_id(),
    )
    db.add(event)
    return event


def get_audit_log_or_404(db: Session, audit_log_id: int) -> AuditLog:
    audit_log = db.query(AuditLog).filter(AuditLog.id == audit_log_id).first()
    if not audit_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found",
        )
    return audit_log


def _build_audit_log_query(
    db: Session,
    *,
    entity_type: str | None = None,
    entity_id: int | None = None,
    action: str | None = None,
    performed_by: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Any:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from cannot be after date_to",
        )

    query = db.query(AuditLog)
    if entity_type is not None:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(AuditLog.entity_id == entity_id)
    if action is not None:
        query = query.filter(AuditLog.action == action)
    if performed_by is not None:
        query = query.filter(AuditLog.performed_by == performed_by)
    if date_from is not None:
        query = query.filter(
            AuditLog.performed_at >= datetime.combine(date_from, time.min)
        )
    if date_to is not None:
        query = query.filter(
            AuditLog.performed_at < datetime.combine(date_to + timedelta(days=1), time.min)
        )
    return query.order_by(AuditLog.performed_at.desc(), AuditLog.id.desc())


def list_audit_logs(
    db: Session,
    *,
    entity_type: str | None = None,
    entity_id: int | None = None,
    action: str | None = None,
    performed_by: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    pagination: PaginationParams,
) -> dict[str, object]:
    return paginate_query(
        _build_audit_log_query(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            performed_by=performed_by,
            date_from=date_from,
            date_to=date_to,
        ),
        pagination=pagination,
    )


def list_audit_logs_for_export(
    db: Session,
    *,
    entity_type: str | None = None,
    entity_id: int | None = None,
    action: str | None = None,
    performed_by: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[AuditLog]:
    return _build_audit_log_query(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        performed_by=performed_by,
        date_from=date_from,
        date_to=date_to,
    ).all()
