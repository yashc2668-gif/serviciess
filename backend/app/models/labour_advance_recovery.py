"""Labour advance recovery model."""

from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class LabourAdvanceRecovery(Base):
    __tablename__ = "labour_advance_recoveries"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_labour_advance_recoveries_amount_positive"),
    )

    id = Column(Integer, primary_key=True, index=True)
    advance_id = Column(
        Integer,
        ForeignKey("labour_advances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    labour_bill_id = Column(
        Integer,
        ForeignKey("labour_bills.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    recovery_date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(18, 2), nullable=False, default=0)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    advance = relationship("LabourAdvance", back_populates="recoveries")
    labour_bill = relationship("LabourBill", backref="advance_recoveries")
