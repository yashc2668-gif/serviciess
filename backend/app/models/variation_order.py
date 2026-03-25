"""Variation order model placeholder."""

from sqlalchemy import Column, DateTime, Integer, String, func

from app.db.base_class import Base


class VariationOrder(Base):
    __tablename__ = "variation_orders"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, nullable=False)
    reference_no = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
