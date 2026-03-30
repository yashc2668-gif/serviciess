"""Refresh token session model."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from app.db.base_class import Base


class RefreshTokenSession(Base):
    __tablename__ = "refresh_token_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    family_id = Column(String(64), nullable=False, index=True)
    token_jti = Column(String(64), nullable=False, unique=True, index=True)
    token_hash = Column(String(64), nullable=False)
    csrf_token_hash = Column(String(64), nullable=False)
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(64), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    rotated_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True, index=True)
    reuse_detected_at = Column(DateTime(timezone=True), nullable=True)
    replaced_by_jti = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
