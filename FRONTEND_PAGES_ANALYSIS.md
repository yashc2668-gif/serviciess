# M2N Construction ERP — Frontend Pages Comprehensive Analysis

**Document Goal:** Establish unified testing patterns, identify all pages requiring tests, and provide templates for systematic coverage.

---

## Executive Summary

- **Total Pages:** 31 page components across 31 feature modules
- **Test Status:** Zero unit tests exist yet (only helper function tests); e2e tests use Playwright route interception
- **Architecture:** All pages follow TanStack Query + React Hook Form + Zod + Permission Gates pattern
- **Testing Approach:** Unit tests (Vitest + React Testing Library) for page components; E2E tests (Playwright) for workflows
- **Priority:** Critical path pages first (masters, key workflows, finance operations)

---

## PART 1: Common Patterns Across All Pages

### 1.1 Data Fetching Pattern (TanStack Query)

**Universal Structure:**
```typescript
// Multiple related queries enabled by auth
const { accessToken } = useAuth();

const materialsQuery = useQuery({
  queryKey: ["materials"],
  queryFn: () => fetchMaterials(accessToken ?? ""),
  enabled: Boolean(accessToken),
});

const projectsQuery = useQuery({
  queryKey: ["projects"],
  queryFn: () => fetchProjects(accessToken ?? ""),
  enabled: Boolean(accessToken),
});

// Safe data access with EMPTY_LIST fallback
const materials = materialsQuery.data ?? EMPTY_LIST;
const projects = projectsQuery.data ?? EMPTY_LIST;
```

**Key Patterns:**
- Query keys: `["entity"]`, `["entity", filter, sort, page]`, or `["entity", "table", ...]`
- All queries gated by `Boolean(accessToken)`
- Data guaranteed not-null via `?? EMPTY_LIST`
- No manual loading/error states—delegated to query object
- Pagination/search queries use `useDeferredValue` for debouncing

**Stale Time & Retry:** Default 30s stale time, retry: 1 (from convention docs)

---

### 1.2 Form Management Pattern

**Universal Schema + Type Inference:**
```typescript
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, useFieldArray } from "react-hook-form";

const materialFormSchema = z.object({
  item_code: z.string().min(1, "Item code is required."),
  item_name: z.string().min(2, "Material name is required."),
  unit: z.string().min(1, "Unit is required."),
  reorder_level: z.number().min(0),
  default_rate: z.number().min(0),
  is_active: z.boolean(),
});

type MaterialFormValues = z.infer<typeof materialFormSchema>;

// In component:
const { register, handleSubmit, control, formState: { errors, isSubmitting } } = useForm<MaterialFormValues>({
  resolver: zodResolver(materialFormSchema),
  defaultValues: buildMaterialFormDefaults(),
});
```

**Multi-line Forms (Requisitions, Receipts, Bills):**
```typescript
const { fields, append, remove } = useFieldArray({
  control,
  name: "items", // array in schema
});

// Render:
{fields.map((field, idx) => (
  <div key={field.id}>
    {/* Inputs for field */}
    <button onClick={() => remove(idx)}>Remove</button>
  </div>
))}
```

**Key Patterns:**
- All forms use Zod + `zodResolver` + React Hook Form
- Type-safe schema inference (`z.infer<...>`)
- Helper function for defaults (e.g., `buildMaterialFormDefaults()`)
- Multi-line forms use `useFieldArray` pattern
- `isSubmitting` state prevents double-submit

---

### 1.3 UI Component Layout Pattern

**Consistent Page Structure:**
```typescript
export default function EntityPage() {
  // ... setup ...
  
  if (query.isLoading) return <PageSkeleton />;
  if (query.error || !query.data) return <ErrorState onRetry={() => query.refetch()} />;
  
  const data = query.data ?? EMPTY_LIST;
  if (data.length === 0) return <EmptyState />;
  
  return (
    <PermissionGate permissions={["entity:read"]}>
      <div className="space-y-6">
        <PageHeader eyebrow="..." title="..." description="..." />
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard label="Total" value={formatCompactNumber(data.length)} />
          {/* more stat cards */}
        </div>
        
        {/* Search/Filter Bar */}
        <div className="flex gap-2">
          <input onchange={setSearch} placeholder="Search..." />
          <select onChange={setStatusFilter} value={statusFilter}>
            <option>All Statuses</option>
            {/* ... */}
          </select>
        </div>
        
        {/* Modal/Drawer for create/edit */}
        <PermissionGate permissions={["entity:create"]}>
          <Button onClick={() => setEditId(null)}>Create</Button>
        </PermissionGate>
        
        {/* Data Table */}
        <DataTable columns={columns} data={filteredData} />
        
        {/* Modal/Drawer Forms */}
        <PermissionGate permissions={["entity:write"]}>
          {editId && <EditModal ... />}
        </PermissionGate>
      </div>
    </PermissionGate>
  );
}
```

**Key Patterns:**
- `PageSkeleton` for loading
- `ErrorState` with retry callback
- `EmptyState` for zero data
- All data mutations/creations gated by `PermissionGate`
- `PageHeader` with eyebrow, title, description (design language)
- `StatCard` for key metrics
- Search/filter inputs as local state
- `DataTable` component with columns prop
- Modal/Drawer for edit/create workflows

---

### 1.4 State Management Pattern (All Local)

