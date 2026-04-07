"""
Core utilities for the application
"""

# RBAC exports
from app.core.rbac_middleware import (
    RBACMiddleware,
    RBACConfig,
    RBACContext,
    RBACError,
    AccessLevel,
    PermissionAction,
    WorkflowState,
    PermissionContext,
    require_permission,
    PermissionChecker,
    get_rbac,
)

from app.core.audit_middleware import (
    AuditLogger,
    AuditAction,
    AuditLog,
    audit_log,
)

from app.core.data_filters import (
    DataFilterEngine,
    FieldMaskEngine,
    QueryOptimizer,
    get_filtered_query,
    mask_sensitive_data,
)

from app.core.permissions import (
    ROLE_DEFINITIONS,
    ROLE_PERMISSIONS,
    has_permissions,
    require_roles,
    require_permissions,
    normalize_role,
    validate_role,
)

__all__ = [
    # RBAC Middleware
    "RBACMiddleware",
    "RBACConfig", 
    "RBACContext",
    "RBACError",
    "AccessLevel",
    "PermissionAction",
    "WorkflowState",
    "PermissionContext",
    "require_permission",
    "PermissionChecker",
    "get_rbac",
    
    # Audit
    "AuditLogger",
    "AuditAction",
    "AuditLog",
    "audit_log",
    
    # Data Filters
    "DataFilterEngine",
    "FieldMaskEngine",
    "QueryOptimizer",
    "get_filtered_query",
    "mask_sensitive_data",
    
    # Legacy Permissions
    "ROLE_DEFINITIONS",
    "ROLE_PERMISSIONS",
    "has_permissions",
    "require_roles",
    "require_permissions",
    "normalize_role",
    "validate_role",
]
