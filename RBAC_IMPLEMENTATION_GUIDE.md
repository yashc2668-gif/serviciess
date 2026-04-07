# Enterprise RBAC Implementation Guide

## Overview

This guide documents the enterprise-grade Role-Based Access Control (RBAC) system implemented for the Construction ERP. The system provides a **6-level permission hierarchy** ensuring data security, compliance, and proper separation of duties.

## 6-Level Permission Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                    PERMISSION HIERARCHY                         │
├─────────────────────────────────────────────────────────────────┤
│ 1. Module Level     │ Which modules can the user access?       │
│ 2. Action Level     │ What actions (CRUD, Approve, etc.)?       │
│ 3. Data Scope       │ Own data, Team data, Department, All?     │
│ 4. Field Level      │ Which fields are visible (masking)?       │
│ 5. State Based      │ Workflow state permissions                │
│ 6. Time Based       │ Time-window restrictions (future)         │
└─────────────────────────────────────────────────────────────────┘
```

## Roles Matrix

| Role | Description | Key Permissions |
|------|-------------|-----------------|
| **Admin** | Full system access | `*` (Wildcard) |
| **Project Manager** | Project oversight | Companies:Read, Projects:All, Vendors:All, Requisitions:Approve |
| **Engineer** | Field operations | Projects:Read/Update, Materials:All, Measurements:Create/Submit |
| **Accountant** | Financial control | Payments:Approve, RA Bills:Approve, Secured Advances:All |
| **Contractor** | Limited view | Dashboard:Read, Projects:Read, Materials:Read |
| **Viewer** | Read-only access | Dashboard:Read, Projects:Read (no sensitive data) |

## Critical Security Rules

### 1. Self-Approval Prevention
```python
# Creator cannot approve their own submissions
def can_approve(user_id, resource_owner_id, action):
    if action == "approve" and user_id == resource_owner_id:
        return False  # Self-approval not allowed
```

### 2. Data Isolation
- **Contractor**: Only sees own company's data
- **Engineer**: Own team's data + assigned projects
- **PM**: All projects under management
- **Admin**: No restrictions

### 3. Field Masking
Sensitive fields are automatically masked based on role:

| Field | Admin | Engineer | Contractor | Viewer |
|-------|-------|----------|------------|--------|
| Company Name | ✓ | ✓ | ✓ | ✓ |
| Address | ✓ | ✓ | ✓ | ✓ |
| GST Number | ✓ | ✓ | ✗ | ✗ |
| PAN Number | ✓ | ✗ | ✗ | ✗ |
| Phone | ✓ | ✓ | ✗ | ✗ |
| Email | ✓ | ✓ | ✗ | ✗ |

## Backend Implementation

### File Structure
```
backend/app/
├── core/
│   └── permissions.py          # Core permission definitions
├── middlewares/
│   ├── __init__.py             # Middleware exports
│   ├── permission_service.py   # Main permission checking
│   ├── ownership_middleware.py # Resource ownership
│   ├── field_masking.py        # Data masking
│   └── audit_logger.py         # Compliance logging
```

### Usage in API Endpoints

#### Method 1: Permission Service (Recommended for Complex Cases)
```python
@router.get("/companies/{id}")
def get_company(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Initialize permission service
    perm_service = PermissionService(db, current_user)
    
    # Check permission with full context
    result = perm_service.check_permission(
        resource_type="companies",
        action="read",
        resource_id=id,
    )
    
    if not result.granted:
        raise HTTPException(403, detail=result.reason)
    
    # Apply field masking
    field_masker = FieldMaskingService(current_user.role)
    company = db.query(Company).get(id)
    return field_masker.mask_company_fields(company)
```

#### Method 2: FastAPI Dependency (Clean for Simple Cases)
```python
from backend.app.core.permissions import require_permissions

@router.get("/companies")
def list_companies(
    current_user: User = Depends(require_permissions("companies:read")),
):
    # Permission checked automatically
    return db.query(Company).all()
```

## Frontend Implementation

### File Structure
```
frontend/src/
├── lib/
│   └── rbac.ts                 # Permission utilities & hooks
├── components/shell/
│   └── permission-gate-new.tsx # React components
```

### React Hooks

```typescript
// Check single permission
const canCreate = usePermission("projects:create");

// Check multiple permissions
const { hasAll, hasAny, permissionsMap } = usePermissions([
  "projects:create",
  "projects:update"
]);

// Check with context (ownership, workflow state)
const { allowed, reason } = useCanPerform("requisitions", "approve", {
  resourceOwnerId: requisition.created_by,
  currentState: requisition.status,
});
```

### React Components

```tsx
// Simple permission gate
<PermissionGate permissions="projects:create">
  <CreateButton />
</PermissionGate>

// Workflow-aware gate
<WorkflowGate
  resourceType="requisitions"
  action="approve"
  currentState={requisition.status}
>
  <ApproveButton />
</WorkflowGate>

// Field-level masking
<FieldVisibility fieldName="gst_number" resourceType="company">
  <GSTDisplay value={company.gst_number} />
</FieldVisibility>

// Smart button with auto-disable
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

## Workflow State Permissions

### Requisition States
| State | Allowed Actions | Who Can Act |
|-------|-----------------|-------------|
| `draft` | view, update, delete, submit | Creator |
| `submitted` | view, approve, reject | Approver |
| `pending` | view, approve, reject | Approver |
| `approved` | view | All |
| `rejected` | view, update, delete | Creator |

### RA Bill States
| State | Allowed Actions | Who Can Act |
|-------|-----------------|-------------|
| `draft` | view, update, delete, submit | Creator |
| `submitted` | view, verify | Engineer |
| `under_review` | view, approve, reject | Accountant |
| `approved` | view, paid | Accountant |
| `paid` | view | All |

## Audit Logging

All permission checks and data access are logged:

```python
audit_logger.log_permission_check(
    resource_type="companies",
    action="update",
    granted=False,
    context={"reason": "Insufficient permissions"}
)

audit_logger.log_data_access(
    resource_type="companies",
    resource_id=123,
    action="read",
    metadata={"fields_accessed": ["name", "address"]}
)
```

## Migration Guide

### Step 1: Update Imports
```python
# Old
from backend.app.api.deps import require_permissions

# New
from backend.app.middlewares import PermissionService, FieldMaskingService
from backend.app.core.permissions import require_permissions
```

### Step 2: Add Permission Checks to Endpoints
Replace simple checks with comprehensive permission service.

### Step 3: Add Field Masking
Wrap responses with field masking service.

### Step 4: Add Audit Logging
Add audit log calls for sensitive operations.

## Testing Checklist

- [ ] Admin can access all resources
- [ ] Contractor cannot see other companies' data
- [ ] Engineer cannot approve own requisitions
- [ ] GST/PAN masked for non-admin roles
- [ ] Audit logs capture all permission checks
- [ ] Workflow state prevents invalid actions
- [ ] Frontend components hide unauthorized actions
- [ ] API returns 403 for unauthorized access

## Compliance Standards

This RBAC system addresses:
- **SOX Compliance**: Separation of duties (creator ≠ approver)
- **GDPR**: Field-level data protection
- **ISO 27001**: Access control and audit trails
- **Industry Standard**: Role-based access with least privilege
