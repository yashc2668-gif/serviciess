"""RA bill amount calculators."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


MONEY_QUANTUM = Decimal("0.01")


def _get_value(source: Any, key: str, default: Any = 0) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def to_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def money(value: Any) -> Decimal:
    return to_decimal(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def calculate_gross_amount(items: list[Any]) -> Decimal:
    total = sum((to_decimal(_get_value(item, "amount", 0)) for item in items), Decimal("0"))
    return money(total)


def calculate_deduction_amount(gross_amount: Any, deduction: Any) -> Decimal:
    explicit_amount = to_decimal(_get_value(deduction, "amount", 0))
    percentage = _get_value(deduction, "percentage", None)
    if explicit_amount != 0:
        return money(explicit_amount)
    if percentage is not None:
        return money(to_decimal(gross_amount) * to_decimal(percentage) / Decimal("100"))
    return money(0)


def calculate_bill_totals(items: list[Any], deductions: list[Any]) -> dict[str, Decimal]:
    gross_amount = calculate_gross_amount(items)
    total_deductions = sum(
        (calculate_deduction_amount(gross_amount, deduction) for deduction in deductions),
        Decimal("0"),
    )
    total_deductions = money(total_deductions)
    net_payable = money(gross_amount - total_deductions)
    return {
        "gross_amount": gross_amount,
        "total_deductions": total_deductions,
        "net_payable": net_payable,
    }