**No Redux/Global State—Purely Local:**
```typescript
// Search/filter local state
const [search, setSearch] = useState("");
const deferredSearch = useDeferredValue(search); // Debounce

// Pagination
const [tablePage, setTablePage] = useState(1);
const [tablePageSize, setTablePageSize] = useState(25);

// Sorting
const [tableSort, setTableSort] = useState<{ id: string; direction: "asc" | "desc" }>({
  id: "created_at",
  direction: "desc",
});

// Filter dropdowns
const [statusFilter, setStatusFilter] = useState("all");
const [projectFilter, setProjectFilter] = useState("all");

// Modal state
const [editingId, setEditingId] = useState<number | null>(null);
const [drawerMode, setDrawerMode] = useState<"create" | "review" | null>(null);

// Feedback
const [serverMessage, setServerMessage] = useState<string | null>(null);
const [localError, setLocalError] = useState<string | null>(null);

// Derived state (memoized)
const filtered = useMemo(() => {
  return data
    .filter((item) => item.status === statusFilter || statusFilter === "all")
    .filter((item) => item.name.includes(deferredSearch));
}, [data, statusFilter, deferredSearch]);
```

**Key Patterns:**
- No Redux/Context for page-local state
- Derived/computed state via `useMemo`
- Search debounced with `useDeferredValue`
- Server state managed by TanStack Query (never local)
- Error/success feedback via local state

---

### 1.5 Mutation & Error Handling Pattern

**Create/Update/Delete & Approval Actions:**
```typescript
const createMutation = useMutation({
  mutationFn: async (formData: MaterialFormValues) => {
    return createMaterial(accessToken ?? "", formData);
  },
  onSuccess: (newItem) => {
    queryClient.setQueryData(["materials"], (old: Material[]) => [newItem, ...old]);
    setServerMessage("Material created successfully.");
    setEditingId(null);
    reset(); // Clear form
  },
  onError: (error) => {
    setServerMessage(getApiErrorMessage(error));
  },
});

const handleSubmit = handleSubmit(async (data) => {
  await createMutation.mutateAsync(data);
});
```

**Approval/Workflow Actions:**
```typescript
const approveMutation = useMutation({
  mutationFn: async ({ billId, remarks }: { billId: number; remarks?: string }) => {
    return approveLabourBill(accessToken ?? "", billId, remarks);
  },
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ["labour-bills"] });
    setServerMessage("Bill approved successfully.");
    setSelectedBillId(null);
  },
});
```

**Key Patterns:**
- All mutations wrap API calls with error/success handling
- `onSuccess` invalidates queries and resets UI state
- `onError` uses `getApiErrorMessage()` utility
- Server message feedback via state
- Form cleared on success via `reset()`
- Permission gates prevent unauthorized UI

---

### 1.6 Permission Pattern

**Route-level Gate:**
```typescript
export default function ReportPage() {
  return (
    <PermissionGate permissions={["report:read"]}>
      {/* Entire page content */}
    </PermissionGate>
  );
}
```

**Specific Action Gate:**
```typescript
<PermissionGate permissions={["material:create"]}>
  <Button onClick={openCreateModal}>Create Material</Button>
</PermissionGate>
```

**Workflow Action Gate:**
```typescript
{hasPermissions(user.permissions, ["bill:approve"]) && (
  <Button onClick={() => approveMutation.mutate({ billId })}>
    Approve Bill
  </Button>
)}
```

**Permission String Format:** `"{entity}:{action}"` (e.g., `material:create`, `bill:approve`, `payment:release`)

---

### 1.7 Data Table Pattern

**Columns Definition:**
```typescript
const columns: DataTableColumn<Material>[] = [
  {
    key: "item_code",
    header: "Item Code",
    width: 120,
  },
  {
    key: "item_name",
    header: "Item Name",
    width: 200,
  },
  {
    key: "current_stock",
    header: "Stock",
    width: 100,
    cell: (row) => formatDecimal(row.current_stock),
  },
  {
    key: "default_rate",
    header: "Rate",
    width: 100,
    cell: (row) => formatCurrency(row.default_rate),
  },
  {
    key: "actions",
    header: "Actions",
    width: 80,
    cell: (row) => (
      <Button size="sm" onClick={() => setEditingId(row.id)}>
        Edit
      </Button>
    ),
  },
];
```

**Key Patterns:**
- `DataTableColumn<T>` generic type
- `key`, `header`, `width` properties
- Optional `cell` function for custom rendering
- Sorting by column click
- Pagination state management
- No server-side pagination for small datasets; fetch all and filter client-side

---

### 1.8 Keyboard Shortcuts Pattern (Masters Pages Only)

**Used in Pages with Search:**
```typescript
const searchRef = useRef<HTMLInputElement>(null);
useKeyboardShortcuts([
  {
    key: "/",
    handler: () => searchRef.current?.focus(),
    description: "Focus search",
  },
  {
    key: "n",
    handler: () => setEditingId(null), // Open create modal
    description: "New material",
  },
]);
```

---

### 1.9 Export Pattern (Masters & Reports)

**Matrix Export:**
```typescript
const exportMutation = useMutation({
  mutationFn: async () => exportMaterials(accessToken ?? "", { statusFilter, categoryFilter }),
  onSuccess: (blob) => {
    saveBlob(blob, "materials.csv");
  },
});
```

**Key Patterns:**
- Pass filters to API for filtered export
- Receive blob, save via `saveBlob()` utility
- CSV or PDF formats
- Typically called from page header export button

---

## PART 2: Page Categories & Test Scenarios

### Category 1: Masters Pages (CRUD)

