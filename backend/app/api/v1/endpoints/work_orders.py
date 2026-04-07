"""
Work Orders API - Incoming (Client → Marco) & Outgoing (Marco → Subcontractor)

World-class API design with:
- Dual nature support (incoming/outgoing)
- Financial reconciliation
- Approval workflow
- Margin analysis
"""

from typing import Any, List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_permissions
from app.models import Contract, Company, Vendor, Project, User
from app.schemas.contract import ContractCreate, ContractUpdate, ContractOut

router = APIRouter(prefix="/work-orders", tags=["work-orders"])


@router.get("/incoming", response_model=List[ContractOut])
def list_incoming_work_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("contracts:read")),
    project_id: Optional[int] = Query(None),
    client_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    approval_status: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    List INCOMING work orders (Client → Marco)
    
    Filters:
    - project_id: Filter by project
    - client_id: Filter by client company
    - status: active, completed, terminated
    - approval_status: draft, pending, approved, rejected
    """
    query = db.query(Contract).filter(Contract.wo_type == "incoming")
    
    # Apply filters
    if project_id:
        query = query.filter(Contract.project_id == project_id)
    if client_id:
        query = query.filter(Contract.client_id == client_id)
    if status:
        query = query.filter(Contract.status == status)
    if approval_status:
        query = query.filter(Contract.approval_status == approval_status)
    
    # Data isolation - non-admin see only their company
    if current_user.role != "admin":
        query = query.join(Project).filter(Project.company_id == current_user.company_id)
    
    total = query.count()
    contracts = query.offset(skip).limit(limit).all()
    
    return contracts


@router.get("/outgoing", response_model=List[ContractOut])
def list_outgoing_work_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("contracts:read")),
    project_id: Optional[int] = Query(None),
    vendor_id: Optional[int] = Query(None),
    contractor_category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    approval_status: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    List OUTGOING work orders (Marco → Subcontractor)
    
    Filters:
    - project_id: Filter by project
    - vendor_id: Filter by subcontractor/vendor
    - contractor_category: civil, electrical, plumbing, etc.
    - status: active, completed, terminated
    - approval_status: draft, pending, approved, rejected
    """
    query = db.query(Contract).filter(Contract.wo_type == "outgoing")
    
    # Apply filters
    if project_id:
        query = query.filter(Contract.project_id == project_id)
    if vendor_id:
        query = query.filter(Contract.vendor_id == vendor_id)
    if contractor_category:
        query = query.filter(Contract.contractor_category == contractor_category)
    if status:
        query = query.filter(Contract.status == status)
    if approval_status:
        query = query.filter(Contract.approval_status == approval_status)
    
    # Data isolation
    if current_user.role != "admin":
        query = query.join(Project).filter(Project.company_id == current_user.company_id)
    
    total = query.count()
    contracts = query.offset(skip).limit(limit).all()
    
    return contracts


@router.post("/incoming", response_model=ContractOut)
def create_incoming_work_order(
    data: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("contracts:create")),
) -> Any:
    """
    Create INCOMING work order (Client → Marco)
    
    Required fields:
    - project_id
    - client_id (company)
    - wo_number
    - title
    - original_value
    """
    # Validate client exists
    client = db.query(Company).filter(Company.id == data.client_id).first()
    if not client:
        raise HTTPException(404, "Client company not found")
    
    # Check WO number uniqueness
    existing = db.query(Contract).filter(Contract.wo_number == data.wo_number).first()
    if existing:
        raise HTTPException(400, "Work order number already exists")
    
    contract = Contract(
        wo_type="incoming",
        project_id=data.project_id,
        client_id=data.client_id,
        client_name=client.name,
        wo_number=data.wo_number,
        title=data.title,
        scope_of_work=data.scope_of_work,
        original_value=data.original_value,
        revised_value=data.revised_value or data.original_value,
        retention_percentage=data.retention_percentage or Decimal("5.00"),
        advance_percentage=data.advance_percentage or Decimal("0"),
        client_payment_terms=data.client_payment_terms,
        billing_cycle=data.billing_cycle or "monthly",
        approval_status="draft",
        status="draft",
    )
    
    db.add(contract)
    db.commit()
    db.refresh(contract)
    
    return contract


@router.post("/outgoing", response_model=ContractOut)
def create_outgoing_work_order(
    data: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("contracts:create")),
) -> Any:
    """
    Create OUTGOING work order (Marco → Subcontractor)
    
    Required fields:
    - project_id
    - vendor_id (subcontractor)
    - wo_number
    - title
    - original_value
    - contractor_category (civil, electrical, etc.)
    """
    # Validate vendor exists
    vendor = db.query(Vendor).filter(Vendor.id == data.vendor_id).first()
    if not vendor:
        raise HTTPException(404, "Vendor/Subcontractor not found")
    
    # Check WO number uniqueness
    existing = db.query(Contract).filter(Contract.wo_number == data.wo_number).first()
    if existing:
        raise HTTPException(400, "Work order number already exists")
    
    # Validate contractor category
    valid_categories = ["civil", "electrical", "plumbing", "hvac", "fire_fighting", "structural", "finishing"]
    if data.contractor_category and data.contractor_category not in valid_categories:
        raise HTTPException(400, f"Invalid category. Must be one of: {', '.join(valid_categories)}")
    
    contract = Contract(
        wo_type="outgoing",
        project_id=data.project_id,
        vendor_id=data.vendor_id,
        wo_number=data.wo_number,
        title=data.title,
        scope_of_work=data.scope_of_work,
        work_scope_summary=data.work_scope_summary,
        contractor_category=data.contractor_category,
        original_value=data.original_value,
        revised_value=data.revised_value or data.original_value,
        retention_percentage=data.retention_percentage or Decimal("5.00"),
        advance_percentage=data.advance_percentage or Decimal("0"),
        security_deposit=data.security_deposit or Decimal("0"),
        billing_cycle=data.billing_cycle or "monthly",
        approval_status="draft",
        status="draft",
    )
    
    db.add(contract)
    db.commit()
    db.refresh(contract)
    
    return contract


