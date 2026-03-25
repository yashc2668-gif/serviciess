"""RA bill header model."""

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class RABill(Base):
    __tablename__ = "ra_bills"
    __table_args__ = (
        UniqueConstraint("contract_id", "bill_no", name="uq_ra_bills_contract_bill_no"),
    )

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)
    bill_no = Column(Integer, nullable=False, index=True)
    bill_date = Column(Date, nullable=False)
    period_from = Column(Date, nullable=True)
    period_to = Column(Date, nullable=True)
    gross_amount = Column(Numeric(18, 2), nullable=False, default=0)
    total_deductions = Column(Numeric(18, 2), nullable=False, default=0)
    net_payable = Column(Numeric(18, 2), nullable=False, default=0)
    status = Column(
        String(30),
        nullable=False,
        default="draft",
        comment=(
            "draft | submitted | verified | approved | rejected | cancelled | "
            "finance_hold | partially_paid | paid"
        ),
    )
    remarks = Column(String(500), nullable=True)
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    contract = relationship("Contract", back_populates="ra_bills")
    items = relationship(
        "RABillItem",
        back_populates="ra_bill",
        cascade="all, delete-orphan",
        order_by="RABillItem.id.asc()",
    )
    deductions = relationship(
        "Deduction",
        back_populates="ra_bill",
        cascade="all, delete-orphan",
        order_by="Deduction.id.asc()",
    )
    payment_allocations = relationship(
        "PaymentAllocation",
        back_populates="ra_bill",
        cascade="all, delete-orphan",
        order_by="PaymentAllocation.id.asc()",
    )
    status_logs = relationship(
        "RABillStatusLog",
        back_populates="ra_bill",
        cascade="all, delete-orphan",
        order_by="RABillStatusLog.id.asc()",
    )

    @property
    def paid_amount(self):
        return sum((allocation.amount or 0 for allocation in self.payment_allocations or []), 0)

    @property
    def outstanding_amount(self):
        return (self.net_payable or 0) - self.paid_amount
