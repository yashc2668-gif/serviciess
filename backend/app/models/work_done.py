"""Derived approved work-done entries."""

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class WorkDoneItem(Base):
    __tablename__ = "work_done_items"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)
    measurement_id = Column(Integer, ForeignKey("measurements.id"), nullable=False, index=True)
    measurement_item_id = Column(
        Integer,
        ForeignKey("measurement_items.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    boq_item_id = Column(Integer, ForeignKey("boq_items.id"), nullable=False, index=True)
    recorded_date = Column(Date, nullable=False)
    previous_quantity = Column(Numeric(14, 3), nullable=False, default=0)
    current_quantity = Column(Numeric(14, 3), nullable=False, default=0)
    cumulative_quantity = Column(Numeric(14, 3), nullable=False, default=0)
    rate = Column(Numeric(14, 2), nullable=False, default=0)
    amount = Column(Numeric(18, 2), nullable=False, default=0)
    remarks = Column(String(500), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    contract = relationship("Contract", back_populates="work_done_entries")
    measurement = relationship("Measurement", back_populates="work_done_entries")
    measurement_item = relationship("MeasurementItem")
    boq_item = relationship("BOQItem", back_populates="work_done_items")
