"""Material requisition model."""

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class MaterialRequisition(Base):
    __tablename__ = "material_requisitions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'submitted', 'approved', 'partially_issued', 'issued', 'rejected', 'cancelled')",
            name="ck_material_requisitions_status_valid",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    requisition_no = Column(String(100), nullable=False, unique=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True, index=True)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(
        String(30),
        nullable=False,
        default="draft",
        index=True,
        comment="draft | submitted | approved | partially_issued | issued | rejected | cancelled",
    )
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    lock_version = Column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": lock_version}

    project = relationship("Project", backref="material_requisitions")
    contract = relationship("Contract", backref="material_requisitions")
    requester = relationship("User", backref="material_requisitions")
    items = relationship(
        "MaterialRequisitionItem",
        back_populates="requisition",
        cascade="all, delete-orphan",
        order_by="MaterialRequisitionItem.id.asc()",
    )
