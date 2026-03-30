# Frontend Blueprint

## Goal

Build a production-grade frontend for this Construction ERP that matches the current backend modules, permissions, workflows, and operational complexity.

This blueprint assumes:

- backend stays at `/backend`
- new frontend will live at `/frontend`
- frontend talks to backend at `/api/v1`
- RBAC, workflow transitions, audit visibility, and backend validation remain authoritative

## Recommended Tech Stack

### Core app stack

- React
- TypeScript with `strict` mode
- Vite
- TanStack Router
- TanStack Query

### Forms and validation

- React Hook Form
- Zod

### UI and styling

- Tailwind CSS
- headless component patterns for dialogs, menus, comboboxes, popovers, and accessibility
- custom design system on top of utility classes

### Data UX

- TanStack Table for standard data grids
- specialized operational grids for attendance/muster and line-item entry flows

### Charts and analytics

- Recharts for dashboard charts

### Testing

- Vitest
- React Testing Library
- Playwright

### Quality and tooling

- ESLint
- Prettier
- Husky + lint-staged

## Why this stack

- Vite gives fast local iteration and fits the current backend deployment pattern well.
- TanStack Router is a strong fit because the app needs nested layouts, route guards, typed params, and search-param-driven filters.
- TanStack Query fits this backend because almost every screen is server-state-heavy: lists, filters, summaries, workflows, audits, and drill-downs.
- React Hook Form + Zod is the right combo for large ERP forms with repeatable item rows and strong server validation mapping.
- Tailwind is a good fit because the app will need many operational screens, dense layouts, and a custom design system, not a generic dashboard theme.

## Top-Level Folder Structure