**Pages:** materials, vendors, contracts, projects, labour, labour-contractors, boq

**Common Features:**
- Full-text search (client-side with debounce)
- Category/type filters
- Pagination (25 rows per page)
- Create form (modal/inline)
- Edit existing record
- Delete (some pages)
- Export to CSV
- Attention badges (stock status, contract value, etc.)
- Stats cards (total count, active count, etc.)

**Test Scenarios:**

1. **Render States**
   - Renders `PageSkeleton` while loading
   - Renders `EmptyState` when data is empty
   - Renders `ErrorState` on API error with retry button
   - Renders table with data when loaded

2. **Search Functionality**
   - Filters items by name/code (case-insensitive)
   - Debounces search input (300ms)
   - Clears results on search clear
   - Shows empty state when no matches

3. **Filter Functionality**
   - Filters by category/type selector
   - Combines multiple filters
   - Persists view on filter change
   - Shows count of results

4. **Pagination**  
   - Shows 25 rows per page
   - Next/previous buttons navigate correctly
   - Page changes reset to page 1 on filter change

5. **Create Form**
   - Form opens on "Create" button click
   - Validates required fields (Zod schema)
   - Shows validation errors inline
   - Submits on form submit
   - Closes form on success
   - Shows error message on failure
   - Permission gate prevents unauthorized users

6. **Edit Existing Record**
   - Prefills form with selected row data
   - Updates record on submit
   - Invalidates query and refreshes table
   - Closes form on success
   - Shows error message on failure

7. **Delete (if applicable)**
   - Shows confirmation
   - Removes from table on success
   - Shows error message on failure

8. **Export**
   - Exports filtered data to CSV
   - Downloads file with correct name
   - Shows loading state during export

9. **Permission Gates**
   - Hides "Create" button if permission denied
   - Hides "Edit" buttons if permission denied
   - Hides "Delete" buttons if permission denied
   - Hides "Export" button if permission denied

10. **Keyboard Shortcuts**
    - `/` key focuses search input
    - `n` key opens create modal (if applicable)

---

### Category 2: Workflow Pages (Multi-line Operations)

**Pages:** material-requisitions, material-issues, material-receipts, labour-bills, labour-attendance, labour-advances, labour-productivity

**Common Features:**
- Multiple-line item forms with add/remove buttons
- Status filters (draft, submitted, approved, completed, etc.)
- Project/vendor/contractor filters
- Approval workflow transitions
- Multi-line calculations (totals, deductions)
- Period/date range filters
- Drawer for review/action

**Test Scenarios:**

1. **Render States**
   - Renders `PageSkeleton` while loading
   - Renders `EmptyState` when no items
   - Renders `ErrorState` on failure
   - Renders list with status badges

2. **Filter & Search**
   - Filters by status (draft, submitted, approved, etc.)
   - Filters by project/vendor/contractor
   - Combines multiple filters
   - Date range filtering

3. **Create New Record**
   - Form opens in "create" mode
   - Can add multiple line items
   - Add line button appends new row
   - Remove line button deletes row
   - Validates all required fields
   - Shows validation errors

4. **Line Item Management**
   - Add line item dynamically
   - Remove line item
   - Edit line item quantity/rate
   - Automatic total calculation
   - Prevents invalid quantities

5. **Submit Workflow**
   - Changes status from draft → submitted
   - Disables edit after submit
   - Shows submit button only in draft state
   - Shows message after submit

6. **Approval Workflow**
   - Approve button visible if permission granted
   - Opens drawer for review/remark
   - Changes status to approved on accept
   - Shows rejection reason if rejected
   - Returns to draft on rejection

7. **Permission Gates**
   - Hides create if permission denied
   - Hides submit if permission denied
   - Hides approve if permission denied
   - Disables actions based on status + permission

---

### Category 3: Complex Finance Workflows

**Pages:** ra-bills, payments, secured-advances

**Common Features:**
- Multi-step approval chains
- Allocation of amounts to multiple bills
- Outstanding amount calculations
- PDF export of bills/receipts
- Complex validation (allocation total = payment total, etc.)
- Date tracking (submitted_at, approved_at, released_at, paid_at)
- Drawer for multi-step actions

**Test Scenarios:**

1. **Render States**
   - Renders with loading state
   - Renders empty or populated
   - Shows error state on API failure

2. **Bill/Payment Creation**
   - Opens form in create mode
   - Validates required fields
   - Contract/project selection
   - Date validation (end date > start date, etc.)
   - Displays totals automatically

3. **Approval Chain**
   - Draft → Submitted → Approved → Released → Paid
   - Each step has permission guards
   - Each step has optional remarks
   - Status flow enforced (cannot skip steps)

4. **Allocation (Payments)**
   - Can allocate payment across multiple RA bills
   - Allocation total ≤ payment amount
   - Shows outstanding per bill
   - Calculates available amount correctly

5. **PDF Export**
   - Exports bill/payment as PDF
   - Contains correct summary
   - Includes signatures section

6. **Outstanding Calculations**
   - Correctly calculates unpaid amount
   - Updates after partial payment
   - Shows zero when fully paid

7. **Multi-step Approval**
   - Can approve with remarks
   - Can release with remarks
   - Cannot approve/release if status wrong
   - Cannot approve/release if permission denied

---

### Category 4: Read-only Pages (Reports, Audit, Dashboard)

**Pages:** reports, audit, dashboard, contract-drilldown

