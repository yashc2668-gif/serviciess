"""Approval log model placeholder."""

from sqlalchemy import Column, DateTime, Integer, String, func

from app.db.base_class import Base


class ApprovalLog(Base):
    __tablename__ = "approval_logs"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, nullable=False)
    action = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
