"""
Audit Logging Middleware for RBAC Operations
Tracks all permission checks, access attempts, and data modifications
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Callable
from functools import wraps
from enum import Enum

from fastapi import Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Types of audit actions"""
    PERMISSION_CHECK = "permission_check"
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    DATA_CREATE = "data_create"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"
    DATA_VIEW = "data_view"
    WORKFLOW_TRANSITION = "workflow_transition"
    BULK_OPERATION = "bulk_operation"
    EXPORT = "export"


class AuditLogger:
    """
    Enterprise Audit Logger
    
    Usage:
        audit_logger = AuditLogger(db)
        
        # Log permission check
        audit_logger.log_permission_check(
            user=current_user,
            action="view",
            resource="projects",
            granted=True
        )
        
        # Log data change
        audit_logger.log_data_change(
            user=current_user,
            action="update",
            resource="projects",
            resource_id=1,
            previous_data=old_data,
            new_data=new_data
        )
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_permission_check(
        self,
        user: Any,
        action: str,
        resource_type: str,
        granted: bool,
        resource_id: Optional[int] = None,
        permission_required: Optional[str] = None,
        request: Optional[Request] = None,
        metadata: Optional[Dict] = None
    ) -> AuditLog:
        """Log a permission check event"""
        
        audit_action = AuditAction.ACCESS_GRANTED if granted else AuditAction.ACCESS_DENIED
        
        log_entry = AuditLog(
            performed_by=getattr(user, 'id', None),
            action=audit_action.value,
            entity_type=resource_type,
            entity_id=resource_id or 0,
            before_data=json.dumps({"permission_required": permission_required}) if permission_required else None,
            after_data=json.dumps({"granted": granted, "action": action}) if metadata else None,
            remarks=f"Permission {('granted' if granted else 'denied')} for {action} on {resource_type}"
        )
        
        self.db.add(log_entry)
        self.db.commit()
        
        # Also log to application logger
        log_level = logging.INFO if granted else logging.WARNING
        logger.log(
            log_level,
            f"Permission {('granted' if granted else 'denied')}: "
            f"{getattr(user, 'email', 'unknown')} -> {action} {resource_type}"
        )
        
        return log_entry
    
    def log_data_change(
        self,
        user: Any,
        action: AuditAction,
        resource_type: str,
        resource_id: int,
        previous_data: Optional[Dict] = None,
        new_data: Optional[Dict] = None,
        request: Optional[Request] = None,
        changes_summary: Optional[str] = None
    ) -> AuditLog:
        """Log data creation, update, or deletion"""
        
        # Calculate changes summary if not provided
        if not changes_summary and previous_data and new_data:
            changes_summary = self._calculate_changes(previous_data, new_data)
        
        log_entry = AuditLog(
            performed_by=getattr(user, 'id', None),
            action=action.value,
            entity_type=resource_type,
            entity_id=resource_id,
            before_data=previous_data if previous_data else None,
            after_data=new_data if new_data else None,
            remarks=changes_summary or f"{action.value} on {resource_type} #{resource_id}"
        )
        
        self.db.add(log_entry)
        self.db.commit()
        
        logger.info(
            f"Data {action.value}: {getattr(user, 'email', 'unknown')} -> "
            f"{resource_type} #{resource_id}"
        )
        
        return log_entry
    
    def log_bulk_operation(
        self,
        user: Any,
        action: AuditAction,
        resource_type: str,
        resource_ids: list,
        request: Optional[Request] = None,
        metadata: Optional[Dict] = None
    ) -> AuditLog:
        """Log bulk operations (export, batch update, etc.)"""
        
        log_entry = AuditLog(
            performed_by=getattr(user, 'id', None),
            action=AuditAction.BULK_OPERATION.value,
            entity_type=resource_type,
            entity_id=0,
            before_data=None,
            after_data={
                "resource_ids": resource_ids,
                "bulk_action": action.value,
                **(metadata or {})
            },
            remarks=f"Bulk {action.value} on {len(resource_ids)} {resource_type}"
        )
        
        self.db.add(log_entry)
        self.db.commit()
        
        logger.info(
            f"Bulk operation: {getattr(user, 'email', 'unknown')} -> "
            f"{action.value} {len(resource_ids)} {resource_type}"
        )
        
        return log_entry
    
    def log_workflow_transition(
        self,
        user: Any,
        resource_type: str,
        resource_id: int,
        from_state: str,
        to_state: str,
        request: Optional[Request] = None,
        metadata: Optional[Dict] = None
    ) -> AuditLog:
        """Log workflow state transitions"""
        
        log_entry = AuditLog(
            performed_by=getattr(user, 'id', None),
            action=AuditAction.WORKFLOW_TRANSITION.value,
            entity_type=resource_type,
            entity_id=resource_id,
            before_data={"status": from_state},
            after_data={"status": to_state},
            remarks=f"Status changed from '{from_state}' to '{to_state}'"
        )
        
        self.db.add(log_entry)
        self.db.commit()
        
        logger.info(
            f"Workflow transition: {getattr(user, 'email', 'unknown')} -> "
            f"{resource_type} #{resource_id}: {from_state} -> {to_state}"
        )
        
        return log_entry
    
    def get_user_activity(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> list:
        """Get activity log for a specific user"""
        query = self.db.query(AuditLog).filter(AuditLog.performed_by == user_id)
        
        if start_date:
            query = query.filter(AuditLog.performed_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.performed_at <= end_date)
        
        return query.order_by(AuditLog.performed_at.desc()).limit(limit).all()
    
    def get_resource_history(
        self,
        resource_type: str,
        resource_id: int
    ) -> list:
        """Get complete history for a resource"""
        return self.db.query(AuditLog).filter(
            AuditLog.entity_type == resource_type,
            AuditLog.entity_id == resource_id
        ).order_by(AuditLog.performed_at.asc()).all()
    
    def get_permission_denials(
        self,
        start_date: Optional[datetime] = None,
        limit: int = 100
    ) -> list:
        """Get recent permission denial events"""
        query = self.db.query(AuditLog).filter(
            AuditLog.action == AuditAction.ACCESS_DENIED.value
        )
        
        if start_date:
            query = query.filter(AuditLog.performed_at >= start_date)
        
        return query.order_by(AuditLog.performed_at.desc()).limit(limit).all()
    
    def _calculate_changes(self, old: Dict, new: Dict) -> str:
        """Calculate human-readable changes summary"""
        changes = []
        for key in old.keys() | new.keys():
            old_val = old.get(key)
            new_val = new.get(key)
            if old_val != new_val:
                changes.append(f"{key}: {old_val} -> {new_val}")
        return "; ".join(changes) if changes else "No changes detected"


def audit_log(
    action: AuditAction,
    resource_type: str,
    log_data_changes: bool = True
):
    """
    Decorator to automatically log endpoint access
    
    Usage:
        @router.put("/projects/{project_id}")
        @audit_log(AuditAction.DATA_UPDATE, "projects")
        async def update_project(...)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get db session and user
            db = kwargs.get('db')
            user = kwargs.get('current_user')
            request = kwargs.get('request')
            
            if not db or not user:
                return await func(*args, **kwargs)
            
            # Get resource ID from kwargs
            resource_id = None
            for key in ['project_id', 'resource_id', 'id', 'company_id']:
                if key in kwargs:
                    resource_id = kwargs[key]
                    break
            
            # Create audit logger
            audit = AuditLogger(db)
            
            # Log the access attempt
            audit.log_permission_check(
                user=user,
                action=action.value,
                resource_type=resource_type,
                granted=True,
                resource_id=resource_id,
                request=request
            )
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Log data changes if applicable
            if log_data_changes and action in [AuditAction.DATA_CREATE, AuditAction.DATA_UPDATE]:
                # TODO: Capture previous/new state for detailed logging
                pass
            
            return result
        return wrapper
    return decorator
