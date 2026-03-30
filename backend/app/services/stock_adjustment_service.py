"""Compatibility exports for stock adjustment services."""

from app.services.material_stock_adjustment_service import (
    create_material_stock_adjustment,
)
from app.services.material_stock_adjustment_service import (
    get_material_stock_adjustment_or_404,
)
from app.services.material_stock_adjustment_service import (
    list_material_stock_adjustments,
)
from app.services.material_stock_adjustment_service import (
    update_material_stock_adjustment,
)

__all__ = [
    "create_material_stock_adjustment",
    "get_material_stock_adjustment_or_404",
    "list_material_stock_adjustments",
    "update_material_stock_adjustment",
]
