"""Measurement model."""

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)
    measurement_no = Column(String(100), nullable=False, unique=True, index=True)
    measurement_date = Column(Date, nullable=False)
    status = Column(
        String(30),
        nullable=False,
        default="draft",
        comment="draft | submitted | approved",
    )
    remarks = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    contract = relationship("Contract", back_populates="measurements")
    items = relationship(
        "MeasurementItem",
        back_populates="measurement",
        cascade="all, delete-orphan",
        order_by="MeasurementItem.id.asc()",
    )
    attachments = relationship(
        "MeasurementAttachment",
        back_populates="measurement",
        cascade="all, delete-orphan",
    )
    work_done_entries = relationship(
        "WorkDoneItem",
        back_populates="measurement",
        cascade="all, delete-orphan",
    )
