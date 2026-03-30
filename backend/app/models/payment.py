"""Payment lifecycle and release tracking."""

from decimal import Decimal

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)
    ra_bill_id = Column(Integer, ForeignKey("ra_bills.id"), nullable=True, index=True)
    payment_date = Column(Date, nullable=False)
    amount = Column(Numeric(18, 2), nullable=False, default=0)
    status = Column(
        String(30),
        nullable=False,
        default="draft",
        comment="draft | approved | released | cancelled",
    )
    payment_mode = Column(
        String(30),
        nullable=True,
        comment="neft | rtgs | cheque | upi | cash",
    )
    reference_no = Column(String(100), nullable=True)
    remarks = Column(String(500), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    released_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    is_archived = Column(Boolean, nullable=False, default=False, index=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    archived_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    archive_batch_id = Column(String(64), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    lock_version = Column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": lock_version}

    contract = relationship("Contract", back_populates="payments")
    ra_bill = relationship("RABill")
    allocations = relationship(
        "PaymentAllocation",
        back_populates="payment",
        cascade="all, delete-orphan",
        order_by="PaymentAllocation.id.asc()",
    )

    @property
    def allocated_amount(self) -> Decimal:
        return sum(
            (Decimal(str(allocation.amount or 0)) for allocation in self.allocations or []),
            Decimal("0"),
        )

    @property
    def available_amount(self) -> Decimal:
        return Decimal(str(self.amount or 0)) - self.allocated_amount
