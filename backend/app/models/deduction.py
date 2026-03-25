"""Deduction entries applied to an RA bill."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Deduction(Base):
    __tablename__ = "deductions"

    id = Column(Integer, primary_key=True, index=True)
    ra_bill_id = Column(Integer, ForeignKey("ra_bills.id"), nullable=False, index=True)
    deduction_type = Column(
        String(50),
        nullable=False,
        comment=(
            "tds | retention | penalty | previous_adjustment | manual | "
            "secured_advance_recovery"
        ),
    )
    description = Column(String(300), nullable=True)
    reason = Column(String(500), nullable=True)
    percentage = Column(Numeric(6, 3), nullable=True)
    amount = Column(Numeric(18, 2), nullable=False, default=0)
    secured_advance_id = Column(
        Integer,
        ForeignKey("secured_advances.id"),
        nullable=True,
        index=True,
    )
    is_system_generated = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ra_bill = relationship("RABill", back_populates="deductions")
    secured_advance = relationship("SecuredAdvance", back_populates="deductions")
