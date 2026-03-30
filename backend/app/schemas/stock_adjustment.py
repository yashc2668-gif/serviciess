"""Compatibility exports for stock adjustment schemas."""

from app.schemas.material_stock_adjustment import (
    MaterialStockAdjustmentCreate as StockAdjustmentCreate,
)
from app.schemas.material_stock_adjustment import (
    MaterialStockAdjustmentItemCreate as StockAdjustmentItemCreate,
)
from app.schemas.material_stock_adjustment import (
    MaterialStockAdjustmentItemOut as StockAdjustmentItemOut,
)
from app.schemas.material_stock_adjustment import (
    MaterialStockAdjustmentItemUpdate as StockAdjustmentItemUpdate,
)
from app.schemas.material_stock_adjustment import (
    MaterialStockAdjustmentOut as StockAdjustmentOut,
)
from app.schemas.material_stock_adjustment import (
    MaterialStockAdjustmentUpdate as StockAdjustmentUpdate,
)

__all__ = [
    "StockAdjustmentCreate",
    "StockAdjustmentItemCreate",
    "StockAdjustmentItemOut",
    "StockAdjustmentItemUpdate",
    "StockAdjustmentOut",
    "StockAdjustmentUpdate",
]