**Common Features:**
- Multiple data queries without mutations
- Charts/visualizations (Recharts)
- Filter combinations (date ranges, entity types, etc.)
- Pagination for large datasets
- Export functionality (CSV, PDF)
- Links to detail pages
- No create/edit/delete

**Test Scenarios:**

1. **Render States**
   - Renders loading state
   - Renders empty/populated
   - Renders error state with retry

2. **Chart Rendering**
   - Charts render with correct data
   - Charts update when filters change
   - Responsive layout

3. **Filters**
   - Date range filtering works
   - Entity type filtering works
   - Multiple filters combine correctly
   - Resets to page 1 on filter change

4. **Pagination**
   - Shows correct page data
   - Navigation buttons work
   - Total results displayed

5. **Export**
   - Exports all or filtered data
   - Correct format (CSV/PDF)
   - Downloads with timestamp filename

6. **Links & Navigation**
   - Drilldown links navigate to detail pages
   - Links pass correct context (filters, IDs, etc.)

---

### Category 5: Authentication Pages

**Pages:** login, forgot-password, reset-password

**Minimal Test Scenarios:**

1. **Login Form**
   - Validates email/password required
   - API call on submit
   - Shows error on failure
   - Redirects on success

2. **Forgot Password**
   - Accepts email
   - Shows confirmation message
   - Calls API endpoint

3. **Reset Password**
   - Accepts new password + confirm
   - Validates match
   - Uses token from URL params
   - Shows success/error

---

### Category 6: Special Pages

**Dashboard:** Read-only metrics & links (multiple queries, no forms, error handling, chart renders)

**Admin/Users:** User management (CRUD for users, role assignment, status toggles)

**AI Boundary:** Configuration page (likely CRUD with complex settings)

---

## PART 3: API Mocking Strategy for Unit Tests

### 3.1 Mock Setup Pattern

**File Structure:**
```
frontend/src/features/materials/
  materials-page.tsx
  materials-page.test.tsx         ← Unit test
  __mocks__/
    materials-api.ts              ← Mock API functions
    fixtures.ts                   ← Mock data
```

**Mock API Functions:**
```typescript
// src/features/materials/__mocks__/materials-api.ts
import { vi } from 'vitest';

export const mockFetchMaterials = vi.fn().mockResolvedValue([
  {
    id: 1,
    item_code: "BRICK",
    item_name: "Red Brick",
    current_stock: 5000,
    default_rate: 8.50,
    is_active: true,
  },
  // ... more fixtures
]);

export const mockCreateMaterial = vi.fn().mockResolvedValue({
  id: 2,
  item_code: "SAND",
  item_name: "Sand",
  current_stock: 0,
  default_rate: 50,
  is_active: true,
});
```

**Fixture Data:**
```typescript
// src/features/materials/__mocks__/fixtures.ts
export const mockMaterials = [
  {
    id: 1,
    item_code: "BRICK",
    item_name: "Red Brick",
    category: "masonry",
    unit: "pcs",
    reorder_level: 1000,
    default_rate: 8.50,
    current_stock: 5000,
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
  },
  // ... more
];
```

---

### 3.2 Mock Setup in Test File

**Standard Test Setup:**
```typescript
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, within, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import MaterialsPage from './materials-page.tsx';

// Mock the API module
vi.mock('@/api/materials', () => ({
  fetchMaterials: vi.fn(),
  createMaterial: vi.fn(),
  updateMaterial: vi.fn(),
}));

vi.mock('@/app/providers/auth-provider', () => ({
  useAuth: vi.fn(() => ({
    accessToken: 'test-token',
    user: { id: 1, email: 'test@example.com', permissions: ['material:read', 'material:create'] },
  })),
}));

describe('MaterialsPage', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  const renderPage = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MaterialsPage />
      </QueryClientProvider>
    );
  };

  it('renders page skeleton while loading', () => {
    vi.mocked(fetchMaterials).mockImplementation(() => new Promise(() => {})); // Never resolves
    renderPage();
    expect(screen.getByRole('progressbar')).toBeInTheDocument(); // Or similar loading indicator
  });

  it('renders empty state when no materials', async () => {
    vi.mocked(fetchMaterials).mockResolvedValueOnce([]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/no materials/i)).toBeInTheDocument();
    });
  });

  it('renders table with materials data', async () => {
    const mockData = [{ id: 1, item_name: 'Red Brick', item_code: 'BRICK', ... }];
    vi.mocked(fetchMaterials).mockResolvedValueOnce(mockData);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Red Brick')).toBeInTheDocument();
    });
  });

  it('filters materials by search', async () => {
    vi.mocked(fetchMaterials).mockResolvedValueOnce([
      { id: 1, item_name: 'Red Brick', ... },
      { id: 2, item_name: 'Sand', ... },
    ]);
    renderPage();
    await waitFor(() => {
      const searchInput = screen.getByPlaceholderText(/search/i);
      expect(searchInput).toBeInTheDocument();
    });
    
    const searchInput = screen.getByPlaceholderText(/search/i);
    await userEvent.type(searchInput, 'Red');
    
    // Wait for debounce
    await waitFor(() => {
      expect(screen.getByText('Red Brick')).toBeInTheDocument();
      expect(screen.queryByText('Sand')).not.toBeInTheDocument();
    }, { timeout: 500 });
  });

  it('opens create form on Create button click', async () => {
    vi.mocked(fetchMaterials).mockResolvedValueOnce([]);
    renderPage();
    
    await waitFor(() => {
      const createButton = screen.getByRole('button', { name: /create/i });
      expect(createButton).toBeInTheDocument();
    });
    
    const createButton = screen.getByRole('button', { name: /create/i });
    await userEvent.click(createButton);
    
    await waitFor(() => {
      expect(screen.getByLabelText(/item code/i)).toBeInTheDocument();
    });
  });

  it('submits create form and refreshes table', async () => {
    vi.mocked(fetchMaterials).mockResolvedValue([
      { id: 1, item_name: 'Red Brick', item_code: 'BRICK', ... },
    ]);
    vi.mocked(createMaterial).mockResolvedValueOnce({
      id: 2,
      item_name: 'Sand',
      item_code: 'SAND',
      ...
    });
    
    renderPage();
    
    // Open form
    const createButton = await screen.findByRole('button', { name: /create/i });
    await userEvent.click(createButton);
    
    // Fill and submit form
    const codeInput = await screen.findByLabelText(/item code/i);
    await userEvent.type(codeInput, 'SAND');
    
    const submitButton = screen.getByRole('button', { name: /submit/i });
    await userEvent.click(submitButton);
    
    // Verify API was called
    await waitFor(() => {
      expect(vi.mocked(createMaterial)).toHaveBeenCalledWith(
        'test-token',
        expect.objectContaining({ item_code: 'SAND' })
      );
    });
    
    // Verify success message appears
    expect(screen.getByText(/created successfully/i)).toBeInTheDocument();
  });

  it('shows error message on API failure', async () => {
    const error = new Error('Network error');
    vi.mocked(fetchMaterials).mockRejectedValueOnce(error);
    renderPage();
    
    await waitFor(() => {
      expect(screen.getByText(/network error|failed to load/i)).toBeInTheDocument();
    });
  });

  it('hides Create button if permission denied', async () => {
    // Re-mock auth with no create permission
    vi.mocked(useAuth).mockReturnValueOnce({
      accessToken: 'test-token',
      user: { id: 1, permissions: ['material:read'] }, // No create
    });
    
    vi.mocked(fetchMaterials).mockResolvedValueOnce([]);
    renderPage();
    
    await waitFor(() => {
      const createButton = screen.queryByRole('button', { name: /create/i });
      expect(createButton).not.toBeInTheDocument();
    });
  });
});
```

