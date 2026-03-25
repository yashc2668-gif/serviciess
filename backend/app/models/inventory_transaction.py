"""Inventory transaction model placeholder."""

from sqlalchemy import Column, DateTime, Integer, Numeric, func

from app.db.base_class import Base


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, index=True)
    inventory_item_id = Column(Integer, nullable=False)
    quantity = Column(Numeric(14, 3), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
