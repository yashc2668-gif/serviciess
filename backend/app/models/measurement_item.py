"""Measurement line-item model."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class MeasurementItem(Base):
    __tablename__ = "measurement_items"

    id = Column(Integer, primary_key=True, index=True)
    measurement_id = Column(Integer, ForeignKey("measurements.id"), nullable=False, index=True)
    boq_item_id = Column(Integer, ForeignKey("boq_items.id"), nullable=False, index=True)
    description_snapshot = Column(Text, nullable=False)
    unit_snapshot = Column(String(30), nullable=False)
    previous_quantity = Column(Numeric(14, 3), nullable=False, default=0)
    current_quantity = Column(Numeric(14, 3), nullable=False, default=0)
    cumulative_quantity = Column(Numeric(14, 3), nullable=False, default=0)
    rate = Column(Numeric(14, 2), nullable=False, default=0)
    amount = Column(Numeric(18, 2), nullable=False, default=0)
    allow_excess = Column(Boolean, nullable=False, default=False)
    warning_message = Column(String(255), nullable=True)
    remarks = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    measurement = relationship("Measurement", back_populates="items")
    boq_item = relationship("BOQItem", back_populates="measurement_items")
