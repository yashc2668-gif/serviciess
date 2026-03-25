"""Secured advance recovery history."""

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class SecuredAdvanceRecovery(Base):
    __tablename__ = "secured_advance_recoveries"

    id = Column(Integer, primary_key=True, index=True)
    secured_advance_id = Column(
        Integer,
        ForeignKey("secured_advances.id"),
        nullable=False,
        index=True,
    )
    ra_bill_id = Column(Integer, ForeignKey("ra_bills.id"), nullable=False, index=True)
    recovery_date = Column(Date, nullable=False)
    amount = Column(Numeric(18, 2), nullable=False, default=0)
    remarks = Column(String(500), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    secured_advance = relationship("SecuredAdvance", back_populates="recoveries")
    ra_bill = relationship("RABill")
