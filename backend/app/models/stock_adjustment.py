"""Compatibility exports for stock adjustment models."""

from app.models.material_stock_adjustment import (
    MaterialStockAdjustment as StockAdjustment,
)
from app.models.material_stock_adjustment_item import (
    MaterialStockAdjustmentItem as StockAdjustmentItem,
)

__all__ = ["StockAdjustment", "StockAdjustmentItem"]
