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
        "description": "Can manage projects and project-facing users.",
    },
    "engineer": {
        "label": "Engineer",
        "description": "Can read projects and update project details.",
    },
    "accountant": {
        "label": "Accountant",
        "description": "Read-only access to project records relevant for finance.",
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

ROLE_PERMISSIONS = {
    "admin": {"*"},
    "project_manager": {
        "dashboard:read",
        "projects:create",
        "projects:read",
        "projects:update",
        "vendors:create",
        "vendors:update",
        "vendors:read",
        "contracts:create",
        "contracts:update",
        "contracts:read",
        "documents:create",
        "documents:update",
        "documents:read",
        "secured_advances:create",
        "secured_advances:update",
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
        "ra_bills:partially_paid",
        "ra_bills:paid",
        "payments:read",
        "payments:create",
        "payments:approve",
        "payments:release",
        "payments:allocate",
        "audit_logs:read",
        "users:read",
    },
    "engineer": {
        "dashboard:read",
        "projects:read",
        "projects:update",
        "contracts:read",
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
    },
    "accountant": {
        "dashboard:read",
        "projects:read",
        "contracts:read",
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
        "audit_logs:read",
    },
    "contractor": {
        "dashboard:read",
        "projects:read",
        "contracts:read",
        "secured_advances:read",
        "documents:read",
        "boq:read",
        "measurements:read",
        "work_done:read",
        "ra_bills:read",
        "payments:read",
    },
    "viewer": {
        "dashboard:read",
        "projects:read",
        "contracts:read",
        "secured_advances:read",
        "documents:read",
        "boq:read",
        "measurements:read",
        "work_done:read",
        "ra_bills:read",
        "payments:read",
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


def has_permissions(role: str, permissions: Iterable[str]) -> bool:
    normalized_role = validate_role(role)
    granted = ROLE_PERMISSIONS[normalized_role]
    if "*" in granted:
        return True
    return all(permission in granted for permission in permissions)


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
