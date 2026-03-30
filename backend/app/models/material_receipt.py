"""Material receipt model."""

from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class MaterialReceipt(Base):
    __tablename__ = "material_receipts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'received', 'cancelled')",
            name="ck_material_receipts_status_valid",
        ),
        CheckConstraint("total_amount >= 0", name="ck_material_receipts_total_amount_nonnegative"),
    )

    id = Column(Integer, primary_key=True, index=True)
    receipt_no = Column(String(100), nullable=False, unique=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    received_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    receipt_date = Column(Date, nullable=False, index=True)
    status = Column(
        String(30),
        nullable=False,
        default="received",
        index=True,
        comment="draft | received | cancelled",
    )
    remarks = Column(Text, nullable=True)
    total_amount = Column(Numeric(18, 2), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    lock_version = Column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": lock_version}

    vendor = relationship("Vendor", backref="material_receipts")
    project = relationship("Project", backref="material_receipts")
    receiver = relationship("User", backref="material_receipts")
    items = relationship(
        "MaterialReceiptItem",
        back_populates="receipt",
        cascade="all, delete-orphan",
        order_by="MaterialReceiptItem.id.asc()",
    )
