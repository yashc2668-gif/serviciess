"""Central model registry for the current ready schema."""

from app.models.audit_log import AuditLog  # noqa: F401
from app.models.boq import BOQItem  # noqa: F401
from app.models.company import Company  # noqa: F401
from app.models.contract import Contract  # noqa: F401
from app.models.contract_revision import ContractRevision  # noqa: F401
from app.models.deduction import Deduction  # noqa: F401
from app.models.document import Document  # noqa: F401
from app.models.document_version import DocumentVersion  # noqa: F401
from app.models.measurement import Measurement  # noqa: F401
from app.models.measurement_attachment import MeasurementAttachment  # noqa: F401
from app.models.measurement_item import MeasurementItem  # noqa: F401
from app.models.payment import Payment  # noqa: F401
from app.models.payment_allocation import PaymentAllocation  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.ra_bill import RABill  # noqa: F401
from app.models.ra_bill_item import RABillItem  # noqa: F401
from app.models.ra_bill_status_log import RABillStatusLog  # noqa: F401
from app.models.role import Role  # noqa: F401
from app.models.secured_advance import SecuredAdvance  # noqa: F401
from app.models.secured_advance_recovery import SecuredAdvanceRecovery  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.vendor import Vendor  # noqa: F401
from app.models.work_done import WorkDoneItem  # noqa: F401
