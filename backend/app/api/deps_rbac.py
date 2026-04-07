"""
FastAPI Dependencies for RBAC Integration
Provides dependency injectors for permission checking and data filtering
"""

from typing import Optional, Type, List, Callable
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.rbac_middleware import (
    RBACMiddleware,
    PermissionContext,
    PermissionAction,
    WorkflowState,
    AccessLevel,
    require_permission,
    PermissionChecker,
    get_rbac,
)
from app.core.audit_middleware import AuditLogger, AuditAction, audit_log
from app.core.data_filters import DataFilterEngine, FieldMaskEngine, get_filtered_query
from app.models.user import User


# =============================================================================
# Permission Dependencies
# =============================================================================

def require_action(
    resource_type: str,
    action: PermissionAction,
    check_ownership: bool = False,
    check_state: bool = False
):
    """
    Dependency factory for permission checking
    
    Usage:
        @router.put("/projects/{project_id}")
        async def update_project(
            project_id: int,
            current_user: User = Depends(require_action("projects", PermissionAction.UPDATE, check_ownership=True))
        ):
            pass
    """
    def permission_checker(
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
    ) -> User:
        rbac = RBACMiddleware(db)
        
        # Build context
        context = PermissionContext(
            user=user,
            action=action,
            resource_type=resource_type,
        )
        
        # Check permission
        rbac.check_permission(context)
        
        return user
    
    return permission_checker


def require_view(resource_type: str):
    """Shortcut for view permission"""
    return require_action(resource_type, PermissionAction.VIEW)


def require_create(resource_type: str):
    """Shortcut for create permission"""
    return require_action(resource_type, PermissionAction.CREATE)


def require_update(resource_type: str, check_ownership: bool = True):
    """Shortcut for update permission with ownership check"""
    return require_action(resource_type, PermissionAction.UPDATE, check_ownership=check_ownership)


def require_delete(resource_type: str, check_ownership: bool = True):
    """Shortcut for delete permission with ownership check"""
    return require_action(resource_type, PermissionAction.DELETE, check_ownership=check_ownership)


def require_approve(resource_type: str):
    """Shortcut for approve permission with self-approval prevention"""
    return require_action(resource_type, PermissionAction.APPROVE, check_ownership=True)


# =============================================================================
# Data Filter Dependencies
# =============================================================================