---

### 3.3 Query Client Test Setup

**Create `src/test/render.tsx`:**
```typescript
import { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, RenderOptions } from '@testing-library/react';

const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      gcTime: 0, // Disable cache
    },
  },
});

export const renderWithQueryClient = (
  component: ReactNode,
  options?: RenderOptions
) => {
  const queryClient = createTestQueryClient();
  
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>,
    options
  );
};
```

---

## PART 4: Complete List of Pages Requiring Tests

### Masters (CRUD)
1. `src/features/materials/materials-page.tsx` — Materials master with search, filter, create/edit
2. `src/features/vendors/vendors-page.tsx` — Vendor master with type filter
3. `src/features/contracts/contracts-page.tsx` — Contract master with status/vendor filter
4. `src/features/projects/projects-page.tsx` — Project master with company filter, export
5. `src/features/labour/labour-page.tsx` — Labour records (minimal)
6. `src/features/labour-contractors/labour-contractors-page.tsx` — Contractor master
7. `src/features/boq/boq-page.tsx` — Bill of Quantities

### Material Operations (Multi-line Workflow)
8. `src/features/material-requisitions/material-requisitions-page.tsx` — Requisitions with draft→submit→approve 
9. `src/features/material-issues/material-issues-page.tsx` — Issue transactions with multi-line
10. `src/features/material-receipts/material-receipts-page.tsx` — Receipt with vendor/project
11. `src/features/material-adjustments/material-adjustments-page.tsx` — Stock adjustments
12. `src/features/stock-ledger/stock-ledger-page.tsx` — Read-only stock ledger

### Labour Operations (Complex Workflow)
13. `src/features/labour-bills/labour-bills-page.tsx` — Bill workflow with attendance selection
14. `src/features/labour-advances/labour-advances-page.tsx` — Advance request workflow
15. `src/features/labour-attendance/labour-attendance-page.tsx` — Attendance marking
16. `src/features/labour-productivity/labour-productivity-page.tsx` — Productivity tracking

### Finance Operations (Complex Multi-step)
17. `src/features/ra-bills/ra-bills-page.tsx` — RA bill workflow (generate, submit, approve)
18. `src/features/payments/payments-page.tsx` — Payment with allocation across bills
19. `src/features/secured-advances/secured-advances-page.tsx` — Advance financing

### Work Tracking
20. `src/features/measurements/measurements-page.tsx` — Progress measurements
21. `src/features/work-done/work-done-page.tsx` — Completed work records

### Documents & Audit
22. `src/features/documents/documents-page.tsx` — Document upload/download, pagination, entity filter
23. `src/features/audit/audit-page.tsx` — Audit log viewer with date/entity/action filters, export

### Reports & Analytics
24. `src/features/reports/reports-page.tsx` — Multi-report dashboard with charts, filters, exports
25. `src/features/reports/contract-drilldown-page.tsx` — Contract detail drilldown

### Other Modules
26. `src/features/dashboard/dashboard-page.tsx` — Dashboard with stats, charts, links
27. `src/features/ai-boundary/ai-boundary-page.tsx` — AI configuration
28. `src/features/admin/users-page.tsx` — User management
29. `src/features/auth/login-page.tsx` — Login form
30. `src/features/auth/forgot-password-page.tsx` — Forgot password
31. `src/features/auth/reset-password-page.tsx` — Reset password confirm

