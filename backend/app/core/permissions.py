"""Role and permission helpers."""

from collections.abc import Iterable

from fastapi import Depends, HTTPException, status

from app.models.user import User

ROLE_DEFINITIONS = {
    "admin": {
        "label": "Admin",
        "description": "Full system access.",
    },
    "project_manager": {
        "label": "Project Manager",
        "description": "Can manage project delivery and RA bill review, without finance settlement control.",
    },
    "engineer": {
        "label": "Engineer",
        "description": "Can read projects and update project details.",
    },
    "accountant": {
        "label": "Accountant",
        "description": "Owns finance settlement, payment, and secured advance control.",
    },
    "contractor": {
        "label": "Contractor",
        "description": "Read-only access to assigned project data.",
    },
    "viewer": {
        "label": "Viewer",
        "description": "General read-only access.",
    },
}

ROLE_ALIASES = {
    "admin": "admin",
    "project manager": "project_manager",
    "project_manager": "project_manager",
    "engineer": "engineer",
    "accountant": "accountant",
    "contractor": "contractor",
    "viewer": "viewer",
}

# Frontend-friendly permission names mapped to existing backend permissions.
# These groups are bi-directional aliases, so either name works in RBAC checks.
PERMISSION_EQUIVALENCE_GROUPS = (
    {"requisitions:create", "material_requisitions:create"},
    {"requisitions:approve", "material_requisitions:update"},
    {"receipts:create", "material_receipts:create"},
    {"stock:issue", "material_issues:create", "material_issues:update"},
    {
        "stock:adjust",
        "material_stock_adjustments:create",
        "material_stock_adjustments:update",
    },
    {"labour:read", "labours:read"},
    {"labour:create", "labours:create"},
    {"labour:update", "labours:update"},
    {"attendance:create", "labour_attendance:create"},
    {"attendance:approve", "labour_attendance:update"},
    {"labour_bills:approve", "labour_bills:update"},
)

PERMISSION_EQUIVALENTS: dict[str, set[str]] = {}
for group in PERMISSION_EQUIVALENCE_GROUPS:
    normalized_group = {permission.strip().lower() for permission in group}
    for permission in normalized_group:
        PERMISSION_EQUIVALENTS[permission] = normalized_group

