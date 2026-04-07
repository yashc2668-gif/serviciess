"""
Material Requisition API Endpoints

Workflow:
1. CREATE: Engineer creates requisition (DRAFT)
2. UPDATE: Edit items while in DRAFT
3. SUBMIT: Send for approval (DRAFT → SUBMITTED)
4. APPROVE: Manager approves (SUBMITTED → APPROVED)
5. REJECT: Manager rejects (SUBMITTED → REJECTED)
6. ISSUE: Store issues materials (APPROVED → ISSUED/PARTIAL)
"""

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_permissions
from app.models import MaterialRequisition, MaterialRequisitionItem, Material, Project, User
from app.schemas.material_requisition import (
    MaterialRequisitionCreate,
    MaterialRequisitionUpdate,
    MaterialRequisitionOut,
    MaterialRequisitionListOut,
    MaterialRequisitionSubmit,
    MaterialRequisitionApprove,
    MaterialRequisitionIssue,
    MaterialRequisitionItemCreate,
)
from app.utils.pagination import PaginationParams, paginate_query, get_pagination_params

router = APIRouter(prefix="/material-requisitions", tags=["Material Requisitions"])


def _generate_req_no(db: Session) -> str:
    """Generate unique requisition number."""
    import datetime
    prefix = "MR"
    date_str = datetime.datetime.now().strftime("%y%m")
    
    # Find latest in current month
    latest = (
        db.query(MaterialRequisition)
        .filter(MaterialRequisition.requisition_no.like(f"{prefix}{date_str}%"))
        .order_by(MaterialRequisition.id.desc())
        .first()
    )
    
    if latest:
        # Extract sequence and increment
        seq = int(latest.requisition_no[-4:]) + 1
    else:
        seq = 1
    
    return f"{prefix}{date_str}{seq:04d}"


@router.get("/", response_model=List[MaterialRequisitionListOut])
def list_requisitions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("material_requisitions:read")),
    project_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    pagination: PaginationParams = Depends(get_pagination_params),
) -> Any:
    """List all material requisitions with filters."""
    query = db.query(MaterialRequisition).options(
        joinedload(MaterialRequisition.project),
        joinedload(MaterialRequisition.contract),
        joinedload(MaterialRequisition.requester),
    )
    
    # Apply filters
    if project_id:
        query = query.filter(MaterialRequisition.project_id == project_id)
    if status:
        query = query.filter(MaterialRequisition.status == status)
    
    # Non-admins see only their own or project-specific
    if current_user.role != "admin":
        query = query.join(Project).filter(
            (MaterialRequisition.requested_by == current_user.id) |
            (Project.company_id == current_user.company_id)
        )
    
    # Order by newest first
    query = query.order_by(MaterialRequisition.created_at.desc())
    
    result = paginate_query(query, pagination)
    
    # Transform to output format
    items = []
    for req in result["items"]:
        items.append(MaterialRequisitionListOut(
            id=req.id,
            requisition_no=req.requisition_no,
            project_id=req.project_id,
            contract_id=req.contract_id,
            requested_by=req.requested_by,
            status=req.status,
            remarks=req.remarks,
            created_at=req.created_at,
            project_name=req.project.name if req.project else None,
            contract_title=req.contract.title if req.contract else None,
            requester_name=req.requester.full_name if req.requester else None,
            item_count=len(req.items),
        ))
    
    return items


@router.get("/{requisition_id}", response_model=MaterialRequisitionOut)
def get_requisition(
    requisition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("material_requisitions:read")),
) -> Any:
    """Get single requisition with items."""
    req = (
        db.query(MaterialRequisition)
        .options(
            joinedload(MaterialRequisition.project),
            joinedload(MaterialRequisition.contract),
            joinedload(MaterialRequisition.requester),
            joinedload(MaterialRequisition.items).joinedload(MaterialRequisitionItem.material),
        )
        .filter(MaterialRequisition.id == requisition_id)
        .first()
    )
    
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")
    
    # Build items output
    items_out = []
    total_requested = 0
    total_approved = 0
    total_issued = 0
    
    for item in req.items:
        items_out.append({
            "id": item.id,
            "requisition_id": item.requisition_id,
            "material_id": item.material_id,
            "custom_material_name": item.custom_material_name,
            "requested_qty": item.requested_qty,
            "approved_qty": item.approved_qty,
            "issued_qty": item.issued_qty,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "material_code": item.material.item_code if item.material else None,
            "material_name": item.material.item_name if item.material else item.custom_material_name,
            "material_unit": item.material.unit if item.material else None,
        })
        total_requested += float(item.requested_qty)
        total_approved += float(item.approved_qty or 0)
        total_issued += float(item.issued_qty or 0)
    
    return MaterialRequisitionOut(
        id=req.id,
        requisition_no=req.requisition_no,
        project_id=req.project_id,
        contract_id=req.contract_id,
        requested_by=req.requested_by,
        status=req.status,
        remarks=req.remarks,
        created_at=req.created_at,
        updated_at=req.updated_at,
        project_name=req.project.name if req.project else None,
        contract_title=req.contract.title if req.contract else None,
        requester_name=req.requester.full_name if req.requester else None,
        items=items_out,
        total_items=len(items_out),
        total_requested_qty=total_requested,
        total_approved_qty=total_approved,
        total_issued_qty=total_issued,
    )


