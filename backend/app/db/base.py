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
from app.models.idempotency_key import IdempotencyKey
from app.models.inventory_transaction import InventoryTransaction
from app.models.labour import Labour
from app.models.labour_advance import LabourAdvance
from app.models.labour_advance_recovery import LabourAdvanceRecovery
from app.models.labour_attendance import LabourAttendance
from app.models.labour_attendance_item import LabourAttendanceItem
from app.models.labour_bill import LabourBill
from app.models.labour_bill_item import LabourBillItem
from app.models.labour_contractor import LabourContractor
from app.models.labour_productivity import LabourProductivity
from app.models.material import Material
from app.models.material_issue import MaterialIssue
from app.models.material_issue_item import MaterialIssueItem
from app.models.material_requisition import MaterialRequisition
from app.models.material_requisition_item import MaterialRequisitionItem
from app.models.material_receipt import MaterialReceipt
from app.models.material_receipt_item import MaterialReceiptItem
from app.models.material_stock_adjustment import MaterialStockAdjustment
from app.models.material_stock_adjustment_item import MaterialStockAdjustmentItem
from app.models.measurement import Measurement
from app.models.measurement_attachment import MeasurementAttachment
from app.models.measurement_item import MeasurementItem
from app.models.project import Project
from app.models.payment import Payment
from app.models.payment_allocation import PaymentAllocation
from app.models.password_reset_otp import PasswordResetOTP
from app.models.ra_bill import RABill
from app.models.ra_bill_item import RABillItem
from app.models.ra_bill_status_log import RABillStatusLog
from app.models.refresh_token_session import RefreshTokenSession
from app.models.role import Role
from app.models.secured_advance import SecuredAdvance
from app.models.secured_advance_recovery import SecuredAdvanceRecovery
from app.models.site_expense import SiteExpense
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
    "IdempotencyKey",
    "InventoryTransaction",
    "LabourContractor",
    "Labour",
    "LabourAttendance",
    "LabourAttendanceItem",
    "LabourProductivity",
    "LabourBill",
    "LabourBillItem",
    "LabourAdvance",
    "LabourAdvanceRecovery",
    "Material",
    "MaterialStockAdjustment",
    "MaterialStockAdjustmentItem",
    "MaterialIssue",
    "MaterialIssueItem",
    "MaterialRequisition",
    "MaterialRequisitionItem",
    "MaterialReceipt",
    "MaterialReceiptItem",
    "BOQItem",
    "Payment",
    "PaymentAllocation",
    "PasswordResetOTP",
    "RABill",
    "RABillItem",
    "RABillStatusLog",
    "RefreshTokenSession",
    "Deduction",
    "Measurement",
    "MeasurementItem",
    "MeasurementAttachment",
    "WorkDoneItem",
    "SecuredAdvance",
    "SecuredAdvanceRecovery",
    "SiteExpense",
]
