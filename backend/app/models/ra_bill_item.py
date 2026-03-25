"""RA bill item snapshot model."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class RABillItem(Base):
    __tablename__ = "ra_bill_items"

    id = Column(Integer, primary_key=True, index=True)
    ra_bill_id = Column(Integer, ForeignKey("ra_bills.id"), nullable=False, index=True)
    work_done_item_id = Column(
        Integer,
        ForeignKey("work_done_items.id"),
        nullable=False,
        index=True,
    )
    measurement_id = Column(Integer, ForeignKey("measurements.id"), nullable=False, index=True)
    boq_item_id = Column(Integer, ForeignKey("boq_items.id"), nullable=False, index=True)
    item_code_snapshot = Column(String(50), nullable=True)
    description_snapshot = Column(Text, nullable=False)
    unit_snapshot = Column(String(30), nullable=False)
    prev_quantity = Column(Numeric(14, 3), nullable=False, default=0)
    curr_quantity = Column(Numeric(14, 3), nullable=False, default=0)
    cumulative_quantity = Column(Numeric(14, 3), nullable=False, default=0)
    rate = Column(Numeric(14, 2), nullable=False, default=0)
    amount = Column(Numeric(18, 2), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ra_bill = relationship("RABill", back_populates="items")
    boq_item = relationship("BOQItem", back_populates="ra_bill_items")
    work_done_item = relationship("WorkDoneItem")
    measurement = relationship("Measurement")
