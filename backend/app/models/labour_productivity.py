"""Labour productivity model."""

from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class LabourProductivity(Base):
    __tablename__ = "labour_productivities"
    __table_args__ = (
        CheckConstraint(
            "quantity_done >= 0",
            name="ck_labour_productivities_quantity_done_nonnegative",
        ),
        CheckConstraint(
            "labour_count > 0",
            name="ck_labour_productivities_labour_count_positive",
        ),
        CheckConstraint(
            "productivity_value >= 0",
            name="ck_labour_productivities_productivity_value_nonnegative",
        ),
        CheckConstraint(
            "quantity >= 0",
            name="ck_labour_productivities_quantity_nonnegative",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True, index=True)
    date = Column(Date, nullable=True, index=True)
    trade = Column(String(100), nullable=True, index=True)
    quantity_done = Column(Numeric(14, 3), nullable=False, default=0)
    labour_count = Column(Integer, nullable=False, default=0)
    productivity_value = Column(Numeric(14, 3), nullable=False, default=0)

    # Backward-compatible fields retained for existing integrations.
    labour_id = Column(Integer, ForeignKey("labours.id"), nullable=True, index=True)
    activity_name = Column(String(255), nullable=False, index=True)
    quantity = Column(Numeric(14, 3), nullable=False, default=0)
    unit = Column(String(30), nullable=False, default="unit")
    productivity_date = Column(Date, nullable=False, index=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project = relationship("Project", backref="labour_productivities")
    contract = relationship("Contract", backref="labour_productivities")
    labour = relationship("Labour", backref="productivity_entries")
