"""RA bill workflow transition log model."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class RABillStatusLog(Base):
    __tablename__ = "ra_bill_status_logs"

    id = Column(Integer, primary_key=True, index=True)
    ra_bill_id = Column(Integer, ForeignKey("ra_bills.id"), nullable=False, index=True)
    from_status = Column(String(30), nullable=True)
    to_status = Column(String(30), nullable=False)
    action = Column(String(50), nullable=False)
    remarks = Column(Text, nullable=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ra_bill = relationship("RABill", back_populates="status_logs")
