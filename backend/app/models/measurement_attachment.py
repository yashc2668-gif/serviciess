"""Measurement attachment placeholder model."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class MeasurementAttachment(Base):
    __tablename__ = "measurement_attachments"

    id = Column(Integer, primary_key=True, index=True)
    measurement_id = Column(Integer, ForeignKey("measurements.id"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(500), nullable=True)
    content_type = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    measurement = relationship("Measurement", back_populates="attachments")