def get_data_filter(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DataFilterEngine:
    """
    Get data filter engine for the current user
    
    Usage:
        @router.get("/projects")
        async def list_projects(
            db: Session = Depends(get_db),
            filter_engine: DataFilterEngine = Depends(get_data_filter)
        ):
            query = db.query(Project)
            filtered = filter_engine.filter_projects(query)
            return filtered.all()
    """
    return DataFilterEngine(db, user)


def get_field_masker(
    user: User = Depends(get_current_user),
) -> FieldMaskEngine:
    """
    Get field mask engine for the current user
    
    Usage:
        @router.get("/companies/{id}")
        async def get_company(
            id: int,
            db: Session = Depends(get_db),
            masker: FieldMaskEngine = Depends(get_field_masker)
        ):
            company = db.query(Company).get(id)
            data = company.to_dict()
            return masker.mask_fields(data, "company")
    """
    return FieldMaskEngine(user.role)


# =============================================================================
# Audit Dependencies
# =============================================================================

def get_audit_logger(
    db: Session = Depends(get_db),
) -> AuditLogger:
    """Get audit logger instance"""
    return AuditLogger(db)


def audit_permission_check(
    action: str,
    resource_type: str,
    resource_id: Optional[int] = None,
):
    """
    Decorator-style dependency for auditing permission checks
    
    Usage:
        @router.get("/projects/{id}")
        async def get_project(
            id: int,
            db: Session = Depends(get_db),
            user: User = Depends(get_current_user),
            _audit: None = Depends(audit_permission_check("view", "projects"))
        ):
            pass
    """
    def audit_dependency(
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
        request: Request = None,
    ) -> None:
        audit = AuditLogger(db)
        audit.log_permission_check(
            user=user,
            action=action,
            resource_type=resource_type,
            granted=True,
            resource_id=resource_id,
            request=request,
        )
        return None
    
    return audit_dependency


# =============================================================================
# Combined Dependencies
# =============================================================================

class RBACContext:
    """
    Combined RBAC context with all utilities
    
    Usage:
        @router.get("/projects")
        async def list_projects(
            rbac: RBACContext = Depends(get_rbac_context)
        ):
            # Access all RBAC utilities
            query = rbac.get_filtered_query(Project)
            return query.all()
    """
    
    def __init__(
        self,
        db: Session,
        user: User,
        rbac: RBACMiddleware,
        data_filter: DataFilterEngine,
        field_mask: FieldMaskEngine,
        audit: AuditLogger,
    ):
        self.db = db
        self.user = user
        self.rbac = rbac
        self.data_filter = data_filter
        self.field_mask = field_mask
        self.audit = audit
    
    def check_permission(
        self,
        action: PermissionAction,
        resource_type: str,
        resource_id: Optional[int] = None,
        **kwargs
    ) -> bool:
        """Check permission with current user"""
        context = PermissionContext(
            user=self.user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            **kwargs
        )
        return self.rbac.check_permission(context)
    
    def get_filtered_query(self, model_class: Type):
        """Get filtered query for model"""
        base_query = self.db.query(model_class)
        return self.data_filter.apply_filter(model_class, base_query)
    
    def mask_fields(self, data: dict, resource_type: str) -> dict:
        """Mask sensitive fields"""
        return self.field_mask.mask_fields(data, resource_type)
    
    def log_access(self, action: str, resource_type: str, resource_id: Optional[int] = None):
        """Log access to audit trail"""
        self.audit.log_permission_check(
            user=self.user,
            action=action,
            resource_type=resource_type,
            granted=True,
            resource_id=resource_id,
        )


def get_rbac_context(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RBACContext:
    """
    Get complete RBAC context with all utilities
    
    This is the recommended way to access RBAC functionality.
    """
    rbac = RBACMiddleware(db)
    data_filter = DataFilterEngine(db, user)
    field_mask = FieldMaskEngine(user.role)
    audit = AuditLogger(db)
    
    return RBACContext(
        db=db,
        user=user,
        rbac=rbac,
        data_filter=data_filter,
        field_mask=field_mask,
        audit=audit,
    )


# =============================================================================
# Middleware for Automatic Filtering
# =============================================================================

class RBACMiddlewareInjector:
    """
    Middleware to automatically apply RBAC to all requests
    
    Usage in FastAPI app:
        app = FastAPI()
        rbac_middleware = RBACMiddlewareInjector()
        app.middleware("http")(rbac_middleware)
    """
    
    async def __call__(self, request: Request, call_next):
        # Add RBAC info to request state
        request.state.rbac_enabled = True
        
        response = await call_next(request)
        
        # Add RBAC headers to response
        response.headers["X-RBAC-Enabled"] = "true"
        
        return response


# =============================================================================
# Permission Helper Functions
# =============================================================================

def has_permission(
    user: User,
    action: PermissionAction,
    resource_type: str,
    db: Session = Depends(get_db),
) -> bool:
    """Check if user has permission without raising exception"""
    try:
        rbac = RBACMiddleware(db)
        context = PermissionContext(
            user=user,
            action=action,
            resource_type=resource_type,
        )
        rbac.check_permission(context)
        return True
    except HTTPException:
        return False


def filter_response_data(
    user: User,
    data: dict,
    resource_type: str,
) -> dict:
    """Filter response data based on user role"""
    masker = FieldMaskEngine(user.role)
    return masker.mask_fields(data, resource_type)


def filter_response_list(
    user: User,
    items: List[dict],
    resource_type: str,
) -> List[dict]:
    """Filter list response data based on user role"""
    masker = FieldMaskEngine(user.role)
    return masker.mask_fields_in_list(items, resource_type)
