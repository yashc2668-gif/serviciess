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
from app.schemas.inventory import InventoryItemCreate, InventoryItemUpdate, InventoryItemOut  # noqa
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
