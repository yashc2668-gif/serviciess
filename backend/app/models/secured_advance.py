"""Secured advance issue and balance tracking."""

from decimal import Decimal

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class SecuredAdvance(Base):
    __tablename__ = "secured_advances"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)
    advance_date = Column(Date, nullable=False)
    description = Column(String(500), nullable=True)
    advance_amount = Column(Numeric(18, 2), nullable=False, default=0)
    recovered_amount = Column(Numeric(18, 2), nullable=False, default=0)
    balance = Column(Numeric(18, 2), nullable=False, default=0)
    status = Column(
        String(30),
        nullable=False,
        default="active",
        comment="active | fully_recovered | written_off",
    )
    issued_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_archived = Column(Boolean, nullable=False, default=False, index=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    archived_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    archive_batch_id = Column(String(64), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    contract = relationship("Contract", back_populates="secured_advances")
    recoveries = relationship(
        "SecuredAdvanceRecovery",
        back_populates="secured_advance",
        cascade="all, delete-orphan",
        order_by="SecuredAdvanceRecovery.id.asc()",
    )
    deductions = relationship("Deduction", back_populates="secured_advance")

    @property
    def recovery_count(self) -> int:
        return len(self.recoveries or [])

    @property
    def normalized_balance(self) -> Decimal:
        return Decimal(str(self.balance or 0))
