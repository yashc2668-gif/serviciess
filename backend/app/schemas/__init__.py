"""Central schema registry."""

from app.schemas.auth import (  # noqa
    LoginRequest,
    ProtectedRouteResponse,
    RegisterRequest,
    TokenPayload,
    TokenResponse,
)
from app.schemas.user import UserCreate, UserUpdate, UserOut  # noqa
from app.schemas.vendor import VendorCreate, VendorUpdate, VendorOut  # noqa
from app.schemas.audit import AuditLogFilterParams, AuditLogOut  # noqa
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyOut  # noqa
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectOut  # noqa
from app.schemas.contract import (  # noqa
    ContractCreate,
    ContractDetailOut,
    ContractOut,
    ContractRevisionOut,
    ContractUpdate,
)
from app.schemas.boq import BOQItemCreate, BOQItemUpdate, BOQItemOut  # noqa
from app.schemas.measurement import (  # noqa
    MeasurementCreate,
    MeasurementItemCreate,
    MeasurementItemOut,
    MeasurementOut,
    MeasurementUpdate,
)
from app.schemas.work_done import WorkDoneOut  # noqa
from app.schemas.ra_bill import (  # noqa
    RABillCreate,
    RABillGenerateRequest,
    RABillOut,
    RABillSubmitRequest,
    RABillTransitionRequest,
    RABillStatusLogOut,
    DeductionCreate, DeductionOut,
)
from app.schemas.secured_advance import (  # noqa
    SecuredAdvanceIssueCreate,
    SecuredAdvanceRecoveryApply,
    SecuredAdvanceRecoveryOut,
    SecuredAdvanceUpdate,
    SecuredAdvanceOut,
)
from app.schemas.payment import (  # noqa
    PaymentActionRequest,
    PaymentAllocationCreate,
    PaymentAllocationOut,
    PaymentCreate,
    OutstandingBillOut,
    PaymentOut,
)
from app.schemas.inventory import (  # noqa
    InventoryItemCreate,
    InventoryItemOut,
    InventoryItemUpdate,
    InventoryTransactionOut,
)
from app.schemas.labour import LabourCreate, LabourOut, LabourUpdate  # noqa
from app.schemas.labour_advance import (  # noqa
    LabourAdvanceCreate,
    LabourAdvanceOut,
    LabourAdvanceRecoveryCreate,
    LabourAdvanceRecoveryOut,
    LabourAdvanceUpdate,
)
from app.schemas.labour_attendance import (  # noqa
    LabourAttendanceCreate,
    LabourAttendanceItemCreate,
    LabourAttendanceItemOut,
    LabourAttendanceItemUpdate,
    LabourAttendanceOut,
    LabourAttendanceUpdate,
)
from app.schemas.labour_bill import LabourBillCreate, LabourBillOut, LabourBillUpdate  # noqa
from app.schemas.labour_contractor import (  # noqa
    LabourContractorCreate,
    LabourContractorOut,
    LabourContractorUpdate,
)
from app.schemas.labour_productivity import (  # noqa
    LabourProductivityCreate,
    LabourProductivityOut,
    LabourProductivityUpdate,
)
from app.schemas.material import (  # noqa
    MaterialCreate,
    MaterialOut,
    MaterialStockSummaryOut,
    MaterialUpdate,
)
from app.schemas.material_issue import (  # noqa
    MaterialIssueCreate,
    MaterialIssueItemCreate,
    MaterialIssueItemOut,
    MaterialIssueItemUpdate,
    MaterialIssueOut,
    MaterialIssueUpdate,
)
from app.schemas.material_requisition import (  # noqa
    MaterialRequisitionCreate,
    MaterialRequisitionItemCreate,
    MaterialRequisitionItemOut,
    MaterialRequisitionItemUpdate,
    MaterialRequisitionOut,
    MaterialRequisitionUpdate,
)
from app.schemas.material_receipt import (  # noqa
    MaterialReceiptCreate,
    MaterialReceiptItemCreate,
    MaterialReceiptItemOut,
    MaterialReceiptItemUpdate,
    MaterialReceiptOut,
    MaterialReceiptUpdate,
)
from app.schemas.material_stock_adjustment import (  # noqa
    MaterialStockAdjustmentCreate,
    MaterialStockAdjustmentItemCreate,
    MaterialStockAdjustmentItemOut,
    MaterialStockAdjustmentItemUpdate,
    MaterialStockAdjustmentOut,
    MaterialStockAdjustmentUpdate,
)
from app.schemas.document import (  # noqa
    DocumentCreate,
    DocumentOut,
    DocumentUpdate,
    DocumentVersionCreate,
    DocumentVersionOut,
)
from app.schemas.dashboard import (  # noqa
    ContractDashboardOut,
    DashboardFinanceOut,
    DashboardSummaryOut,
    ProjectDashboardOut,
)