@router.post("/{contract_id}/approve")
def approve_work_order(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("contracts:approve")),
) -> Any:
    """
    Approve a work order (both incoming and outgoing)
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(404, "Work order not found")
    
    if contract.approval_status == "approved":
        raise HTTPException(400, "Work order already approved")
    
    contract.approval_status = "approved"
    contract.approved_by = current_user.id
    contract.approved_at = func.now()
    contract.status = "active"
    
    db.commit()
    db.refresh(contract)
    
    return {"message": "Work order approved", "contract_id": contract.id}


@router.post("/{contract_id}/reject")
def reject_work_order(
    contract_id: int,
    remarks: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("contracts:approve")),
) -> Any:
    """
    Reject a work order
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(404, "Work order not found")
    
    contract.approval_status = "rejected"
    contract.approved_by = current_user.id
    contract.approved_at = func.now()
    
    db.commit()
    db.refresh(contract)
    
    return {"message": "Work order rejected", "contract_id": contract.id, "remarks": remarks}


@router.get("/project/{project_id}/margin-analysis")
def get_project_margin_analysis(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("contracts:read")),
) -> Any:
    """
    Get margin analysis for a project
    
    Shows:
    - Total incoming (Client payments)
    - Total outgoing (Subcontractor payments)
    - Gross margin
    - Margin percentage
    """
    # Incoming total
    incoming_total = db.query(func.sum(Contract.revised_value)).filter(
        Contract.project_id == project_id,
        Contract.wo_type == "incoming",
        Contract.approval_status == "approved"
    ).scalar() or Decimal("0")
    
    # Outgoing total
    outgoing_total = db.query(func.sum(Contract.revised_value)).filter(
        Contract.project_id == project_id,
        Contract.wo_type == "outgoing",
        Contract.approval_status == "approved"
    ).scalar() or Decimal("0")
    
    margin = incoming_total - outgoing_total
    margin_percent = (margin / incoming_total * 100) if incoming_total > 0 else Decimal("0")
    
    # WO details
    incoming_wos = db.query(Contract).filter(
        Contract.project_id == project_id,
        Contract.wo_type == "incoming"
    ).all()
    
    outgoing_wos = db.query(Contract).filter(
        Contract.project_id == project_id,
        Contract.wo_type == "outgoing"
    ).all()
    
    return {
        "project_id": project_id,
        "incoming_total": float(incoming_total),
        "outgoing_total": float(outgoing_total),
        "gross_margin": float(margin),
        "margin_percent": float(margin_percent),
        "health_status": "healthy" if margin_percent >= 15 else "warning" if margin_percent >= 10 else "critical",
        "incoming_wos": [{"id": w.id, "wo_number": w.wo_number, "value": float(w.revised_value)} for w in incoming_wos],
        "outgoing_wos": [{"id": w.id, "wo_number": w.wo_number, "value": float(w.revised_value), "category": w.contractor_category} for w in outgoing_wos],
    }


@router.get("/stats/dashboard")
def get_work_order_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("dashboard:read")),
) -> Any:
    """
    Get dashboard stats for work orders
    """
    # Base query with company isolation
    base_query = db.query(Contract)
    if current_user.role != "admin":
        base_query = base_query.join(Project).filter(Project.company_id == current_user.company_id)
    
    # Incoming stats
    incoming_count = base_query.filter(Contract.wo_type == "incoming").count()
    incoming_value = base_query.filter(Contract.wo_type == "incoming").with_entities(
        func.sum(Contract.revised_value)
    ).scalar() or 0
    
    # Outgoing stats
    outgoing_count = base_query.filter(Contract.wo_type == "outgoing").count()
    outgoing_value = base_query.filter(Contract.wo_type == "outgoing").with_entities(
        func.sum(Contract.revised_value)
    ).scalar() or 0
    
    # Pending approvals
    pending_approvals = base_query.filter(Contract.approval_status == "pending").count()
    
    # By category (outgoing)
    category_breakdown = db.query(
        Contract.contractor_category,
        func.count(Contract.id),
        func.sum(Contract.revised_value)
    ).filter(
        Contract.wo_type == "outgoing"
    ).group_by(Contract.contractor_category).all()
    
    return {
        "incoming": {
            "count": incoming_count,
            "total_value": float(incoming_value),
        },
        "outgoing": {
            "count": outgoing_count,
            "total_value": float(outgoing_value),
        },
        "margin": {
            "gross": float(incoming_value - outgoing_value),
            "percent": float((incoming_value - outgoing_value) / incoming_value * 100) if incoming_value > 0 else 0,
        },
        "pending_approvals": pending_approvals,
        "category_breakdown": [
            {"category": cat, "count": count, "value": float(val or 0)}
            for cat, count, val in category_breakdown if cat
        ],
    }
