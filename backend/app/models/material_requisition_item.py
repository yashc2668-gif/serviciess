"""Material requisition item model."""

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class MaterialRequisitionItem(Base):
    __tablename__ = "material_requisition_items"
    __table_args__ = (
        UniqueConstraint(
            "requisition_id",
            "material_id",
            name="uq_material_requisition_items_requisition_material",
        ),
        CheckConstraint(
            "requested_qty > 0",
            name="ck_material_requisition_items_requested_qty_positive",
        ),
        CheckConstraint(
            "approved_qty >= 0",
            name="ck_material_requisition_items_approved_qty_nonnegative",
        ),
        CheckConstraint(
            "issued_qty >= 0",
            name="ck_material_requisition_items_issued_qty_nonnegative",
        ),
        CheckConstraint(
            "approved_qty <= requested_qty",
            name="ck_material_requisition_items_approved_qty_lte_requested_qty",
        ),
        CheckConstraint(
            "issued_qty <= approved_qty",
            name="ck_material_requisition_items_issued_qty_lte_approved_qty",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    requisition_id = Column(
        Integer,
        ForeignKey("material_requisitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    requested_qty = Column(Numeric(14, 3), nullable=False, default=0)
    approved_qty = Column(Numeric(14, 3), nullable=False, default=0)
    issued_qty = Column(Numeric(14, 3), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    requisition = relationship("MaterialRequisition", back_populates="items")
    material = relationship("Material", backref="material_requisition_items")
