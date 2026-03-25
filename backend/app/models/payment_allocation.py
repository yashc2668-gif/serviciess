"""Payment allocation model."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class PaymentAllocation(Base):
    __tablename__ = "payment_allocations"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False, index=True)
    ra_bill_id = Column(Integer, ForeignKey("ra_bills.id"), nullable=False, index=True)
    amount = Column(Numeric(18, 2), nullable=False, default=0)
    remarks = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    payment = relationship("Payment", back_populates="allocations")
    ra_bill = relationship("RABill", back_populates="payment_allocations")