```text
frontend/
  public/
    favicon.svg
    manifest.webmanifest

  src/
    app/
      providers/
        app-provider.tsx
        auth-provider.tsx
        query-provider.tsx
        theme-provider.tsx
      router/
        index.tsx
        route-tree.ts
      layouts/
        auth-layout.tsx
        app-shell-layout.tsx
        dashboard-layout.tsx
        module-layout.tsx
      store/
        session-store.ts
        ui-store.ts
      styles/
        globals.css
        tokens.css
        utilities.css

    routes/
      __root.tsx
      index.tsx
      login.tsx
      unauthorized.tsx

      app/
        index.tsx
        dashboard.tsx

        admin/
          users.tsx
          audit-logs.tsx
          ai-boundary.tsx

        masters/
          companies.tsx
          projects.tsx
          vendors.tsx
          contracts.tsx
          boq.tsx

        materials/
          index.tsx
          list.tsx
          create.tsx
          $materialId.tsx
          stock-summary.tsx
          stock-ledger.tsx
          requisitions/
            index.tsx
            create.tsx
            $requisitionId.tsx
          receipts/
            index.tsx
            create.tsx
            $receiptId.tsx
          issues/
            index.tsx
            create.tsx
            $issueId.tsx
          adjustments/
            index.tsx
            create.tsx
            $adjustmentId.tsx

        labour/
          index.tsx
          contractors/
            index.tsx
            create.tsx
            $contractorId.tsx
          workers/
            index.tsx
            create.tsx
            $labourId.tsx
          attendance/
            index.tsx
            create.tsx
            $attendanceId.tsx
          productivity/
            index.tsx
            create.tsx
            $productivityId.tsx
          bills/
            index.tsx
            create.tsx
            $billId.tsx
          advances/
            index.tsx
            create.tsx
            $advanceId.tsx

        finance/
          index.tsx
          measurements/
            index.tsx
            create.tsx
            $measurementId.tsx
          work-done/
            index.tsx
          ra-bills/
            index.tsx
            create.tsx
            $billId.tsx
          secured-advances/
            index.tsx
            create.tsx
            $advanceId.tsx
          payments/
            index.tsx
            create.tsx
            $paymentId.tsx
          deductions/
            index.tsx

        documents/
          index.tsx
          $documentId.tsx

        workflows/
          index.tsx

    modules/
      auth/
      dashboard/
      admin/
      masters/
      materials/
      labour/
      finance/
      documents/
      workflows/

    components/
      ui/
        button.tsx
        input.tsx
        select.tsx
        textarea.tsx
        dialog.tsx
        drawer.tsx
        sheet.tsx
        combobox.tsx
        table.tsx
        tabs.tsx
        badge.tsx
        tooltip.tsx
        pagination.tsx
        skeleton.tsx

      data-display/
        summary-card.tsx
        status-badge.tsx
        amount.tsx
        quantity.tsx
        date-chip.tsx
        entity-link.tsx

      tables/
        data-grid.tsx
        filter-bar.tsx
        row-actions.tsx
        column-toggle.tsx
        empty-state.tsx

      forms/
        form-section.tsx
        field-error.tsx
        line-items-editor.tsx
        server-error-banner.tsx
        submit-bar.tsx

      workflow/
        approval-timeline.tsx
        status-transition-card.tsx
        workflow-action-bar.tsx
        audit-drawer.tsx

      shell/
        app-sidebar.tsx
        app-header.tsx
        breadcrumb.tsx
        permission-gate.tsx
        project-switcher.tsx
        global-search.tsx

    api/
      client.ts
      interceptors.ts
      query-client.ts
      errors.ts
      auth.ts
      dashboard.ts
      companies.ts
      projects.ts
      vendors.ts
      contracts.ts
      boq.ts
      materials.ts
      material-requisitions.ts
      material-receipts.ts
      material-issues.ts
      stock-ledger.ts
      stock-adjustments.ts
      labours.ts
      labour-contractors.ts
      labour-attendance.ts
      labour-productivity.ts
      labour-bills.ts
      labour-advances.ts
      measurements.ts
      work-done.ts
      ra-bills.ts
      deductions.ts
      secured-advances.ts
      payments.ts
      documents.ts
      audit-logs.ts
      workflows.ts
      ai-boundary.ts

    hooks/
      use-auth.ts
      use-permissions.ts
      use-project-context.ts
      use-server-table.ts
      use-line-items.ts
      use-confirmation.ts

    lib/
      auth.ts
      permissions.ts
      constants.ts
      formatters.ts
      dates.ts
      numbers.ts
      status-maps.ts
      route-helpers.ts
      download.ts

    types/
      api.ts
      auth.ts
      common.ts
      materials.ts
      labour.ts
      finance.ts
      documents.ts

    test/
      setup.ts
      factories/
      mocks/

  .env.example
  index.html
  package.json
  tsconfig.json
  vite.config.ts
  vitest.config.ts
  playwright.config.ts
```

## Frontend Architecture Rules

### 1. API contract-first

Frontend modules should mirror backend modules:

- one API file per backend endpoint group
- one route group per business module
- one type file per domain
- one query-key namespace per module

### 2. Server-state heavy, client-state light

Use TanStack Query for:

- lists
- details
- filters
- dashboard summaries
- dependent dropdowns
- workflow actions

Use local component state only for:

- dialog open/close
- local row editing
- temporary UI preferences

### 3. Permission-first UI

The frontend must not assume visibility equals authority.

Every screen should support:

- route-level permission gate
- widget/button-level permission gate
- graceful unauthorized state
- backend 401/403 error mapping

### 4. Workflow-safe UX

UI must reflect backend truth:

- only show valid workflow actions
- disable actions while mutation is pending
- prevent duplicate submit clicks
- show audit trail or status timeline on every approval-heavy screen

## Page-by-Page Construction ERP Map

## A. Foundation Pages

### 1. `/login`

Purpose:

- login to backend via `/api/v1/auth/login`

UI:

- email
- password
- login CTA
- backend error banner

### 2. `/app`

Purpose:

- authenticated shell redirect entry

UI:

- route redirect based on role and recent context

### 3. `/app/dashboard`

Purpose:

- executive and operational summary

Widgets:

- project count
- contract value summary
- material stock highlights
- labour attendance highlights
- RA bill and payment summary
- pending approvals
- quick actions

## B. Admin Pages

### 4. `/app/admin/users`

Purpose:

- manage backend users

UI:

- users table
- create user modal
- edit user drawer
- active/inactive state

### 5. `/app/admin/audit-logs`

