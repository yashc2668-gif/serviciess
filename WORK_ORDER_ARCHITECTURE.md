# Work Order Architecture - World Class Design

## Core Concept: "Contract Duality Pattern"

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         YOUR COMPANY (M2N)                                  │
│                         ═══════════════════                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   INCOMING (Client → M2N)              OUTGOING (M2N → Subcontractor)      │
│   ═════════════════════════              ═══════════════════════════════    │
│                                                                             │
│   📋 Client Work Order                  📋 Subcontract Work Order          │
│                                                                             │
│   • Client Name                         • Contractor/Vendor Name           │
│   • WO Number                           • WO Number                        │
│   • Project (Your Project)              • Project (Same Project)           │
│   • BOQ (What you'll do)                • BOQ (What they'll do)            │
│   • Payment Terms (Client pays you)     • Rate Analysis (You pay them)     │
│   • GST/TDS (Incoming)                  • GST/TDS (Outgoing)               │
│   • Retention (Held by client)          • Retention (You hold)             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Existing Model Enhancement

Your `Contract` model already supports this via `contract_type`:

```python
# contracts table
contract_type = Column(String(30), nullable=False, default="vendor_contract")
# Values: "client_contract" | "vendor_contract"
```

## Recommended Architecture

### Option A: Enhanced Contract Model (Recommended)

Leverage existing `Contract` model with extensions:

```python
class Contract(Base):
    __tablename__ = "contracts"
    
    # Existing fields
    contract_type = Column(String(30))  # "incoming" | "outgoing"
    
    # NEW: Work Order Specific Fields
    wo_number = Column(String(100), unique=True, index=True)
    wo_type = Column(String(20))  # "client" | "subcontract"
    
    # INCOMING (Client → M2N)
    client_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    client_po_number = Column(String(100), nullable=True)
    client_payment_terms = Column(String(255), nullable=True)  # "30% advance, 70% on completion"
    
    # OUTGOING (M2N → Subcontractor)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    contractor_category = Column(String(50), nullable=True)  # "civil", "electrical", "plumbing"
    work_scope_summary = Column(Text, nullable=True)
    
    # FINANCIAL (Both)
    advance_percentage = Column(Numeric(5, 2), default=0)  # 0-100
    security_deposit = Column(Numeric(18, 2), default=0)
    billing_cycle = Column(String(50), default="monthly")  # monthly | fortnightly | milestone
    
    # APPROVAL WORKFLOW
    approval_status = Column(String(20), default="draft")  # draft | pending | approved | rejected
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
```

### Option B: Separate Work Order Table (If contracts are too different)

```python
class WorkOrder(Base):
    __tablename__ = "work_orders"
    
    id = Column(Integer, primary_key=True)
    wo_number = Column(String(100), unique=True)
    wo_type = Column(String(20))  # "incoming" | "outgoing"
    
    # Polymorphic relationship
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    
    # For quick access without joining contracts
    project_id = Column(Integer, ForeignKey("projects.id"))
    party_id = Column(Integer)  # company_id OR vendor_id
    party_type = Column(String(20))  # "client" | "vendor"
```

## UI Architecture

### Tab-Based Design (Clean & Intuitive)

```
┌─────────────────────────────────────────────────────────────────┐
│  WORK ORDERS                                                    │
│  ═══════════                                                    │
│                                                                 │
│  [📥 Incoming]  [📤 Outgoing]  [📊 Analytics]                   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Incoming Work Orders (Client → M2N)                           │
│  ═══════════════════════════════════                           │
│                                                                 │
│  ┌─────────────┬──────────────┬────────────┬──────────┬──────┐ │
│  │ WO Number   │ Client       │ Project    │ Value    │Status│ │
│  ├─────────────┼──────────────┼────────────┼──────────┼──────┤ │
│  │ WO-2024-001 │ ABC Infra    │ Tower A    │ ₹5.2Cr   │Active│ │
│  │ WO-2024-002 │ XYZ Builders │ Mall B     │ ₹12.8Cr  │Active│ │
│  └─────────────┴──────────────┴────────────┴──────────┴──────┘ │
│                                                                 │
│  [+ Create Incoming WO]                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Form Design - Different Fields per Type

```typescript
// Form config based on WO type
const INCOMING_FIELDS = [
  'client_name', 'wo_number', 'project', 'boq',
  'payment_terms', 'gst_rate', 'tds_rate', 'retention_percent'
];

