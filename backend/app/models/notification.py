"""Notification model placeholder."""

from sqlalchemy import Column, DateTime, Integer, String, func

from app.db.base_class import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
