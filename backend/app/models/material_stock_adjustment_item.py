"""Material stock adjustment item model."""

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class MaterialStockAdjustmentItem(Base):
    __tablename__ = "material_stock_adjustment_items"
    __table_args__ = (
        UniqueConstraint(
            "adjustment_id",
            "material_id",
            name="uq_material_stock_adjustment_items_adjustment_material",
        ),
        CheckConstraint(
            "qty_change <> 0",
            name="ck_material_stock_adjustment_items_qty_change_nonzero",
        ),
        CheckConstraint(
            "unit_rate >= 0",
            name="ck_material_stock_adjustment_items_unit_rate_nonnegative",
        ),
        CheckConstraint(
            "line_amount >= 0",
            name="ck_material_stock_adjustment_items_line_amount_nonnegative",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    adjustment_id = Column(
        Integer,
        ForeignKey("material_stock_adjustments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    qty_change = Column(Numeric(14, 3), nullable=False, default=0)
    unit_rate = Column(Numeric(14, 2), nullable=False, default=0)
    line_amount = Column(Numeric(18, 2), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    adjustment = relationship("MaterialStockAdjustment", back_populates="items")
    material = relationship("Material", backref="material_stock_adjustment_items")
