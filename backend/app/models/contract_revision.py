"""Contract revision model."""

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class ContractRevision(Base):
    __tablename__ = "contract_revisions"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)
    revision_no = Column(String(50), nullable=False)
    revised_value = Column(Numeric(18, 2), nullable=False, default=0)
    effective_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    contract = relationship("Contract", back_populates="revisions")
