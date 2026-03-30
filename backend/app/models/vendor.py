"""Vendor model."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    code = Column(String(50), nullable=True, unique=True, index=True)
    vendor_type = Column(String(50), nullable=False, default="contractor")
    contact_person = Column(String(150), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    gst_number = Column(String(20), nullable=True)
    pan_number = Column(String(15), nullable=True)
    address = Column(Text, nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    lock_version = Column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": lock_version}

    contracts = relationship("Contract", back_populates="vendor")