Purpose:

- inspect create/update/approval transitions

UI:

- filter panel
- audit table
- record detail drawer

### 6. `/app/admin/ai-boundary`

Purpose:

- inspect current AI usage boundary from backend

UI:

- AI mode card
- blocked operations list
- allowed operations list
- evaluate operation form

## C. Master Data Pages

### 7. `/app/masters/companies`

Purpose:

- company master management

### 8. `/app/masters/projects`

Purpose:

- project listing and project detail

UI:

- project filters
- project status
- contract/material/labour shortcuts

### 9. `/app/masters/vendors`

Purpose:

- vendor master

### 10. `/app/masters/contracts`

Purpose:

- contract registry and detail

UI:

- contract status
- original vs revised value
- linked project and vendor

### 11. `/app/masters/boq`

Purpose:

- BOQ master and rate items

## D. Material Module Pages

### 12. `/app/materials/list`

Purpose:

- material master list

UI:

- stock cards
- material table
- reorder warning
- quick filters by category/project

### 13. `/app/materials/create`

Purpose:

- create material master

### 14. `/app/materials/$materialId`

Purpose:

- material detail page

Tabs:

- overview
- stock history
- project linkage
- requisition usage
- receipt usage
- issue usage

### 15. `/app/materials/stock-summary`

Purpose:

- project-wise or company-wise stock summary

UI:

- grouped stock cards
- low stock markers
- export

### 16. `/app/materials/stock-ledger`

Purpose:

- full stock ledger drill-down

UI:

- date filters
- material filter
- project filter
- qty in / qty out / balance table
- reference link to receipt/issue/adjustment

### 17. `/app/materials/requisitions`

Purpose:

- requisition listing

### 18. `/app/materials/requisitions/create`

Purpose:

- create requisition with item rows

UI:

- project selector
- requested-by
- line-items editor
- draft vs submit actions

### 19. `/app/materials/requisitions/$requisitionId`

Purpose:

- requisition detail and workflow

UI:

- header summary
- items
- approval actions
- issue progress
- audit timeline

### 20. `/app/materials/receipts`

Purpose:

- goods receipt list

### 21. `/app/materials/receipts/create`

Purpose:

- create vendor stock receipt

UI:

- vendor selector
- project selector
- receipt date
- item rows
- totals

### 22. `/app/materials/receipts/$receiptId`

Purpose:

- receipt detail and stock impact

### 23. `/app/materials/issues`

Purpose:

- material issue list

### 24. `/app/materials/issues/create`

Purpose:

- issue stock to project/site/activity

UI:

- project selector
- optional contract
- site name
- activity name
- item rows with available stock

### 25. `/app/materials/issues/$issueId`

Purpose:

- issue detail page

### 26. `/app/materials/adjustments`

Purpose:

- stock adjustment list

### 27. `/app/materials/adjustments/create`

Purpose:

- post damage/wastage/correction adjustments

### 28. `/app/materials/adjustments/$adjustmentId`

Purpose:

- adjustment detail page

## E. Labour Module Pages

### 29. `/app/labour/contractors`

Purpose:

- labour contractor or gang registry

### 30. `/app/labour/contractors/create`

Purpose:

- create contractor/gang

### 31. `/app/labour/contractors/$contractorId`

Purpose:

- contractor detail

Tabs:

- workers
- attendance
- bills
- advances

### 32. `/app/labour/workers`

Purpose:

- labour master list

### 33. `/app/labour/workers/create`

Purpose:

- create labour entry

### 34. `/app/labour/workers/$labourId`

Purpose:

- labour detail

### 35. `/app/labour/attendance`

Purpose:

- attendance/muster list

### 36. `/app/labour/attendance/create`

Purpose:

- create muster with fast grid UX

UI:

- project
- contractor
- date
- labour rows
- attendance status
- overtime
- remarks

### 37. `/app/labour/attendance/$attendanceId`

Purpose:

- attendance detail + submit/approve workflow

### 38. `/app/labour/productivity`

Purpose:

- labour productivity list

### 39. `/app/labour/productivity/create`

Purpose:

- create productivity entry

