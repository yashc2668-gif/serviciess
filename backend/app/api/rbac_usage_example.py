"""
RBAC Usage Examples

This file demonstrates how to use the new RBAC middleware system
in your FastAPI endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.deps import get_db, get_current_user
from app.api.deps_rbac import (
    get_rbac_context,
    require_view,
    require_create,
    require_update,
    require_delete,
    require_approve,
    get_data_filter,
    get_field_masker,
    RBACContext,
)
from app.core.rbac_middleware import (
    PermissionAction,
    WorkflowState,
    PermissionContext,
)
from app.core.data_filters import DataFilterEngine, FieldMaskEngine
from app.core.audit_middleware import AuditLogger, AuditAction
from app.models.user import User
from app.models.project import Project
from app.models.material_requisition import MaterialRequisition

router = APIRouter()


# =============================================================================
# EXAMPLE 1: Basic Permission Checking
# =============================================================================

@router.get("/projects")
async def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_view("projects")),  # Simple permission check
    filter_engine: DataFilterEngine = Depends(get_data_filter),
):
    """
    List projects - automatically filtered by user permissions
    """
    # Get base query
    query = db.query(Project)
    
    # Apply RBAC filters based on user role
    filtered_query = filter_engine.filter_projects(query)
    
    return filtered_query.all()


@router.post("/projects")
async def create_project(
    project_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_create("projects")),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """
    Create project - requires create permission
    """
    # Create project
    project = Project(**project_data, created_by=current_user.id)
    db.add(project)
    db.commit()
    
    # Audit log
    audit.log_data_change(
        user=current_user,
        action=AuditAction.DATA_CREATE,
        resource_type="projects",
        resource_id=project.id,
        new_data=project_data,
    )
    
    return project


@router.put("/projects/{project_id}")
async def update_project(
    project_id: int,
    project_data: dict,
    rbac: RBACContext = Depends(get_rbac_context),  # Full RBAC context
):
    """
    Update project - with ownership check
    """
    # Get project
    project = rbac.db.query(Project).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check permission with ownership context
    rbac.check_permission(
        action=PermissionAction.UPDATE,
        resource_type="projects",
        resource_id=project_id,
        resource_owner_id=project.created_by,
        resource_company_id=project.company_id,
    )
    
    # Store old state for audit
    old_state = project.to_dict()
    
    # Update project
    for key, value in project_data.items():
        setattr(project, key, value)
    
    rbac.db.commit()
    
    # Audit log
    rbac.audit.log_data_change(
        user=rbac.user,
        action=AuditAction.DATA_UPDATE,
        resource_type="projects",
        resource_id=project_id,
        previous_data=old_state,
        new_data=project_data,
    )
    
    return project


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    rbac: RBACContext = Depends(get_rbac_context),
):
    """
    Delete project - requires delete permission
    """
    project = rbac.db.query(Project).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check permission
    rbac.check_permission(
        action=PermissionAction.DELETE,
        resource_type="projects",
        resource_id=project_id,
        resource_owner_id=project.created_by,
    )
    
    # Store for audit
    old_state = project.to_dict()
    
    # Delete
    rbac.db.delete(project)
    rbac.db.commit()
    
    # Audit log
    rbac.audit.log_data_change(
        user=rbac.user,
        action=AuditAction.DATA_DELETE,
        resource_type="projects",
        resource_id=project_id,
        previous_data=old_state,
    )
    
    return {"message": "Project deleted"}


# =============================================================================
# EXAMPLE 2: Workflow State-Based Permissions
# =============================================================================

@router.post("/requisitions/{req_id}/approve")
async def approve_requisition(
    req_id: int,
    rbac: RBACContext = Depends(get_rbac_context),
):
    """
    Approve requisition - with state checking and self-approval prevention
    """
    requisition = rbac.db.query(MaterialRequisition).get(req_id)
    if not requisition:
        raise HTTPException(status_code=404, detail="Requisition not found")
    
    # Check permission with state context
    # This will:
    # 1. Check if user has approve permission
    # 2. Check if approve action is allowed in current state
    # 3. Prevent self-approval (if user created it)
    rbac.check_permission(
        action=PermissionAction.APPROVE,
        resource_type="requisitions",
        resource_id=req_id,
        resource_owner_id=requisition.requested_by,
        current_state=WorkflowState(requisition.status),
    )
    
    old_state = requisition.status
    
    # Update status
    requisition.status = "approved"
    rbac.db.commit()
    
    # Log workflow transition
    rbac.audit.log_workflow_transition(
        user=rbac.user,
        resource_type="requisitions",
        resource_id=req_id,
        from_state=old_state,
        to_state="approved",
    )
    
    return requisition


@router.post("/requisitions/{req_id}/submit")
async def submit_requisition(
    req_id: int,
    rbac: RBACContext = Depends(get_rbac_context),
):
    """
    Submit requisition for approval
    """
    requisition = rbac.db.query(MaterialRequisition).get(req_id)
    if not requisition:
        raise HTTPException(status_code=404, detail="Requisition not found")
    
    # Check if submit is allowed in current state (draft)
    rbac.check_permission(
        action=PermissionAction.SUBMIT,
        resource_type="requisitions",
        resource_id=req_id,
        resource_owner_id=requisition.requested_by,
        current_state=WorkflowState(requisition.status),
    )
    
    old_state = requisition.status
    requisition.status = "submitted"
    rbac.db.commit()
    
    rbac.audit.log_workflow_transition(
        user=rbac.user,
        resource_type="requisitions",
        resource_id=req_id,
        from_state=old_state,
        to_state="submitted",
    )
    
    return requisition


# =============================================================================
# EXAMPLE 3: Data Masking
# =============================================================================

@router.get("/companies/{company_id}")
async def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    masker: FieldMaskEngine = Depends(get_field_masker),
):
    """
    Get company - with field masking based on role
    
    Contractors will see:
    {
        "id": 1,
        "name": "Acme Corp",
        "gst_number": "***MASKED***",
        "pan_number": "***MASKED***",
        ...
    }
    """
    company = db.query(Company).get(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Convert to dict
    data = company.to_dict()
    
    # Apply field masking based on user role
    masked_data = masker.mask_fields(data, "company")
    
    return masked_data


@router.get("/companies")
async def list_companies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    filter_engine: DataFilterEngine = Depends(get_data_filter),
    masker: FieldMaskEngine = Depends(get_field_masker),
):
    """
    List companies - filtered and masked
    """
    query = db.query(Company)
    
    # Apply filters
    filtered = filter_engine.filter_companies(query)
    companies = filtered.all()
    
    # Convert to dicts
    data = [c.to_dict() for c in companies]
    
    # Mask sensitive fields
    masked_data = masker.mask_fields_in_list(data, "company")
    
    return masked_data


# =============================================================================
# EXAMPLE 4: Bulk Operations with Audit
# =============================================================================

@router.post("/projects/bulk-update")
async def bulk_update_projects(
    project_ids: List[int],
    update_data: dict,
    rbac: RBACContext = Depends(get_rbac_context),
):
    """
    Bulk update projects - with audit logging
    """
    # Check permission for bulk operation
    rbac.check_permission(
        action=PermissionAction.UPDATE,
        resource_type="projects",
    )
    
    # Get projects
    projects = rbac.db.query(Project).filter(Project.id.in_(project_ids)).all()
    
    # Check ownership for each
    for project in projects:
        rbac.check_permission(
            action=PermissionAction.UPDATE,
            resource_type="projects",
            resource_id=project.id,
            resource_owner_id=project.created_by,
        )
    
    # Update all
    for project in projects:
        for key, value in update_data.items():
            setattr(project, key, value)
    
    rbac.db.commit()
    
    # Log bulk operation
    rbac.audit.log_bulk_operation(
        user=rbac.user,
        action=AuditAction.DATA_UPDATE,
        resource_type="projects",
        resource_ids=project_ids,
    )
    
    return {"updated": len(projects)}


# =============================================================================
# EXAMPLE 5: Complex Query with Multiple Filters
# =============================================================================

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    rbac: RBACContext = Depends(get_rbac_context),
):
    """
    Dashboard stats - automatically filtered by user access
    """
    # Get filtered queries
    projects_query = rbac.get_filtered_query(Project)
    requisitions_query = rbac.get_filtered_query(MaterialRequisition)
    
    # Calculate stats
    total_projects = projects_query.count()
    active_projects = projects_query.filter(Project.status == "active").count()
    
    pending_reqs = requisitions_query.filter(
        MaterialRequisition.status == "pending"
    ).count()
    
    return {
        "total_projects": total_projects,
        "active_projects": active_projects,
        "pending_requisitions": pending_reqs,
        "user_role": rbac.user.role,
    }


# =============================================================================
# HELPER: Get audit logger dependency
# =============================================================================

from app.api.deps_rbac import get_audit_logger

# Usage in endpoints
def get_audit_logger(
    db: Session = Depends(get_db),
) -> AuditLogger:
    return AuditLogger(db)
