"""Finance archival helpers for fiscal-year close."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.models.ra_bill import RABill
from app.models.secured_advance import SecuredAdvance
from app.models.user import User
from app.schemas.financial_archive import FinancialArchiveRequest, FinancialArchiveResponse
from app.services.audit_service import log_audit_event


def archive_financial_records(
    db: Session,
    payload: FinancialArchiveRequest,
    current_user: User,
) -> FinancialArchiveResponse:
    archive_batch_id = f"fy-close-{uuid4().hex[:12]}"
    archived_at = datetime.now(timezone.utc)

    archived_payments = (
        db.query(Payment)
        .filter(
            Payment.is_archived.is_(False),
            Payment.payment_date <= payload.fiscal_year_end,
            Payment.status.in_(["released", "cancelled"]),
        )
        .update(
            {
                Payment.is_archived: True,
                Payment.archived_at: archived_at,
                Payment.archived_by: current_user.id,
                Payment.archive_batch_id: archive_batch_id,
            },
            synchronize_session=False,
        )
    )

    archived_ra_bills = (
        db.query(RABill)
        .filter(
            RABill.is_archived.is_(False),
            RABill.bill_date <= payload.fiscal_year_end,
            RABill.status.in_(["paid", "cancelled", "rejected"]),
        )
        .update(
            {
                RABill.is_archived: True,
                RABill.archived_at: archived_at,
                RABill.archived_by: current_user.id,
                RABill.archive_batch_id: archive_batch_id,
            },
            synchronize_session=False,
        )
    )

    archived_secured_advances = 0
    if payload.include_secured_advances:
        archived_secured_advances = (
            db.query(SecuredAdvance)
            .filter(
                SecuredAdvance.is_archived.is_(False),
                SecuredAdvance.advance_date <= payload.fiscal_year_end,
                SecuredAdvance.status.in_(["fully_recovered", "written_off"]),
            )
            .update(
                {
                    SecuredAdvance.is_archived: True,
                    SecuredAdvance.archived_at: archived_at,
                    SecuredAdvance.archived_by: current_user.id,
                    SecuredAdvance.archive_batch_id: archive_batch_id,
                },
                synchronize_session=False,
            )
        )

    log_audit_event(
        db,
        entity_type="financial_archive",
        entity_id=0,
        action="archive",
        performed_by=current_user,
        after_data={
            "archive_batch_id": archive_batch_id,
            "fiscal_year_end": payload.fiscal_year_end.isoformat(),
            "archived_at": archived_at.isoformat(),
            "archived_payments": archived_payments,
            "archived_ra_bills": archived_ra_bills,
            "archived_secured_advances": archived_secured_advances,
        },
        remarks=f"Fiscal close archive through {payload.fiscal_year_end.isoformat()}",
    )
    db.commit()

    return FinancialArchiveResponse(
        archive_batch_id=archive_batch_id,
        fiscal_year_end=payload.fiscal_year_end,
        archived_at=archived_at,
        archived_payments=archived_payments,
        archived_ra_bills=archived_ra_bills,
        archived_secured_advances=archived_secured_advances,
    )
