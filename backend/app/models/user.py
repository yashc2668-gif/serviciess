"""User model."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func

from app.db.base_class import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    role = Column(
        String(30),
        nullable=False,
        default="viewer",
        comment="admin | project_manager | site_engineer | accountant | viewer",
    )
    is_active = Column(Boolean, default=True, nullable=False)
    failed_login_attempts = Column(Integer, nullable=False, default=0, server_default="0")
    last_failed_login_at = Column(DateTime(timezone=True), nullable=True)
    locked_until = Column(DateTime(timezone=True), nullable=True, index=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
