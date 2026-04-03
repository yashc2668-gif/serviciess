"""Project-scoped site expense register."""

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class SiteExpense(Base):
    __tablename__ = "site_expenses"

    id = Column(Integer, primary_key=True, index=True)
    expense_no = Column(String(100), nullable=False, unique=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True, index=True)
    expense_date = Column(Date, nullable=False, index=True)
    expense_head = Column(String(100), nullable=False, index=True)
    payee_name = Column(String(255), nullable=True)
    amount = Column(Numeric(18, 2), nullable=False, default=0)
    payment_mode = Column(String(30), nullable=True)
    reference_no = Column(String(100), nullable=True)
    status = Column(
        String(30),
        nullable=False,
        default="draft",
        index=True,
        comment="draft | approved | paid",
    )
    remarks = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    paid_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    lock_version = Column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": lock_version}

    project = relationship("Project", backref="site_expenses")
    vendor = relationship("Vendor", backref="site_expenses")