const OUTGOING_FIELDS = [
  'contractor_name', 'wo_number', 'project', 'work_category',
  'scope_of_work', 'rate_analysis', 'advance_percent', 
  'security_deposit', 'billing_cycle'
];
```

## Data Flow Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Client     │     │     M2N      │     │ Subcontractor│
│  (External)  │◄───►│   (System)   │◄───►│  (Vendor)    │
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │                    │
       │                    │                    │
       ▼                    ▼                    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│Incoming WO   │     │Project/BOQ   │     │Outgoing WO   │
│• WO Number   │     │• Measurements│     │• WO Number   │
│• Payment In  │     │• RA Bills    │     │• Payment Out │
│• Retention + │     │• Cost Mgmt   │     │• Retention - │
└──────────────┘     └──────────────┘     └──────────────┘
```

## Key Business Logic

### 1. Contract Value Reconciliation
```python
# Total project value should match:
# Incoming WO Value = Sum of all Outgoing WO Values + Margin

def validate_contract_coverage(project_id):
    incoming = sum(wo.value for wo in get_incoming_wos(project_id))
    outgoing = sum(wo.value for wo in get_outgoing_wos(project_id))
    margin = incoming - outgoing
    margin_percent = (margin / incoming) * 100
    
    if margin_percent < 10:  # Less than 10% margin
        raise Warning("Margin too low!")
```

### 2. Retention Tracking
```python
# Incoming: Client holds retention from M2N
# Outgoing: M2N holds retention from subcontractor

class RetentionTracker:
    def get_net_retention(self):
        incoming_retention = self.incoming_wo.retention_amount
        outgoing_retention = sum(wo.retention_amount for wo in self.outgoing_wos)
        return incoming_retention - outgoing_retention  # Should be >= 0
```

### 3. Billing Cycle Alignment
```python
# M2N should receive payment from client BEFORE paying subcontractors
# Or at least have matching cycles

def validate_billing_cycles(incoming_wo, outgoing_wo):
    incoming_cycle = incoming_wo.billing_cycle  # "monthly"
    outgoing_cycle = outgoing_wo.billing_cycle  # "monthly"
    
    # Outgoing should never be more frequent than incoming
    cycle_rank = {"milestone": 1, "fortnightly": 2, "monthly": 3}
    if cycle_rank[outgoing_cycle] < cycle_rank[incoming_cycle]:
        raise ValidationError("Subcontractor billing cycle cannot be faster than client cycle")
```

## Recommended Implementation

### Step 1: Enhance Contract Model (5 min)
```python
# Add to existing Contract model
wo_type = Column(String(20))  # "incoming" | "outgoing"
wo_number = Column(String(100), unique=True)
contractor_category = Column(String(50))  # For outgoing
client_po_number = Column(String(100))    # For incoming
```

### Step 2: Create UI Tabs (30 min)
- Incoming WO List (filter: contract_type="incoming")
- Outgoing WO List (filter: contract_type="outgoing")
- Dynamic form fields based on type

### Step 3: Add Validations (20 min)
- WO Number uniqueness
- Contract value reconciliation
- Retention tracking

### Step 4: Reports (30 min)
- Margin analysis (Incoming - Outgoing)
- Retention summary
- Billing cycle alignment

## Database Schema

```sql
-- Existing contracts table (enhanced)
ALTER TABLE contracts ADD COLUMN wo_type VARCHAR(20);
ALTER TABLE contracts ADD COLUMN wo_number VARCHAR(100) UNIQUE;
ALTER TABLE contracts ADD COLUMN contractor_category VARCHAR(50);
ALTER TABLE contracts ADD COLUMN client_po_number VARCHAR(100);
ALTER TABLE contracts ADD COLUMN advance_percentage DECIMAL(5,2) DEFAULT 0;
ALTER TABLE contracts ADD COLUMN billing_cycle VARCHAR(50) DEFAULT 'monthly';
```

## API Endpoints

```
GET  /api/work-orders?type=incoming
GET  /api/work-orders?type=outgoing
POST /api/work-orders
     Body: { wo_type: "incoming", ... } or { wo_type: "outgoing", ... }
GET  /api/work-orders/{id}/margin-analysis
GET  /api/work-orders/{id}/retention-summary
```

This architecture gives you:
1. ✅ **Single source of truth** (contracts table)
2. ✅ **Clean UI separation** (tabs for incoming/outgoing)
3. ✅ **Financial reconciliation** (margin tracking)
4. ✅ **Workflow support** (approval status)
5. ✅ **Extensible** (easy to add new WO types)
