# RBAC Quick Reference Card

## Permission Strings

Format: `{module}:{action}`

| Module | Actions | Example |
|--------|---------|---------|
| dashboard | read | `dashboard:read` |
| companies | read, create, update, delete | `companies:update` |
| projects | read, create, update, delete | `projects:delete` |
| vendors | read, create, update | `vendors:create` |
| materials | read, create, update | `materials:update` |
| requisitions | read, create, update, delete, approve | `requisitions:approve` |
| labour_attendance | read, create, update, approve | `labour_attendance:create` |
| labour_bills | read, create, update, approve | `labour_bills:approve` |
| measurements | read, create, update, submit, approve | `measurements:submit` |
| ra_bills | read, create, update, submit, verify, approve | `ra_bills:verify` |
| payments | read, create, approve | `payments:approve` |
| contracts | read, create, update | `contracts:read` |
| documents | read, create, update, delete | `documents:create` |

## Backend Snippets

### Basic Permission Check
```python
from backend.app.core.permissions import require_permissions

@router.get("/items")
def list_items(
    user: User = Depends(require_permissions("items:read")),
):
    return items
```

### Complex Permission with Context
```python
from backend.app.middlewares import PermissionService, FieldMaskingService

@router.get("/items/{id}")
def get_item(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    perm = PermissionService(db, user)
    result = perm.check_permission(
        resource_type="items",
        action="read",
        resource_id=id,
    )
    if not result.granted:
        raise HTTPException(403, detail=result.reason)
    
    # Apply masking
    masker = FieldMaskingService(user.role)
    return masker.apply_masking(item)
```

### Audit Logging
```python
from backend.app.middlewares import AuditLogger

@router.post("/items")
def create_item(
    data: ItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # ... create logic ...
    
    audit = AuditLogger(db, user)
    audit.log_data_access("items", item.id, "create")
    return item
```

## Frontend Snippets

### Hook Usage
```tsx
import { usePermission, useCanPerform, useFieldMask } from "@/lib/rbac";

function MyComponent() {
  // Basic permission
  const canCreate = usePermission("projects:create");
  
  // With context
  const { allowed, reason } = useCanPerform("requisitions", "approve", {
    resourceOwnerId: req.created_by,
    currentState: req.status,
  });
  
  // Field masking
  const maskedCompany = useFieldMask(company, "company");
}
```

### Component Usage
```tsx
import { 
  PermissionGate, 
  ActionGate, 
  WorkflowGate,
  SmartActionButton 
} from "@/components/shell/permission-gate-new";

// Basic gate
<PermissionGate permissions="projects:delete">
  <DeleteButton />
</PermissionGate>

// Workflow-aware
<WorkflowGate
  resourceType="requisitions"
  action="submit"
  currentState={req.status}
>
  <SubmitButton />
</WorkflowGate>

// Smart button
<SmartActionButton
  resourceType="requisitions"
  action="approve"
  resourceOwnerId={req.created_by}
  currentState={req.status}
  onClick={handleApprove}
>
  Approve
</SmartActionButton>
```

## Common Patterns

### CRUD with RBAC
```python
@router.get("/items")      # require_permissions("items:read")
@router.post("/items")     # require_permissions("items:create")
@router.put("/items/{id}") # require_permissions("items:update")
@router.delete("/items/{id}") # require_permissions("items:delete")
```

### Approval Workflow
```python
@router.post("/items/{id}/approve")
def approve_item(id: int, user: User = Depends(get_current_user)):
    perm = PermissionService(db, user)
    
    # Check self-approval
    item = db.query(Item).get(id)
    if perm.is_self_approval(item.created_by):
        raise HTTPException(403, "Cannot approve own item")
    
    # Check state transition
    if not perm.check_state_transition("items", item.status, "approved"):
        raise HTTPException(400, "Invalid state transition")
    
    # Approve
    item.status = "approved"
    db.commit()
```

### Field Masking in API
```python
@router.get("/companies")
def list_companies(user: User = Depends(get_current_user)):
    companies = db.query(Company).all()
    masker = FieldMaskingService(user.role)
    return [masker.mask_company_fields(c) for c in companies]
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| 403 Forbidden | Permission denied | Check user role has required permission |
| Fields showing `***MASKED***` | Field masking active | Verify role should see field |
| Self-approval blocked | Separation of duties | Different user must approve |
| Empty list | Data isolation | User only sees own company data |
| State transition fails | Invalid workflow | Check allowed transitions for state |

## Role Capabilities Summary

| Capability | Admin | PM | Engineer | Accountant | Contractor | Viewer |
|------------|:-----:|:--:|:--------:|:----------:|:----------:|:------:|
| Create Project | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Approve Requisition | ✓ | ✓ | ✗* | ✗ | ✗ | ✗ |
| Create Measurement | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| Approve Payment | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| View GST/PAN | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| Delete Records | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |

*Engineer can approve requisitions in their scope

## Files Modified/Created

### Backend
- `backend/app/core/permissions.py` - Core definitions
- `backend/app/middlewares/permission_service.py` - Main service
- `backend/app/middlewares/ownership_middleware.py` - Ownership checks
- `backend/app/middlewares/field_masking.py` - Data masking
- `backend/app/middlewares/audit_logger.py` - Compliance logging
- `backend/app/middlewares/__init__.py` - Exports

### Frontend
- `frontend/src/lib/rbac.ts` - Utility functions & hooks
- `frontend/src/components/shell/permission-gate-new.tsx` - React components