---

## PART 5: Recommended Test File Structure & Template

### Directory Structure
```
frontend/src/features/materials/
  materials-page.tsx
  materials-page.test.tsx          ← Main unit test file
  materials-helpers.ts
  materials-helpers.test.ts        ← Already exists
  __mocks__/
    api.ts                         ← Mocked API functions
    fixtures.ts                    ← Test data fixtures
```

### Test File Template

**`src/features/materials/materials-page.test.tsx`:**
```typescript
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, within, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import MaterialsPage from './materials-page.tsx';
import * as materialsApi from '@/api/materials';
import { useAuth } from '@/app/providers/auth-provider';
import { mockMaterials, mockCompanies, mockProjects } from '#/__mocks__/fixtures';

// Mocks
vi.mock('@/api/materials');
vi.mock('@/app/providers/auth-provider');

describe('MaterialsPage', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    
    vi.mocked(useAuth).mockReturnValue({
      accessToken: 'test-token',
      user: { 
        id: 1, 
        email: 'test@example.com',
        permissions: ['material:read', 'material:create', 'material:update', 'material:delete'],
      },
    });
  });

  afterEach(() => vi.clearAllMocks());

  const renderPage = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MaterialsPage />
      </QueryClientProvider>
    );
  };

  describe('Loading & Error States', () => {
    it('should render page skeleton while loading', () => {
      vi.mocked(materialsApi.fetchMaterials).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );
      renderPage();
      expect(screen.getByRole('article')).toHaveClass('animate-pulse'); // Skeleton class
    });

    it('should render empty state when no materials', async () => {
      vi.mocked(materialsApi.fetchMaterials).mockResolvedValueOnce([]);
      renderPage();
      await waitFor(() => {
        expect(screen.getByText(/no materials found/i)).toBeInTheDocument();
      });
    });

    it('should render error state on API failure', async () => {
      const error = new Error('API Error');
      vi.mocked(materialsApi.fetchMaterials).mockRejectedValueOnce(error);
      renderPage();
      await waitFor(() => {
        expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
      });
    });

    it('should refetch data on retry button click', async () => {
      vi.mocked(materialsApi.fetchMaterials)
        .mockRejectedValueOnce(new Error('Error'))
        .mockResolvedValueOnce(mockMaterials);
      renderPage();
      
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
      });
      
      const retryButton = screen.getByRole('button', { name: /retry/i });
      await userEvent.click(retryButton);
      
      await waitFor(() => {
        expect(screen.getByText('Red Brick')).toBeInTheDocument();
      });
    });
  });

  describe('Table Rendering', () => {
    it('should render table with materials data', async () => {
      vi.mocked(materialsApi.fetchMaterials).mockResolvedValueOnce(mockMaterials);
      renderPage();
      
      await waitFor(() => {
        expect(screen.getByText('Red Brick')).toBeInTheDocument();
        expect(screen.getByText('Sand')).toBeInTheDocument();
      });
    });

    it('should display correct columns', async () => {
      vi.mocked(materialsApi.fetchMaterials).mockResolvedValueOnce(mockMaterials);
      renderPage();
      
      await waitFor(() => {
        const table = screen.getByRole('table');
        expect(within(table).getByText('Item Code')).toBeInTheDocument();
        expect(within(table).getByText('Item Name')).toBeInTheDocument();
        expect(within(table).getByText('Stock')).toBeInTheDocument();
      });
    });

    it('should format currency and numeric values correctly', async () => {
      vi.mocked(materialsApi.fetchMaterials).mockResolvedValueOnce([
        { id: 1, item_name: 'Cement', default_rate: 500.00, current_stock: 1234.5, ... },
      ]);
      renderPage();
      
      await waitFor(() => {
        expect(screen.getByText('₹500')).toBeInTheDocument();
        expect(screen.getByText('1,234.5')).toBeInTheDocument();
      });
    });
  });

  describe('Search Functionality', () => {
    beforeEach(() => {
      vi.mocked(materialsApi.fetchMaterials).mockResolvedValueOnce(mockMaterials);
    });

    it('should filter materials by search term', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('Red Brick')).toBeInTheDocument();
      });
      
      const searchInput = screen.getByPlaceholderText(/search/i);
      await userEvent.type(searchInput, 'Red');
      
      // Wait for debounce
      await waitFor(() => {
        expect(screen.getByText('Red Brick')).toBeInTheDocument();
        expect(screen.queryByText('Sand')).not.toBeInTheDocument();
      }, { timeout: 500 });
    });

    it('should be case-insensitive', async () => {
      renderPage();
      await waitFor(() => expect(screen.getByText('Red Brick')).toBeInTheDocument());
      
      await userEvent.type(screen.getByPlaceholderText(/search/i), 'red');
      await waitFor(() => {
        expect(screen.getByText('Red Brick')).toBeInTheDocument();
      }, { timeout: 500 });
    });

    it('should show empty state when no search matches', async () => {
      renderPage();
      await waitFor(() => expect(screen.getByText('Red Brick')).toBeInTheDocument());
      
      await userEvent.type(screen.getByPlaceholderText(/search/i), 'xyz123');
      await waitFor(() => {
        expect(screen.getByText(/no materials found/i)).toBeInTheDocument();
      }, { timeout: 500 });
    });

    it('should focus search on slash key', async () => {
      renderPage();
      const searchInput = await screen.findByPlaceholderText(/search/i);
      
      await userEvent.keyboard('/');
      expect(searchInput).toHaveFocus();
    });
  });

  describe('Filter Functionality', () => {
    beforeEach(() => {
      vi.mocked(materialsApi.fetchMaterials).mockResolvedValueOnce(mockMaterials);
    });

    it('should filter by category', async () => {
      renderPage();
      await waitFor(() => expect(screen.getByText('Red Brick')).toBeInTheDocument());
      
      const categorySelect = screen.getByDisplayValue('All');
      await userEvent.selectOptions(categorySelect, 'masonry');
      
      await waitFor(() => {
        expect(screen.getByText('Red Brick')).toBeInTheDocument();
        expect(screen.queryByText('Cement')).not.toBeInTheDocument();
      });
    });

    it('should combine search and filter', async () => {
      renderPage();
      await waitFor(() => expect(screen.getByText('Red Brick')).toBeInTheDocument());
      
      // Set filter
      await userEvent.selectOptions(screen.getByDisplayValue('All'), 'masonry');
      
      // Set search
      await userEvent.type(screen.getByPlaceholderText(/search/i), 'Red');
      
      await waitFor(() => {
        expect(screen.getByText('Red Brick')).toBeInTheDocument();
      }, { timeout: 500 });
    });
  });

  describe('Create Material', () => {
    beforeEach(() => {
      vi.mocked(materialsApi.fetchMaterials).mockResolvedValue(mockMaterials);
      vi.mocked(materialsApi.createMaterial).mockResolvedValueOnce({
        id: 999,
        item_code: 'PAINT',
        item_name: 'Paint',
        unit: 'ltr',
        default_rate: 300,
        current_stock: 0,
        is_active: true,
        ...
      });
    });

    it('should open create form on Create button click', async () => {
      renderPage();
      const createButton = await screen.findByRole('button', { name: /create/i });
      await userEvent.click(createButton);
      
      await waitFor(() => {
        expect(screen.getByLabelText(/item code/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/item name/i)).toBeInTheDocument();
      });
    });

    it('should validate required fields', async () => {
      renderPage();
      const createButton = await screen.findByRole('button', { name: /create/i });
      await userEvent.click(createButton);
      
      // Try submit without filling
      const submitButton = await screen.findByRole('button', { name: /submit|save/i });
      await userEvent.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/item code is required/i)).toBeInTheDocument();
      });
    });

    it('should submit create form and refresh data', async () => {
      renderPage();
      const createButton = await screen.findByRole('button', { name: /create/i });
      await userEvent.click(createButton);
      
      // Fill form
      await userEvent.type(screen.getByLabelText(/item code/i), 'PAINT');
      await userEvent.type(screen.getByLabelText(/item name/i), 'Paint');
      
      const submitButton = await screen.findByRole('button', { name: /submit|save/i });
      await userEvent.click(submitButton);
      
      // Verify API call
      await waitFor(() => {
        expect(vi.mocked(materialsApi.createMaterial)).toHaveBeenCalledWith(
          'test-token',
          expect.objectContaining({ item_code: 'PAINT', item_name: 'Paint' })
        );
      });
      
      // Verify success message
      expect(screen.getByText(/created successfully/i)).toBeInTheDocument();
    });

    it('should show error on create failure', async () => {
      vi.mocked(materialsApi.createMaterial).mockRejectedValueOnce(
        new Error('Item code already exists')
      );
      
      renderPage();
      const createButton = await screen.findByRole('button', { name: /create/i });
      await userEvent.click(createButton);
      
      await userEvent.type(screen.getByLabelText(/item code/i), 'DUPLICATE');
      const submitButton = await screen.findByRole('button', { name: /submit|save/i });
      await userEvent.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/already exists/i)).toBeInTheDocument();
      });
    });

    it('should close form on success', async () => {
      renderPage();
      const createButton = await screen.findByRole('button', { name: /create/i });
      await userEvent.click(createButton);
      
      await userEvent.type(screen.getByLabelText(/item code/i), 'PAINT');
      await userEvent.type(screen.getByLabelText(/item name/i), 'Paint');
      
      const submitButton = await screen.findByRole('button', { name: /submit|save/i });
      await userEvent.click(submitButton);
      
      await waitFor(() => {
        expect(screen.queryByLabelText(/item code/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Edit Material', () => {
    beforeEach(() => {
      vi.mocked(materialsApi.fetchMaterials).mockResolvedValue(mockMaterials);
      vi.mocked(materialsApi.updateMaterial).mockResolvedValueOnce({
        ...mockMaterials[0],
        item_name: 'Red Brick (Updated)',
      });
    });

    it('should open edit form on table row Edit click', async () => {
      renderPage();
      await waitFor(() => {
        const editButtons = screen.getAllByRole('button', { name: /edit/i });
        expect(editButtons.length).toBeGreaterThan(0);
      });
      
      const editButton = screen.getAllByRole('button', { name: /edit/i })[0];
      await userEvent.click(editButton);
      
      await waitFor(() => {
        const itemCodeInput = screen.getByLabelText(/item code/i);
        expect(itemCodeInput).toHaveValue(mockMaterials[0].item_code);
      });
    });

    it('should update material on form submit', async () => {
      renderPage();
      const editButton = await screen.findByRole('button', { name: /edit/i });
      await userEvent.click(editButton);
      
      const itemNameInput = await screen.findByLabelText(/item name/i);
      await userEvent.clear(itemNameInput);
      await userEvent.type(itemNameInput, 'Red Brick (Updated)');
      
      const submitButton = screen.getByRole('button', { name: /submit|save/i });
      await userEvent.click(submitButton);
      
      await waitFor(() => {
        expect(vi.mocked(materialsApi.updateMaterial)).toHaveBeenCalled();
        expect(screen.getByText(/updated successfully/i)).toBeInTheDocument();
      });
    });
  });

  describe('Permission Gates', () => {
    it('should hide Create button when permission denied', async () => {
      vi.mocked(useAuth).mockReturnValue({
        accessToken: 'test-token',
        user: { id: 1, permissions: ['material:read'] }, // No create
      });
      
      vi.mocked(materialsApi.fetchMaterials).mockResolvedValueOnce(mockMaterials);
      renderPage();
      
      await waitFor(() => {
        expect(screen.queryByRole('button', { name: /create/i })).not.toBeInTheDocument();
      });
    });

    it('should hide Edit buttons when permission denied', async () => {
      vi.mocked(useAuth).mockReturnValue({
        accessToken: 'test-token',
        user: { id: 1, permissions: ['material:read'] }, // No update
      });
      
      vi.mocked(materialsApi.fetchMaterials).mockResolvedValueOnce(mockMaterials);
      renderPage();
      
      await waitFor(() => {
        expect(screen.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument();
      });
    });
  });

  describe('Export', () => {
    it('should export materials to CSV', async () => {
      const mockBlob = new Blob(['mock csv content']);
      vi.mocked(materialsApi.exportMaterials).mockResolvedValueOnce(mockBlob);
      
      vi.mocked(materialsApi.fetchMaterials).mockResolvedValueOnce(mockMaterials);
      renderPage();
      
      const exportButton = await screen.findByRole('button', { name: /export/i });
      await userEvent.click(exportButton);
      
      await waitFor(() => {
        expect(vi.mocked(materialsApi.exportMaterials)).toHaveBeenCalledWith(
          'test-token',
          expect.any(Object)
        );
      });
    });
  });

  describe('Stat Cards', () => {
    it('should display correct material counts', async () => {
      vi.mocked(materialsApi.fetchMaterials).mockResolvedValueOnce(mockMaterials);
      renderPage();
      
      await waitFor(() => {
        expect(screen.getByText(/\b\d+ materials?/i)).toBeInTheDocument();
      });
    });
  });
});
```

