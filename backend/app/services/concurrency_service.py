"""Concurrency helpers for optimistic locking and conflict translation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Query, Session
from sqlalchemy.orm.exc import StaleDataError


def apply_write_lock(query: Query, db: Session) -> Query:
    bind = db.get_bind()
    if bind is None or bind.dialect.name == "sqlite":
        return query
    return query.with_for_update()


def touch_rows(*instances: object) -> None:
    touched_at = datetime.now(timezone.utc)
    for instance in instances:
        if instance is None:
            continue
        if isinstance(instance, (list, tuple, set)):
            touch_rows(*instance)
            continue
        if isinstance(instance, Iterable) and not isinstance(instance, (str, bytes, dict)):
            touch_rows(*list(instance))
            continue
        if hasattr(instance, "updated_at"):
            setattr(instance, "updated_at", touched_at)


def _raise_conflict(entity_name: str, exc: Exception) -> None:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"{entity_name} was modified concurrently. Refresh and retry.",
    ) from exc


def ensure_lock_version_matches(
    instance: object,
    expected_lock_version: int | None,
    *,
    entity_name: str,
) -> None:
    if expected_lock_version is None:
        return
    current_lock_version = getattr(instance, "lock_version", None)
    if current_lock_version is None:
        return
    if int(current_lock_version) != int(expected_lock_version):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{entity_name} was modified concurrently. Refresh and retry.",
        )


def flush_with_conflict_handling(db: Session, *, entity_name: str) -> None:
    try:
        db.flush()
    except (StaleDataError, IntegrityError, OperationalError) as exc:
        db.rollback()
        _raise_conflict(entity_name, exc)


def commit_with_conflict_handling(db: Session, *, entity_name: str) -> None:
    try:
        db.commit()
    except (StaleDataError, IntegrityError, OperationalError) as exc:
        db.rollback()
        _raise_conflict(entity_name, exc)
