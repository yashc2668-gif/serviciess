"""
Enhanced Companies API with RBAC Integration

This module demonstrates full RBAC implementation with:
- Permission checks at endpoint level
- Ownership validation
- Field-level masking
- Audit logging
- Workflow state awareness
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, and_, or_

from backend.app.api.deps import get_current_user, get_db
from backend.app.middlewares import PermissionService, FieldMaskingService, AuditLogger
from backend.app.models import Company, User, Project
from backend.app.schemas import Company as CompanySchema, CompanyCreate, CompanyUpdate
from backend.app.core.permissions import require_permissions

router = APIRouter()


@router.get("/companies", response_model=List[CompanySchema])
def list_companies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Any:
    """
    List companies with RBAC enforcement.
    
    - Admin: See all companies
    - Other roles: See only their company (data isolation)
    """
    # Initialize services
    perm_service = PermissionService(db, current_user)
    field_masker = FieldMaskingService(current_user.role)
    
    # Permission check
    result = perm_service.check_permission(
        resource_type="companies",
        action="read",
    )
    if not result.granted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=result.reason or "Permission denied"
        )
    
    # Build query with ownership filtering
    query = db.query(Company)
    
    # Apply data scope filtering
    if current_user.role != "admin":
        # Non-admin users only see their own company
        query = query.filter(Company.id == current_user.company_id)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                Company.name.ilike(f"%{search}%"),
                Company.address.ilike(f"%{search}%"),
            )
        )
    
    if is_active is not None:
        query = query.filter(Company.is_active == is_active)
    
    # Pagination
    total = query.count()
    companies = query.offset((page - 1) * page_size).limit(page_size).all()
    
    # Apply field masking for sensitive data
    masked_companies = []
    for company in companies:
        company_dict = {
            "id": company.id,
            "name": company.name,
            "address": company.address,
            "gst_number": company.gst_number,
            "pan_number": company.pan_number,
            "phone": company.phone,
            "email": company.email,
            "created_at": company.created_at,
            "updated_at": company.updated_at,
            "is_active": company.is_active,
        }
        masked = field_masker.mask_company_fields(company_dict)
        masked_companies.append(masked)
    
    return masked_companies


@router.get("/companies/{company_id}", response_model=CompanySchema)
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get company by ID with RBAC enforcement.
    """
    # Initialize services
    perm_service = PermissionService(db, current_user)
    field_masker = FieldMaskingService(current_user.role)
    
    # Permission check
    result = perm_service.check_permission(
        resource_type="companies",
        action="read",
        resource_id=company_id,
    )
    if not result.granted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=result.reason or "Permission denied"
        )
    
    # Fetch company
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Data isolation check
    if current_user.role != "admin" and company.id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this company"
        )
    
    # Apply field masking
    company_dict = {
        "id": company.id,
        "name": company.name,
        "address": company.address,
        "gst_number": company.gst_number,
        "pan_number": company.pan_number,
        "phone": company.phone,
        "email": company.email,
        "created_at": company.created_at,
        "updated_at": company.updated_at,
        "is_active": company.is_active,
    }
    
    return field_masker.mask_company_fields(company_dict)


@router.post("/companies", response_model=CompanySchema)
def create_company(
    data: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Create company with RBAC enforcement.
    
    - Only Admin and Project Manager can create companies
    """
    # Initialize services
    perm_service = PermissionService(db, current_user)
    audit_logger = AuditLogger(db, current_user)
    
    # Permission check
    result = perm_service.check_permission(
        resource_type="companies",
        action="create",
    )
    if not result.granted:
        audit_logger.log_permission_denied("companies", "create")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=result.reason or "Permission denied"
        )
    
    # Create company
    company = Company(
        name=data.name,
        address=data.address,
        gst_number=data.gst_number,
        pan_number=data.pan_number,
        phone=data.phone,
        email=data.email,
        is_active=data.is_active,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    
    # Audit log
    audit_logger.log_data_access("companies", company.id, "create")
    
    return company


@router.put("/companies/{company_id}", response_model=CompanySchema)
def update_company(
    company_id: int,
    data: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update company with RBAC enforcement.
    
    - Admin: Can update any company
    - PM: Can update companies they manage
    - Others: Cannot update
    """
    # Initialize services
    perm_service = PermissionService(db, current_user)
    audit_logger = AuditLogger(db, current_user)
    
    # Fetch company
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Permission check with ownership
    result = perm_service.check_permission(
        resource_type="companies",
        action="update",
        resource_id=company_id,
        resource_owner_id=None,  # Companies don't have a single owner
    )
    if not result.granted:
        audit_logger.log_permission_denied("companies", "update")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=result.reason or "Permission denied"
        )
    
    # Update fields
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    
    db.commit()
    db.refresh(company)
    
    # Audit log
    audit_logger.log_data_access("companies", company.id, "update")
    
    return company


@router.delete("/companies/{company_id}")
def delete_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Delete company with RBAC enforcement.
    
    - Only Admin can delete companies
    - Soft delete only
    """
    # Initialize services
    perm_service = PermissionService(db, current_user)
    audit_logger = AuditLogger(db, current_user)
    
    # Fetch company
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Permission check - only admin
    result = perm_service.check_permission(
        resource_type="companies",
        action="delete",
        resource_id=company_id,
    )
    if not result.granted:
        audit_logger.log_permission_denied("companies", "delete")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=result.reason or "Permission denied"
        )
    
    # Soft delete
    company.is_active = False
    db.commit()
    
    # Audit log
    audit_logger.log_data_access("companies", company.id, "delete")
    
    return {"message": "Company deleted successfully"}


# =============================================================================
# Alternative: Using FastAPI dependency approach for cleaner code
# =============================================================================

from fastapi import Security
from backend.app.core.permissions import require_permissions as req_perms


@router.get("/companies/v2", response_model=List[CompanySchema])
def list_companies_v2(
    db: Session = Depends(get_db),
    current_user: User = Depends(req_perms("companies:read")),
) -> Any:
    """
    List companies using dependency-based permission check.
    Cleaner code but less flexible for complex scenarios.
    """
    # Permission already checked by dependency
    field_masker = FieldMaskingService(current_user.role)
    
    query = db.query(Company)
    
    # Data isolation
    if current_user.role != "admin":
        query = query.filter(Company.id == current_user.company_id)
    
    companies = query.all()
    
    # Apply field masking
    return [
        field_masker.mask_company_fields({
            "id": c.id,
            "name": c.name,
            "address": c.address,
            "gst_number": c.gst_number,
            "pan_number": c.pan_number,
            "phone": c.phone,
            "email": c.email,
        })
        for c in companies
    ]


# =============================================================================
# Company Analytics with Permission Checks
# =============================================================================

@router.get("/companies/{company_id}/analytics")
def get_company_analytics(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get company analytics with full RBAC.
    """
    perm_service = PermissionService(db, current_user)
    
    # Check read permission
    result = perm_service.check_permission(
        resource_type="companies",
        action="read",
        resource_id=company_id,
    )
    if not result.granted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    # Data isolation
    if current_user.role != "admin" and current_user.company_id != company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Aggregate data
    total_projects = db.query(func.count(Project.id)).filter(
        Project.company_id == company_id
    ).scalar()
    
    return {
        "company_id": company_id,
        "total_projects": total_projects,
        "can_view_details": current_user.role in ["admin", "project_manager", "accountant"],
    }