---

## PART 6: Testing Priorities & Rollout Plan

### Tier 1: Critical Path (Week 1)
Start with high-impact, frequently used pages:
1. `materials-page` — Most-used master, represents CRUD pattern
2. `vendors-page` — Simpler CRUD, good second example
3. `material-requisitions-page` — Represents multi-line workflow pattern

### Tier 2: Finance Workflows (Week 2–3)
1. `ra-bills-page` — Complex multi-step approval
2. `payments-page` — Complex allocation logic
3. `labour-bills-page` — Labour workflow with calculations

### Tier 3: Remaining Operations (Week 3–4)
1. `material-receipts`, `material-issues`
2. `labour-advances`, `labour-attendance`

### Tier 4: Reports & Read-only (Week 5)
1. `reports-page`
2. `audit-page`
3. `dashboard-page`

### Tier 5: Auth & Admin (Week 5–6)
1. `login-page`
2. `admin/users-page`

---

## PART 7: Common Pitfalls & Best Practices

### Pitfall 1: Not Waiting for Debounce
❌ Don't:
```typescript
await userEvent.type(searchInput, 'Red');
expect(screen.getByText('Red Brick')).toBeInTheDocument(); // Too fast
```

✅ Do:
```typescript
await userEvent.type(searchInput, 'Red');
await waitFor(() => {
  expect(screen.getByText('Red Brick')).toBeInTheDocument();
}, { timeout: 500 });
```

