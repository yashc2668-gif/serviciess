"""Central audit log model."""

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, func

from app.db.base_class import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    before_data = Column(JSON, nullable=True)
    after_data = Column(JSON, nullable=True)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    performed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    remarks = Column(String(500), nullable=True)
    request_id = Column(String(100), nullable=True, index=True)
