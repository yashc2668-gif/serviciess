"""Material receipt item model."""

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class MaterialReceiptItem(Base):
    __tablename__ = "material_receipt_items"
    __table_args__ = (
        UniqueConstraint(
            "receipt_id",
            "material_id",
            name="uq_material_receipt_items_receipt_material",
        ),
        CheckConstraint(
            "received_qty > 0",
            name="ck_material_receipt_items_received_qty_positive",
        ),
        CheckConstraint(
            "unit_rate >= 0",
            name="ck_material_receipt_items_unit_rate_nonnegative",
        ),
        CheckConstraint(
            "line_amount >= 0",
            name="ck_material_receipt_items_line_amount_nonnegative",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(
        Integer,
        ForeignKey("material_receipts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    received_qty = Column(Numeric(14, 3), nullable=False, default=0)
    unit_rate = Column(Numeric(14, 2), nullable=False, default=0)
    line_amount = Column(Numeric(18, 2), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    receipt = relationship("MaterialReceipt", back_populates="items")
    material = relationship("Material", backref="material_receipt_items")
