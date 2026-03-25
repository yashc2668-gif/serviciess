"""BOQ item model."""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class BOQItem(Base):
    __tablename__ = "boq_items"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)
    item_code = Column(String(50), nullable=True, index=True)
    description = Column(Text, nullable=False)
    unit = Column(String(30), nullable=False)
    quantity = Column(Numeric(14, 3), nullable=False, default=0)
    rate = Column(Numeric(14, 2), nullable=False, default=0)
    amount = Column(Numeric(18, 2), nullable=False, default=0)
    category = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    contract = relationship("Contract", back_populates="boq_items")
    measurement_items = relationship(
        "MeasurementItem",
        back_populates="boq_item",
        cascade="all, delete-orphan",
        order_by="MeasurementItem.id.asc()",
    )
    work_done_items = relationship(
        "WorkDoneItem",
        back_populates="boq_item",
        cascade="all, delete-orphan",
        order_by="WorkDoneItem.id.asc()",
    )
    ra_bill_items = relationship(
        "RABillItem",
        back_populates="boq_item",
        cascade="all, delete-orphan",
        order_by="RABillItem.id.asc()",
    )