ROLE_PERMISSIONS = {
    "admin": {"*"},
    "project_manager": {
        "dashboard:read",
        "companies:read",
        "projects:create",
        "projects:read",
        "projects:update",
        "vendors:create",
        "vendors:update",
        "vendors:read",
        "materials:create",
        "materials:update",
        "materials:read",
        "stock_ledger:read",
        "material_stock_adjustments:create",
        "material_stock_adjustments:update",
        "material_stock_adjustments:read",
        "material_issues:create",
        "material_issues:update",
        "material_issues:read",
        "material_receipts:create",
        "material_receipts:update",
        "material_receipts:read",
        "material_requisitions:create",
        "material_requisitions:update",
        "material_requisitions:read",
        "requisitions:create",
        "requisitions:approve",
        "receipts:create",
        "stock:issue",
        "stock:adjust",
        "labour_contractors:create",
        "labour_contractors:update",
        "labour_contractors:read",
        "labours:create",
        "labours:update",
        "labours:read",
        "labour:create",
        "labour:update",
        "labour:read",
        "labour_attendance:create",
        "labour_attendance:update",
        "labour_attendance:read",
        "attendance:create",
        "attendance:approve",
        "labour_productivity:create",
        "labour_productivity:update",
        "labour_productivity:read",
        "labour_bills:create",
        "labour_bills:update",
        "labour_bills:read",
        "labour_bills:approve",
        "labour_advances:create",
        "labour_advances:update",
        "labour_advances:read",
        "contracts:create",
        "contracts:update",
        "contracts:read",
        "documents:create",
        "documents:update",
        "documents:read",
        "secured_advances:read",
        "boq:create",
        "boq:update",
        "boq:read",
        "measurements:create",
        "measurements:read",
        "measurements:update",
        "measurements:submit",
        "measurements:approve",
        "work_done:read",
        "ra_bills:create",
        "ra_bills:read",
        "ra_bills:submit",
        "ra_bills:verify",
        "ra_bills:approve",
        "ra_bills:reject",
        "ra_bills:cancel",
        "ra_bills:finance_hold",
        "payments:read",
        "site_expenses:create",
        "site_expenses:read",
        "site_expenses:update",
        "audit_logs:read",
        "workflows:read",
    },
    "engineer": {
        "dashboard:read",
        "companies:read",
        "projects:read",
        "projects:update",
        "contracts:read",
        "vendors:read",
        "materials:create",
        "materials:update",
        "materials:read",
        "stock_ledger:read",
        "material_stock_adjustments:create",
        "material_stock_adjustments:update",
        "material_stock_adjustments:read",
        "material_issues:create",
        "material_issues:update",
        "material_issues:read",
        "material_receipts:create",
        "material_receipts:update",
        "material_receipts:read",
        "material_requisitions:create",
        "material_requisitions:update",
        "material_requisitions:read",
        "requisitions:create",
        "requisitions:approve",
        "receipts:create",
        "stock:issue",
        "stock:adjust",
        "labour_contractors:create",
        "labour_contractors:update",
        "labour_contractors:read",
        "labours:create",
        "labours:update",
        "labours:read",
        "labour:create",
        "labour:update",
        "labour:read",
        "labour_attendance:create",
        "labour_attendance:update",
        "labour_attendance:read",
        "attendance:create",
        "attendance:approve",
        "labour_productivity:create",
        "labour_productivity:update",
        "labour_productivity:read",
        "labour_bills:create",
        "labour_bills:update",
        "labour_bills:read",
        "labour_bills:approve",
        "labour_advances:create",
        "labour_advances:update",
        "labour_advances:read",
        "secured_advances:read",
        "documents:create",
        "documents:update",
        "documents:read",
        "boq:create",
        "boq:update",
        "boq:read",
        "measurements:create",
        "measurements:read",
        "measurements:update",
        "measurements:submit",
        "work_done:read",
        "ra_bills:read",
        "payments:read",
        "site_expenses:create",
        "site_expenses:read",
        "site_expenses:update",
        "workflows:read",
    },
    "accountant": {
        "dashboard:read",
        "companies:read",
        "projects:read",
        "contracts:read",
        "vendors:read",
        "materials:read",
        "stock_ledger:read",
        "material_stock_adjustments:read",
        "material_issues:read",
        "material_receipts:read",
        "material_requisitions:read",
        "labour_contractors:read",
        "labours:read",
        "labour:read",
        "labour_attendance:read",
        "labour_productivity:read",
        "labour_bills:create",
        "labour_bills:update",
        "labour_bills:read",
        "labour_bills:approve",
        "labour_advances:create",
        "labour_advances:update",
        "labour_advances:read",
        "secured_advances:create",
        "secured_advances:update",
        "secured_advances:read",
        "documents:create",
        "documents:update",
        "documents:read",
        "boq:read",
        "measurements:read",
        "work_done:read",
        "ra_bills:create",
        "ra_bills:read",
        "ra_bills:submit",
        "ra_bills:verify",
        "ra_bills:approve",
        "ra_bills:reject",
        "ra_bills:cancel",
        "ra_bills:finance_hold",
        "ra_bills:partially_paid",
        "ra_bills:paid",
        "payments:read",
        "payments:create",
        "payments:approve",
        "payments:release",
        "payments:allocate",
        "site_expenses:create",
        "site_expenses:read",
        "site_expenses:update",
        "site_expenses:approve",
        "site_expenses:pay",
        "audit_logs:read",
        "workflows:read",
    },
    "contractor": {
        "dashboard:read",
        "companies:read",
        "projects:read",
        "contracts:read",
        "vendors:read",
        "materials:read",
        "stock_ledger:read",
        "material_stock_adjustments:read",
        "material_issues:read",
        "material_receipts:read",
        "material_requisitions:read",
        "labour_contractors:read",
        "labours:read",
        "labour:read",
        "labour_attendance:read",
        "labour_productivity:read",
        "labour_bills:read",
        "labour_advances:read",
        "secured_advances:read",
        "documents:read",
        "boq:read",
        "measurements:read",
        "work_done:read",
        "ra_bills:read",
        "payments:read",
        "site_expenses:read",
    },
    "viewer": {
        "dashboard:read",
        "companies:read",
        "projects:read",
        "contracts:read",
        "vendors:read",
        "materials:read",
        "stock_ledger:read",
        "material_stock_adjustments:read",
        "material_issues:read",
        "material_receipts:read",
        "material_requisitions:read",
        "labour_contractors:read",
        "labours:read",
        "labour:read",
        "labour_attendance:read",
        "labour_productivity:read",
        "labour_bills:read",
        "labour_advances:read",
        "secured_advances:read",
        "documents:read",
        "boq:read",
        "measurements:read",
        "work_done:read",
        "ra_bills:read",
        "payments:read",
        "site_expenses:read",
    },
}


def normalize_role(role: str) -> str:
    normalized = role.strip().lower().replace("-", "_")
    normalized = " ".join(normalized.split()).replace(" ", "_")
    return ROLE_ALIASES.get(normalized, normalized)


def validate_role(role: str) -> str:
    normalized = normalize_role(role)
    if normalized not in ROLE_DEFINITIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported role: {role}",
        )
    return normalized


def normalize_permission(permission: str) -> str:
    return permission.strip().lower()


def _permission_equivalents(permission: str) -> set[str]:
    normalized = normalize_permission(permission)
    return PERMISSION_EQUIVALENTS.get(normalized, {normalized})


def has_permissions(role: str, permissions: Iterable[str]) -> bool:
    normalized_role = validate_role(role)
    granted = {normalize_permission(permission) for permission in ROLE_PERMISSIONS[normalized_role]}
    if "*" in granted:
        return True
    for permission in permissions:
        aliases = _permission_equivalents(permission)
        if not any(alias in granted for alias in aliases):
            return False
    return True


def require_roles(*roles: str):
    allowed_roles = {validate_role(role) for role in roles}
    from app.services.auth_service import get_current_user

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        current_role = validate_role(current_user.role)
        if current_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this resource",
            )
        return current_user

    return dependency


def require_permissions(*permissions: str):
    from app.services.auth_service import get_current_user

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not has_permissions(current_user.role, permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return dependency