### Pitfall 2: Mocking vs Spying
❌ Don't:
```typescript
vi.mock('@/api/materials', () => ({})); // Mocking entire module breaks types
```

✅ Do:
```typescript
vi.mock('@/api/materials');
vi.mocked(fetchMaterials).mockResolvedValueOnce([...]);
```

### Pitfall 3: QueryClient Not Cleared Between Tests
❌ Don't:
```typescript
describe('Page', () => {
  it('test 1', () => { /* uses queryClient */ });
  it('test 2', () => { /* uses same queryClient */ });
});
```

✅ Do:
```typescript
describe('Page', () => {
  let queryClient: QueryClient;
  
  beforeEach(() => {
    queryClient = new QueryClient({ ... });
  });
});
```

### Pitfall 4: Not Waiting for Queries to Resolve
❌ Don't:
```typescript
renderPage();
const button = screen.getByRole('button'); // Might not exist yet
```

✅ Do:
```typescript
renderPage();
const button = await screen.findByRole('button'); // Waits for query
```

### Pitfall 5: Testing Implementation Details
❌ Don't:
```typescript
expect(component.state.editingId).toBe(1); // Testing internal state
```

✅ Do:
```typescript
expect(screen.getByLabelText(/item name/i)).toBeInTheDocument(); // Test visible output
```

---

## Summary

**31 pages** require unit tests. All follow consistent patterns:
1. TanStack Query for server state
2. React Hook Form + Zod for forms
3. Local state for UI (filters, pagination, search)
4. PermissionGate for access control
5. Vitest + React Testing Library for testing

Start with **Tier 1 pages** (materials, vendors, requisitions) to establish patterns, then roll out systematically. Use the provided template to reduce setup time per test file.
