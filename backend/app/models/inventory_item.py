"""Inventory item model placeholder."""

from sqlalchemy import Column, DateTime, Integer, String, func

from app.db.base_class import Base


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
