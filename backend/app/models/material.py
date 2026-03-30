"""Material master model."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Material(Base):
    __tablename__ = "materials"
    __table_args__ = (
        CheckConstraint("reorder_level >= 0", name="ck_materials_reorder_level_nonnegative"),
        CheckConstraint("default_rate >= 0", name="ck_materials_default_rate_nonnegative"),
        CheckConstraint("current_stock >= 0", name="ck_materials_current_stock_nonnegative"),
    )

    id = Column(Integer, primary_key=True, index=True)
    item_code = Column(String(50), nullable=False, unique=True, index=True)
    item_name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=True, index=True)
    unit = Column(String(30), nullable=False)
    reorder_level = Column(Numeric(14, 3), nullable=False, default=0)
    default_rate = Column(Numeric(14, 2), nullable=False, default=0)
    current_stock = Column(Numeric(14, 3), nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    lock_version = Column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": lock_version}

    company = relationship("Company", backref="materials")
    project = relationship("Project", backref="materials")
