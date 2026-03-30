"""Labour bill item model."""

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class LabourBillItem(Base):
    __tablename__ = "labour_bill_items"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_labour_bill_items_quantity_nonnegative"),
        CheckConstraint("rate >= 0", name="ck_labour_bill_items_rate_nonnegative"),
        CheckConstraint("amount >= 0", name="ck_labour_bill_items_amount_nonnegative"),
    )

    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(
        Integer,
        ForeignKey("labour_bills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attendance_id = Column(
        Integer,
        ForeignKey("labour_attendances.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    labour_id = Column(
        Integer,
        ForeignKey("labours.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    description = Column(String(255), nullable=True)
    quantity = Column(Numeric(14, 3), nullable=False, default=0)
    rate = Column(Numeric(14, 2), nullable=False, default=0)
    amount = Column(Numeric(18, 2), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    bill = relationship("LabourBill", back_populates="items")
    attendance = relationship("LabourAttendance", backref="labour_bill_items")
    labour = relationship("Labour", backref="labour_bill_items")
