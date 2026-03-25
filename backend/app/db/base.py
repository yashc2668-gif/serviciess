"""Import model modules so Alembic can discover metadata."""

from app.db.base_class import Base
from app.models.audit_log import AuditLog
from app.models.boq import BOQItem
from app.models.company import Company
from app.models.contract import Contract
from app.models.contract_revision import ContractRevision
from app.models.deduction import Deduction
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.measurement import Measurement
from app.models.measurement_attachment import MeasurementAttachment
from app.models.measurement_item import MeasurementItem
from app.models.project import Project
from app.models.payment import Payment
from app.models.payment_allocation import PaymentAllocation
from app.models.ra_bill import RABill
from app.models.ra_bill_item import RABillItem
from app.models.ra_bill_status_log import RABillStatusLog
from app.models.role import Role
from app.models.secured_advance import SecuredAdvance
from app.models.secured_advance_recovery import SecuredAdvanceRecovery
from app.models.user import User
from app.models.vendor import Vendor
from app.models.work_done import WorkDoneItem

__all__ = [
    "Base",
    "AuditLog",
    "Role",
    "Company",
    "User",
    "Project",
    "Vendor",
    "Contract",
    "ContractRevision",
    "Document",
    "DocumentVersion",
    "BOQItem",
    "Payment",
    "PaymentAllocation",
    "RABill",
    "RABillItem",
    "RABillStatusLog",
    "Deduction",
    "Measurement",
    "MeasurementItem",
    "MeasurementAttachment",
    "WorkDoneItem",
    "SecuredAdvance",
    "SecuredAdvanceRecovery",
]