@router.post("/", response_model=MaterialRequisitionOut, status_code=status.HTTP_201_CREATED)
def create_requisition(
    data: MaterialRequisitionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("material_requisitions:create")),
) -> Any:
    """Create new material requisition with items."""
    # Validate project exists
    project = db.query(Project).filter(Project.id == data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Generate requisition number
    req_no = _generate_req_no(db)
    
    # Create requisition
    req = MaterialRequisition(
        requisition_no=req_no,
        project_id=data.project_id,
        contract_id=data.contract_id,
        requested_by=current_user.id,
        status="draft",
        remarks=data.remarks,
    )
    db.add(req)
    db.flush()  # Get the ID
    
    # Create items
    for item_data in data.items:
        # Validate material exists if provided
        material_name = item_data.custom_material_name
        if item_data.material_id:
            material = db.query(Material).filter(Material.id == item_data.material_id).first()
            if material:
                material_name = material.item_name
        
        item = MaterialRequisitionItem(
            requisition_id=req.id,
            material_id=item_data.material_id,
            custom_material_name=material_name,
            requested_qty=item_data.requested_qty,
            approved_qty=0,
            issued_qty=0,
        )
        db.add(item)
    
    db.commit()
    db.refresh(req)
    
    # Return using get_requisition logic
    return get_requisition(req.id, db, current_user)


@router.put("/{requisition_id}", response_model=MaterialRequisitionOut)
def update_requisition(
    requisition_id: int,
    data: MaterialRequisitionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("material_requisitions:update")),
) -> Any:
    """Update requisition (only in DRAFT status)."""
    req = db.query(MaterialRequisition).filter(MaterialRequisition.id == requisition_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")
    
    if req.status != "draft":
        raise HTTPException(status_code=400, detail="Only DRAFT requisitions can be edited")
    
    if req.requested_by != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You can only edit your own requisitions")
    
    # Update fields
    if data.project_id:
        req.project_id = data.project_id
    if data.contract_id is not None:
        req.contract_id = data.contract_id
    if data.remarks is not None:
        req.remarks = data.remarks
    
    db.commit()
    db.refresh(req)
    
    return get_requisition(req.id, db, current_user)


@router.post("/{requisition_id}/submit", response_model=MaterialRequisitionOut)
def submit_requisition(
    requisition_id: int,
    data: MaterialRequisitionSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("material_requisitions:update")),
) -> Any:
    """Submit requisition for approval."""
    req = db.query(MaterialRequisition).filter(MaterialRequisition.id == requisition_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")
    
    if req.status != "draft":
        raise HTTPException(status_code=400, detail="Only DRAFT requisitions can be submitted")
    
    if req.requested_by != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You can only submit your own requisitions")
    
    # Check if has items
    if not req.items:
        raise HTTPException(status_code=400, detail="Cannot submit empty requisition")
    
    req.status = "submitted"
    if data.remarks:
        req.remarks = (req.remarks or "") + f"\n[Submit]: {data.remarks}"
    
    db.commit()
    
    return get_requisition(req.id, db, current_user)


@router.post("/{requisition_id}/approve", response_model=MaterialRequisitionOut)
def approve_requisition(
    requisition_id: int,
    data: MaterialRequisitionApprove,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("material_requisitions:approve")),
) -> Any:
    """Approve or reject requisition (Manager only)."""
    req = db.query(MaterialRequisition).filter(MaterialRequisition.id == requisition_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")
    
    if req.status != "submitted":
        raise HTTPException(status_code=400, detail="Only SUBMITTED requisitions can be approved/rejected")
    
    if data.approved:
        req.status = "approved"
        
        # Update approved quantities
        if data.items:
            for item_data in data.items:
                item = db.query(MaterialRequisitionItem).filter(
                    MaterialRequisitionItem.id == item_data.id,
                    MaterialRequisitionItem.requisition_id == req.id,
                ).first()
                if item and item_data.approved_qty is not None:
                    item.approved_qty = item_data.approved_qty
    else:
        req.status = "rejected"
    
    req.remarks = (req.remarks or "") + f"\n[{ 'Approve' if data.approved else 'Reject' } by {current_user.full_name}]: {data.remarks or ''}"
    
    db.commit()
    
    return get_requisition(req.id, db, current_user)


@router.post("/{requisition_id}/issue", response_model=MaterialRequisitionOut)
def issue_requisition(
    requisition_id: int,
    data: MaterialRequisitionIssue,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("material_requisitions:issue")),
) -> Any:
    """Issue materials from store (Store keeper only)."""
    req = db.query(MaterialRequisition).filter(MaterialRequisition.id == requisition_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")
    
    if req.status not in ["approved", "partial"]:
        raise HTTPException(status_code=400, detail="Only APPROVED or PARTIAL requisitions can be issued")
    
    # Update issued quantities
    total_issued = 0
    total_requested = 0
    
    for item_data in data.items:
        item = db.query(MaterialRequisitionItem).filter(
            MaterialRequisitionItem.id == item_data.id,
            MaterialRequisitionItem.requisition_id == req.id,
        ).first()
        
        if item and item_data.issued_qty is not None:
            item.issued_qty = item_data.issued_qty
            total_issued += float(item_data.issued_qty)
        
        total_requested += float(item.approved_qty or item.requested_qty)
    
    # Update status based on issuance
    if total_issued >= total_requested:
        req.status = "issued"
    else:
        req.status = "partial"
    
    req.remarks = (req.remarks or "") + f"\n[Issue by {current_user.full_name}]: {data.remarks or ''}"
    
    db.commit()
    
    return get_requisition(req.id, db, current_user)


@router.delete("/{requisition_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_requisition(
    requisition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("material_requisitions:delete")),
) -> None:
    """Delete requisition (only DRAFT)."""
    req = db.query(MaterialRequisition).filter(MaterialRequisition.id == requisition_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")
    
    if req.status != "draft":
        raise HTTPException(status_code=400, detail="Only DRAFT requisitions can be deleted")
    
    if req.requested_by != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You can only delete your own requisitions")
    
    db.delete(req)
    db.commit()
