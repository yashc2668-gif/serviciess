"""Helpers for safe idempotent POST request replay."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.constants import IDEMPOTENCY_HEADER
from app.core.security import decode_access_token
from app.models.idempotency_key import IdempotencyKey


@dataclass(frozen=True)
class IdempotencyContext:
    actor_key: str
    key: str
    request_method: str
    request_path: str
    request_hash: str


def should_apply_idempotency(request: Request) -> bool:
    if request.method.upper() != "POST":
        return False
    if not request.url.path.startswith("/api/v1/"):
        return False
    if request.url.path.startswith("/api/v1/auth"):
        return False
    return IDEMPOTENCY_HEADER in request.headers


def build_idempotency_context(request: Request, body: bytes) -> IdempotencyContext:
    key = (request.headers.get(IDEMPOTENCY_HEADER) or "").strip()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{IDEMPOTENCY_HEADER} header cannot be empty",
        )

    actor_key = _resolve_actor_key(request)
    payload = {
        "actor_key": actor_key,
        "method": request.method.upper(),
        "path": request.url.path,
        "query": request.url.query,
        "content_type": request.headers.get("content-type", ""),
        "body_sha256": hashlib.sha256(body).hexdigest(),
    }
    request_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return IdempotencyContext(
        actor_key=actor_key,
        key=key,
        request_method=request.method.upper(),
        request_path=request.url.path,
        request_hash=request_hash,
    )


def get_existing_record(db: Session, context: IdempotencyContext) -> IdempotencyKey | None:
    return (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.actor_key == context.actor_key,
            IdempotencyKey.key == context.key,
            IdempotencyKey.request_method == context.request_method,
            IdempotencyKey.request_path == context.request_path,
        )
        .first()
    )


def claim_request(db: Session, context: IdempotencyContext) -> IdempotencyKey:
    record = IdempotencyKey(
        actor_key=context.actor_key,
        key=context.key,
        request_method=context.request_method,
        request_path=context.request_path,
        request_hash=context.request_hash,
        status="processing",
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A request with this Idempotency-Key already exists",
        ) from exc
    db.refresh(record)
    return record


def complete_request(
    db: Session,
    record: IdempotencyKey,
    *,
    response_status_code: int,
    response_body: Any,
) -> None:
    record.status = "completed"
    record.response_status_code = response_status_code
    record.response_body = response_body
    db.add(record)
    db.commit()


def abandon_request(db: Session, record: IdempotencyKey) -> None:
    db.delete(record)
    db.commit()


def ensure_request_matches(record: IdempotencyKey, context: IdempotencyContext) -> None:
    if record.request_hash != context.request_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key cannot be reused with a different request payload",
        )


def build_replay_response(record: IdempotencyKey) -> JSONResponse:
    return JSONResponse(
        status_code=record.response_status_code or status.HTTP_200_OK,
        content=record.response_body,
        headers={"X-Idempotency-Replayed": "true"},
    )


def _resolve_actor_key(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return "anonymous"
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return f"auth:{hashlib.sha256(auth_header.encode('utf-8')).hexdigest()}"
    payload = decode_access_token(token.strip())
    if not payload:
        return "anonymous"
    subject = payload.get("sub")
    if subject is None:
        return "anonymous"
    return f"user:{subject}"
