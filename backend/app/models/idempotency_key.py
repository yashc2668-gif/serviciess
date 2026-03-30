"""Idempotency key record for replay-safe write requests."""

from sqlalchemy import Column, DateTime, Integer, JSON, String, UniqueConstraint, func

from app.db.base_class import Base


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint(
            "actor_key",
            "key",
            "request_method",
            "request_path",
            name="uq_idempotency_keys_actor_key_method_path",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    actor_key = Column(String(255), nullable=False, index=True)
    key = Column(String(255), nullable=False, index=True)
    request_method = Column(String(10), nullable=False, index=True)
    request_path = Column(String(500), nullable=False, index=True)
    request_hash = Column(String(128), nullable=False)
    status = Column(String(20), nullable=False, default="processing", index=True)
    response_status_code = Column(Integer, nullable=True)
    response_body = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
