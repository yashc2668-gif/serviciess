"""Configurable deduction helpers."""

from app.models.contract import Contract
from app.schemas.ra_bill import DeductionCreate, RABillGenerateRequest


def build_generate_deduction_payloads(
    contract: Contract,
    payload: RABillGenerateRequest,
) -> list[DeductionCreate]:
    deductions: list[DeductionCreate] = []

    if payload.apply_contract_retention and float(contract.retention_percentage or 0) > 0:
        deductions.append(
            DeductionCreate(
                deduction_type="retention",
                description="Contract retention",
                reason="Auto-applied contract retention",
                percentage=float(contract.retention_percentage),
                amount=0,
                is_system_generated=True,
            )
        )

    if payload.tds_percentage is not None:
        deductions.append(
            DeductionCreate(
                deduction_type="tds",
                description="TDS",
                reason="Percentage TDS",
                percentage=payload.tds_percentage,
                amount=0,
                is_system_generated=True,
            )
        )

    deductions.extend(payload.deductions)

    for recovery in payload.secured_advance_recoveries:
        deductions.append(
            DeductionCreate(
                deduction_type="secured_advance_recovery",
                description="Secured advance recovery",
                reason=recovery.reason,
                amount=recovery.amount,
                secured_advance_id=recovery.secured_advance_id,
                is_system_generated=True,
            )
        )

    return deductions
