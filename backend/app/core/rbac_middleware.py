"""
World-Class RBAC Middleware System
Enterprise-grade permission control with:
- Ownership-based access (own/team/department/all)
- State-based permissions (workflow states)
- Field-level data masking
- Context-aware permission evaluation
- Comprehensive audit logging
"""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from functools import wraps
import logging
from datetime import datetime

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.permissions import has_permissions, normalize_role, ROLE_PERMISSIONS
from app.db.session import get_db
from app.services.auth_service import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)


class AccessLevel(str, Enum):
    """Data access granularity levels"""
    OWN = "own"           # Only user's own records
    TEAM = "team"         # User's team/assigned records
    DEPARTMENT = "dept"   # Department-level records
    COMPANY = "company"   # Company-wide records
    ALL = "all"           # All records (admin)


class PermissionAction(str, Enum):
    """CRUD + workflow actions"""
    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    SUBMIT = "submit"
    VERIFY = "verify"
    REJECT = "reject"
    CANCEL = "cancel"
    PAID = "paid"


class WorkflowState(str, Enum):
    """Common workflow states"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"
    CANCELLED = "cancelled"


class PermissionContext(BaseModel):
    """Context for permission evaluation"""
    user: User
    action: PermissionAction
    resource_type: str
    resource_id: Optional[int] = None
    resource_owner_id: Optional[int] = None
    resource_company_id: Optional[int] = None
    resource_project_id: Optional[int] = None
    current_state: Optional[WorkflowState] = None
    requested_fields: Optional[List[str]] = None
    
    class Config:
        arbitrary_types_allowed = True


# Alias for backward compatibility
RBACContext = PermissionContext


class RBACConfig:
    """Configuration for RBAC middleware"""
    
    # State-based permission rules
    STATE_PERMISSIONS = {
        # Format: module: {state: [allowed_actions]}
        "requisitions": {
            WorkflowState.DRAFT: [PermissionAction.VIEW, PermissionAction.UPDATE, PermissionAction.DELETE, PermissionAction.SUBMIT],
            WorkflowState.SUBMITTED: [PermissionAction.VIEW, PermissionAction.APPROVE, PermissionAction.REJECT],
            WorkflowState.PENDING: [PermissionAction.VIEW, PermissionAction.APPROVE, PermissionAction.REJECT],
            WorkflowState.APPROVED: [PermissionAction.VIEW],
            WorkflowState.REJECTED: [PermissionAction.VIEW, PermissionAction.UPDATE, PermissionAction.DELETE],
        },
        "ra_bills": {
            WorkflowState.DRAFT: [PermissionAction.VIEW, PermissionAction.UPDATE, PermissionAction.DELETE, PermissionAction.SUBMIT],
            WorkflowState.SUBMITTED: [PermissionAction.VIEW, PermissionAction.VERIFY],
            WorkflowState.UNDER_REVIEW: [PermissionAction.VIEW, PermissionAction.APPROVE, PermissionAction.REJECT],
            WorkflowState.APPROVED: [PermissionAction.VIEW, PermissionAction.PAID],
            WorkflowState.PAID: [PermissionAction.VIEW],
        },
        "payments": {
            WorkflowState.DRAFT: [PermissionAction.VIEW, PermissionAction.UPDATE, PermissionAction.DELETE, PermissionAction.SUBMIT],
            WorkflowState.PENDING: [PermissionAction.VIEW, PermissionAction.APPROVE, PermissionAction.REJECT],
            WorkflowState.APPROVED: [PermissionAction.VIEW, PermissionAction.UPDATE],  # Release
            WorkflowState.PAID: [PermissionAction.VIEW],
        },
        "labour_bills": {
            WorkflowState.DRAFT: [PermissionAction.VIEW, PermissionAction.UPDATE, PermissionAction.DELETE, PermissionAction.SUBMIT],
            WorkflowState.PENDING: [PermissionAction.VIEW, PermissionAction.APPROVE, PermissionAction.REJECT],
            WorkflowState.APPROVED: [PermissionAction.VIEW, PermissionAction.PAID],
            WorkflowState.PAID: [PermissionAction.VIEW],
        },
    }
    
    # Field-level masking rules by role
    FIELD_MASKS = {
        "companies": {
            "contractor": ["gst_number", "pan_number", "phone", "email", "address"],  # Hide sensitive
            "viewer": ["gst_number", "pan_number", "phone", "email"],
            "engineer": [],  # Can see all
            "accountant": [],  # Can see all
            "project_manager": [],  # Can see all
        },
        "vendors": {
            "contractor": ["gst_number", "pan_number", "bank_details"],
            "viewer": ["gst_number", "pan_number", "bank_details"],
        },
        "payments": {
            "engineer": ["bank_account", "ifsc_code", "payment_notes"],  # Engineers can't see payment details
            "contractor": ["bank_account", "ifsc_code", "payment_notes"],
            "viewer": ["bank_account", "ifsc_code", "payment_notes"],
        },
    }
    
    # Ownership-based permission matrix
    # Format: role: {access_level: [actions]}
    OWNERSHIP_MATRIX = {
        "admin": {
            AccessLevel.ALL: list(PermissionAction),
        },
        "project_manager": {
            AccessLevel.ALL: [PermissionAction.VIEW, PermissionAction.CREATE, PermissionAction.APPROVE],
            AccessLevel.COMPANY: [PermissionAction.UPDATE, PermissionAction.DELETE],
        },
        "engineer": {
            AccessLevel.TEAM: [PermissionAction.VIEW, PermissionAction.CREATE, PermissionAction.UPDATE],
            AccessLevel.OWN: [PermissionAction.DELETE, PermissionAction.SUBMIT],
        },
        "accountant": {
            AccessLevel.COMPANY: [PermissionAction.VIEW, PermissionAction.CREATE, PermissionAction.UPDATE, PermissionAction.APPROVE],
        },
        "contractor": {
            AccessLevel.OWN: [PermissionAction.VIEW],
        },
        "viewer": {
            AccessLevel.ALL: [PermissionAction.VIEW],
        },
    }


class RBACError(HTTPException):
    """RBAC-specific exception with detailed error info"""
    def __init__(
        self,
        detail: str,
        permission_required: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Permission denied",
                "message": detail,
                "permission_required": permission_required,
                "resource": resource,
                "action": action,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


class RBACMiddleware:
    """
    Enterprise RBAC Middleware
    
    Usage:
        @router.post("/items")
        async def create_item(
            data: ItemCreate,
            current_user: User = Depends(get_current_user),
            rbac: RBACMiddleware = Depends()
        ):
            context = PermissionContext(
                user=current_user,
                action=PermissionAction.CREATE,
                resource_type="items"
            )
            rbac.check_permission(context)
            # ... create logic
    """
    
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.config = RBACConfig()
    
    def check_permission(self, context: PermissionContext) -> bool:
        """
        Main permission check with ownership, state, and field validation
        """
        logger.debug(
            f"Checking permission: {context.user.email} -> {context.action} {context.resource_type}"
        )
        
        # 1. Check basic role permission
        if not self._check_role_permission(context):
            raise RBACError(
                detail="Insufficient role permissions",
                permission_required=f"{context.resource_type}:{context.action}",
                resource=context.resource_type,
                action=context.action.value
            )
        
        # 2. Check ownership if resource exists
        if context.resource_id:
            if not self._check_ownership(context):
                raise RBACError(
                    detail="You don't have access to this resource",
                    resource=context.resource_type,
                    action=context.action.value
                )
        
        # 3. Check state-based permissions
        if context.current_state:
            if not self._check_state_permission(context):
                raise RBACError(
                    detail=f"Action '{context.action}' not allowed in state '{context.current_state}'",
                    resource=context.resource_type,
                    action=context.action.value
                )
        
        # 4. Check self-approval prevention
        if context.action == PermissionAction.APPROVE:
            if self._is_self_approval(context):
                raise RBACError(
                    detail="Self-approval is not allowed",
                    resource=context.resource_type,
                    action=context.action.value
                )
        
        logger.info(
            f"Permission granted: {context.user.email} -> {context.action} {context.resource_type}"
        )
        return True
    
    def _check_role_permission(self, context: PermissionContext) -> bool:
        """Check if role has basic permission"""
        permission_key = f"{context.resource_type}:{context.action.value}"
        return has_permissions(context.user.role, [permission_key])
    
    def _check_ownership(self, context: PermissionContext) -> bool:
        """Check ownership-based access"""
        role = normalize_role(context.user.role)
        matrix = self.config.OWNERSHIP_MATRIX.get(role, {})
        
        # Determine access level required
        access_level = self._determine_access_level(context)
        
        # Check if role has permission at this access level
        allowed_levels = []
        for level, actions in matrix.items():
            if context.action in actions:
                allowed_levels.append(level)
        
        # Check hierarchy: own < team < dept < company < all
        hierarchy = [AccessLevel.OWN, AccessLevel.TEAM, AccessLevel.DEPARTMENT, 
                     AccessLevel.COMPANY, AccessLevel.ALL]
        
        required_idx = hierarchy.index(access_level) if access_level in hierarchy else 0
        
        for allowed_level in allowed_levels:
            if allowed_level in hierarchy:
                allowed_idx = hierarchy.index(allowed_level)
                if allowed_idx >= required_idx:
                    return True
        
        return False
    
    def _determine_access_level(self, context: PermissionContext) -> AccessLevel:
        """Determine required access level for resource"""
        user = context.user
        
        # Check if user owns the resource
        if context.resource_owner_id and context.resource_owner_id == user.id:
            return AccessLevel.OWN
        
        # Check if user is in same project
        if context.resource_project_id:
            # TODO: Check if user is assigned to project
            # For now, assume company-level access for PMs
            if normalize_role(user.role) in ["project_manager", "admin"]:
                return AccessLevel.COMPANY
        
        # Check company match
        if context.resource_company_id:
            if context.resource_company_id == user.company_id:
                return AccessLevel.COMPANY
        
        return AccessLevel.ALL
    
    def _check_state_permission(self, context: PermissionContext) -> bool:
        """Check if action is allowed in current workflow state"""
        module_states = self.config.STATE_PERMISSIONS.get(context.resource_type, {})
        allowed_actions = module_states.get(context.current_state, [PermissionAction.VIEW])
        
        # Admin bypass state checks
        if normalize_role(context.user.role) == "admin":
            return True
        
        return context.action in allowed_actions
    
    def _is_self_approval(self, context: PermissionContext) -> bool:
        """Prevent users from approving their own records"""
        if context.action != PermissionAction.APPROVE:
            return False
        
        if context.resource_owner_id and context.resource_owner_id == context.user.id:
            return True
        
        return False
    
    def get_masked_fields(self, role: str, resource_type: str) -> List[str]:
        """Get list of fields to mask for this role/resource"""
        resource_masks = self.config.FIELD_MASKS.get(resource_type, {})
        normalized_role = normalize_role(role)
        return resource_masks.get(normalized_role, [])
    
    def filter_data_by_permission(
        self, 
        data: Dict[str, Any], 
        context: PermissionContext
    ) -> Dict[str, Any]:
        """Filter data fields based on role permissions"""
        masked_fields = self.get_masked_fields(
            context.user.role, 
            context.resource_type
        )
        
        filtered = {}
        for key, value in data.items():
            if key not in masked_fields:
                filtered[key] = value
            else:
                filtered[key] = "***MASKED***"
        
        return filtered


# Dependency injection helper
def get_rbac(db: Session = Depends(get_db)) -> RBACMiddleware:
    return RBACMiddleware(db)


# Decorator for permission checking
def require_permission(
    resource_type: str,
    action: PermissionAction,
    check_ownership: bool = False,
    check_state: bool = False
):
    """
    Decorator to enforce permissions on endpoint
    
    Usage:
        @router.put("/items/{item_id}")
        @require_permission("items", PermissionAction.UPDATE, check_ownership=True)
        async def update_item(...)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs
            current_user = kwargs.get('current_user')
            if not current_user:
                for arg in args:
                    if isinstance(arg, User):
                        current_user = arg
                        break
            
            if not current_user:
                raise RBACError(detail="Authentication required")
            
            # Create context
            context = PermissionContext(
                user=current_user,
                action=action,
                resource_type=resource_type,
                resource_id=kwargs.get('resource_id'),
                resource_owner_id=kwargs.get('owner_id'),
            )
            
            # Check permission
            rbac = RBACMiddleware()
            rbac.check_permission(context)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Context manager for permission checking
class PermissionChecker:
    """Context manager for permission checks"""
    
    def __init__(
        self,
        rbac: RBACMiddleware,
        user: User,
        action: PermissionAction,
        resource_type: str,
        resource_id: Optional[int] = None,
        **kwargs
    ):
        self.rbac = rbac
        self.context = PermissionContext(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            **kwargs
        )
    
    def __enter__(self):
        self.rbac.check_permission(self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
