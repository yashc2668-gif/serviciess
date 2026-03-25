"""Permission model placeholder."""

from sqlalchemy import Column, DateTime, Integer, String, func

from app.db.base_class import Base


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(120), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