### 40. `/app/labour/productivity/$productivityId`

Purpose:

- productivity detail

### 41. `/app/labour/bills`

Purpose:

- labour bill list

### 42. `/app/labour/bills/create`

Purpose:

- create labour bill from approved attendance

UI:

- period range
- contractor
- attendance selection
- gross/deduction/net summary

### 43. `/app/labour/bills/$billId`

Purpose:

- bill detail with approval and paid state

### 44. `/app/labour/advances`

Purpose:

- labour advance list

### 45. `/app/labour/advances/create`

Purpose:

- create advance record

### 46. `/app/labour/advances/$advanceId`

Purpose:

- advance detail with recoveries

## F. Finance and Execution Pages

### 47. `/app/finance/measurements`

Purpose:

- measurement list

### 48. `/app/finance/measurements/create`

Purpose:

- create measurement against BOQ

### 49. `/app/finance/measurements/$measurementId`

Purpose:

- measurement detail and status

### 50. `/app/finance/work-done`

Purpose:

- work-done listing and progress view

### 51. `/app/finance/ra-bills`

Purpose:

- RA bill list

### 52. `/app/finance/ra-bills/create`

Purpose:

- create/generate RA bill

### 53. `/app/finance/ra-bills/$billId`

Purpose:

- RA bill detail with workflow and deductions

### 54. `/app/finance/secured-advances`

Purpose:

- secured advance list

### 55. `/app/finance/secured-advances/create`

Purpose:

- issue secured advance

### 56. `/app/finance/secured-advances/$advanceId`

Purpose:

- secured advance recovery history

### 57. `/app/finance/payments`

Purpose:

- payment list

### 58. `/app/finance/payments/create`

Purpose:

- create payment

### 59. `/app/finance/payments/$paymentId`

Purpose:

- payment detail, approval, release, allocation

### 60. `/app/finance/deductions`

Purpose:

- deduction visibility and audit

## G. Documents and Workflow Pages

### 61. `/app/documents`

Purpose:

- document list and upload history

### 62. `/app/documents/$documentId`

Purpose:

- document detail, versions, download actions

### 63. `/app/workflows`

Purpose:

- global workflow visibility across modules

UI:

- pending approvals queue
- workflow definitions
- entity transitions

## Navigation Model

```text
Dashboard
Masters
  Companies
  Projects
  Vendors
  Contracts
  BOQ
Materials
  Materials
  Requisitions
  Receipts
  Issues
  Stock Adjustments
  Stock Ledger
Labour
  Contractors
  Labour Master
  Attendance
  Productivity
  Labour Bills
  Labour Advances
Finance
  Measurements
  Work Done
  RA Bills
  Secured Advances
  Payments
  Deductions
Documents
Admin
  Users
  Audit Logs
  AI Boundary
```

## Frontend Build Order

### Phase 1. Core foundation

- app scaffold
- routing
- auth
- query client
- app shell
- permission gate
- common table/form primitives

### Phase 2. Master data

- dashboard
- companies
- projects
- vendors
- contracts
- BOQ

### Phase 3. Material module

- materials
- requisitions
- stock ledger
- receipts
- issues
- stock adjustments

### Phase 4. Labour module

- labour contractors
- labour master
- attendance
- productivity
- labour bills
- labour advances

### Phase 5. Finance module

- measurements
- work done
- RA bills
- secured advances
- payments
- deductions

### Phase 6. Admin and polish

- audit logs
- AI boundary view
- document UX
- exports
- mobile polish
- E2E tests

## What a world-class frontend developer would avoid

- random page-by-page coding without shell and routing foundation
- global state for server data
- weak permission handling
- generic admin template dependency
- duplicating form/table logic in every page
- backend workflow assumptions in frontend
- hiding validation errors instead of mapping them cleanly
- building desktop-only ERP screens

## Final recommendation

If you want the strongest long-term result for this repo:

1. Create `/frontend`
2. Scaffold React + TypeScript + Vite
3. Add TanStack Router + TanStack Query + Tailwind + React Hook Form + Zod
4. Build the app shell and permission system first
5. Then implement pages in the same order as the backend modules
