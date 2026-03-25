"""Approval step model placeholder."""

from sqlalchemy import Column, DateTime, Integer, String, func

from app.db.base_class import Base


class ApprovalStep(Base):
    __tablename__ = "approval_steps"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, nullable=False)
    step_name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
