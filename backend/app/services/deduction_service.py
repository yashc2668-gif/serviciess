"""Deduction service helpers."""

from app.calculators.ra_bill_calculator import calculate_deduction_amount
from app.models.deduction import Deduction
from app.schemas.ra_bill import DeductionCreate


def build_deduction_models(
    *,
    ra_bill_id: int,
    gross_amount,
    deductions: list[DeductionCreate],
) -> list[Deduction]:
    models: list[Deduction] = []
    for deduction in deductions:
        resolved_amount = calculate_deduction_amount(gross_amount, deduction)
        models.append(
            Deduction(
                ra_bill_id=ra_bill_id,
                deduction_type=deduction.deduction_type,
                description=deduction.description,
                reason=deduction.reason,
                percentage=deduction.percentage,
                amount=resolved_amount,
                secured_advance_id=deduction.secured_advance_id,
                is_system_generated=deduction.is_system_generated,
            )
        )
    return models
