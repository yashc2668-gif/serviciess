---
description: "Implement Phase 6 testing and quality hardening for M2N Construction ERP - backend coverage, frontend unit/page tests, API contracts, E2E, load, visual, and accessibility gates"
agent: "agent"
argument-hint: "Task number (e.g. 6.1) or keyword (coverage, component tests, page tests, e2e, contract, load, visual, accessibility)"
---

# Phase 6 - Testing & Quality

You are implementing enterprise-grade testing, regression protection, and quality gates for the **M2N Construction ERP** monorepo. Follow the project conventions in [copilot-instructions.md](../../.github/copilot-instructions.md).

## Execution Mode

This phase must be delivered **sequentially** from `6.1` through `6.8`.

- When the user says `start` or does not specify a task number, begin with `6.1`.
- Do not jump to the next task until the current task is implemented, tested, and wired into CI or documented as blocked.
- Treat each task as production hardening work: implementation, tests, CI integration, and developer workflow updates must land together.

## Current State

- **Backend tests exist**, but CI only runs `python -m unittest discover app/tests -v`; there is no coverage gate, no XML/HTML coverage artifact, and no package-level coverage target.
- The backend currently contains **37 service modules**, **4 calculators**, and **4 workflow modules**:
  - Services: `ai_boundary_service`, `audit_service`, `auth_service`, `boq_service`, `company_scope_service`, `company_service`, `concurrency_service`, `contract_service`, `dashboard_service`, `deduction_service`, `document_service`, `financial_archive_service`, `idempotency_service`, `inventory_service`, `labour_advance_service`, `labour_attendance_service`, `labour_bill_service`, `labour_contractor_service`, `labour_productivity_service`, `labour_service`, `material_issue_service`, `material_receipt_service`, `material_requisition_service`, `material_service`, `material_stock_adjustment_service`, `measurement_service`, `payment_service`, `pdf_service`, `project_service`, `ra_bill_service`, `reporting_service`, `secured_advance_service`, `stock_adjustment_service`, `user_service`, `vendor_service`, `workflow_service`, `work_done_service`.
  - Calculators: `deduction_calculator`, `progress_calculator`, `ra_bill_calculator`, `secured_advance_calculator`.
  - Workflows: `contract_revision_flow`, `payment_approval`, `ra_bill_approval`, `requisition_approval`.
- The frontend has **11 UI primitives** in `frontend/src/components/ui/`, but there are currently **no dedicated UI primitive tests**.
- The frontend has only **10 unit tests**, mostly for helpers and providers; there are **no page-level test suites** for the 30 feature pages.
- Playwright is configured, but there are only **4 E2E specs**: `finance-permissions`, `material-labour-permissions`, `payments`, `ra-bills`.
- There is **no API contract generation/check**, **no load testing toolchain**, **no visual regression baseline**, and **no axe-core accessibility gate**.
- Frontend CI currently runs `lint`, `vitest`, `build`, and the existing Playwright suite. Backend CI does not enforce coverage thresholds.

## Task Manifest

| #   | Task                        | Layer    | Priority | Status      |
|-----|-----------------------------|----------|----------|-------------|
| 6.1 | Backend test coverage >=80% | Backend  | CRITICAL | Not started |
| 6.2 | Frontend component tests    | Frontend | HIGH     | Not started |
| 6.3 | Frontend page tests         | Frontend | HIGH     | Not started |
| 6.4 | E2E coverage                | Frontend | HIGH     | Not started |
| 6.5 | API contract tests          | Both     | HIGH     | Not started |
| 6.6 | Load/stress testing         | Backend  | MEDIUM   | Not started |
| 6.7 | Visual regression           | Frontend | MEDIUM   | Not started |
| 6.8 | Accessibility audit         | Frontend | MEDIUM   | Not started |

---

## 6.1 - Backend Test Coverage >=80%

**Goal**: Reach and enforce at least `80%` backend coverage for service, calculator, and workflow logic, with deterministic tests and CI reporting.

### Requirements
1. Add a coverage toolchain to the backend:
   - Add `coverage[toml]>=7.6` to `backend/requirements.txt`.
   - Add backend coverage configuration in `pyproject.toml` or `.coveragerc`.
   - Scope coverage reporting to `app/services`, `app/calculators`, `app/workflows`, and other business-critical modules touched by service tests.
2. Create or expand unit tests so every backend service module, calculator, and workflow has direct test coverage.
3. Add shared backend test helpers/factories where repetition is high:
   - Reusable authenticated client setup.
   - Deterministic DB fixtures for company/project/vendor/contract/payment flows.
   - Mock helpers for external integrations such as storage, email, SMS, and background tasks.
4. Update CI and local commands:
   - `coverage run -m unittest discover app/tests -v`
   - `coverage report --fail-under=80`
   - `coverage xml` for CI artifacts.
5. Make coverage a hard gate in backend CI.
6. Do not inflate coverage with trivial assertions; tests must exercise business rules, validation, permission logic, state transitions, and edge cases.
7. Prefer unit-style service tests over broad end-to-end backend tests when the same rule can be validated more precisely at the service layer.

### Files to touch
- `backend/requirements.txt`
- `backend/pyproject.toml` or `backend/.coveragerc` (new)
- `backend/app/tests/`
- `backend/app/tests/helpers.py`
- `.github/workflows/backend-ci.yml`
- `backend/README.md`

---

## 6.2 - Frontend Component Tests

**Goal**: Add reliable unit tests for every UI primitive so shared components become a stable platform instead of an untested dependency layer.

### Requirements
1. Create dedicated tests for all UI primitives in `frontend/src/components/ui/`:
   - `badge`
   - `button`
   - `card`
   - `data-table`
   - `date-picker`
   - `dialog`
   - `drawer`
   - `page-header`
   - `password-strength-indicator`
   - `stat-card`
   - `tabs`
2. Every component test should cover the behaviors that matter for consumers:
   - render and default state
   - variant/state styling contracts where relevant
   - keyboard interactions for focusable widgets
   - disabled/loading states where applicable
   - callbacks and emitted events
   - accessibility roles, labels, and focus trapping for overlays
3. Add shared frontend test utilities:
   - `renderWithProviders()`
   - router/query provider wrappers where needed
   - stable mocks for `ResizeObserver`, `matchMedia`, `IntersectionObserver`, and portal behavior if required by Radix-like components
4. Keep component tests fast and deterministic; avoid testing CSS implementation details unless they are part of a public variant contract.

### Files to touch
- `frontend/src/components/ui/*.test.tsx` (new)
- `frontend/src/test/setup.ts`
- `frontend/src/test/` (new helpers if needed)
- `frontend/package.json`

---

## 6.3 - Frontend Page Tests

**Goal**: Add page-level tests for each feature page so rendering, primary interactions, data states, and form flows are covered without relying only on browser E2E.

### Requirements
1. Create page tests for the current 30 feature pages under `frontend/src/features/`.
2. For each page, test the meaningful equivalents of:
   - initial render
   - loading state
   - empty state or no-results state
   - search and filter behavior when the page supports it
   - form submit or primary mutation flow when the page supports it
   - backend error state and retry affordance
3. Where a page does not have a search/filter/form, test its primary user interaction instead of adding meaningless assertions.
4. Add shared page-test helpers for:
   - query client bootstrapping
   - mocked API clients
   - seeded route params
   - permission-context setup
5. Keep page tests at the feature boundary:
   - mock network/API modules
   - verify user-visible behavior
   - do not duplicate detailed component tests from `6.2`

### Files to touch
- `frontend/src/features/**/**.test.tsx` (new)
- `frontend/src/test/` (shared page harness)
- `frontend/src/api/` mocks or test adapters

---

## 6.4 - E2E Coverage

**Goal**: Expand Playwright from a small regression set to workflow coverage for every major ERP domain.

### Requirements
1. Keep the existing 4 Playwright specs and expand coverage to all major domain flows:
   - auth and password reset
   - admin/users/permissions
   - projects and contracts
   - BOQ, measurements, work done, RA bills
   - payments and secured advances
   - materials, receipts, requisitions, issues, stock ledger, adjustments
   - labour, attendance, bills, productivity, advances
   - reports, documents, audit, AI boundary
2. Each domain should have at least:
   - one happy-path business flow
   - one validation or error-path assertion
   - one permission/visibility assertion where role rules matter
3. Reuse fixtures aggressively:
   - session bootstrap
   - mocked API payload builders
   - common navigation helpers
4. Keep the suite CI-viable:
   - split specs by domain
   - avoid giant all-in-one journeys
   - prefer deterministic mocked responses over flaky external dependencies
5. Update Playwright config/reporting only as needed to keep runtime reasonable and artifacts debuggable.

### Files to touch
- `frontend/e2e/*.spec.ts`
- `frontend/e2e/support/`
- `frontend/playwright.config.ts`
- `.github/workflows/frontend-ci.yml`

---

## 6.5 - API Contract Tests

**Goal**: Make backend response schemas and frontend API types impossible to drift silently.

### Decision

Use the backend OpenAPI schema as the contract source of truth, then generate or validate frontend response types against it in CI.

### Requirements
1. Add a backend contract export step:
   - generate `openapi.json` from the FastAPI app in a deterministic script
   - store it as a build artifact or checked-in generated file if that fits the repo workflow better
2. Add frontend contract tooling:
   - use `openapi-typescript` or an equivalent generator to produce typed API contracts
   - either replace manual response types in `frontend/src/api/types.ts` or assert compatibility against generated types
3. Add tests or validation scripts that fail when:
   - a backend response model changes without frontend type updates
   - an endpoint is removed or renamed without corresponding frontend updates
4. Validate critical endpoints first:
   - auth
   - dashboard
   - projects
   - contracts
   - measurements
   - RA bills
   - payments
   - reports
5. Wire contract validation into CI so drift is blocked before merge.

### Files to touch
- `backend/` contract export script (new)
- `frontend/package.json`
- `frontend/src/api/types.ts`
- `frontend/src/api/` generated contract file(s)
- `.github/workflows/backend-ci.yml`
- `.github/workflows/frontend-ci.yml`

---

## 6.6 - Load/Stress Testing

**Goal**: Add repeatable performance tests for concurrent users and large datasets so the team can detect throughput and latency regressions before production.

### Decision

Use `k6` as the default load-testing tool for Phase 6 because it is scriptable, CI-friendly, and well-suited for HTTP API performance baselines. Keep the design extensible if richer user-behavior simulations are needed later.

### Requirements
1. Add load-test scripts for critical backend flows:
   - login/auth token refresh
   - dashboard summary fetch
   - paginated list endpoints with large payloads
   - RA bill and payment listing/detail endpoints
   - report endpoints over seeded large datasets
2. Define baseline scenarios:
   - 100+ concurrent virtual users
   - large datasets with 10K+ rows in list/report contexts
   - spike and steady-state scenarios
3. Record thresholds such as:
   - request failure rate
   - p95 latency
   - throughput
4. Add seed/setup guidance for realistic local runs and CI smoke runs.
5. Keep load tests separate from default unit-test CI if they are too heavy, but add at least one smoke-performance gate that runs automatically.

### Files to touch
- `backend/load/` or `backend/perf/` (new)
- `backend/README.md`
- `backend/docker-compose.yml` or supporting seed scripts if needed
- `.github/workflows/backend-ci.yml` or a dedicated perf workflow

---

## 6.7 - Visual Regression

**Goal**: Catch unintended UI changes with deterministic screenshot comparison.

### Requirements
1. Add Playwright visual tests for stable, representative screens:
   - shell layout
   - login/auth screens
   - dashboard
   - table-heavy pages
   - dialogs/drawers
   - reports surfaces
2. Make screenshots deterministic:
   - stable viewport
   - stable mock data
   - disable or control time-sensitive UI where needed
   - mask volatile content such as timestamps if necessary
3. Store baseline snapshots in repo and upload diffs in CI artifacts.
4. Keep visual coverage focused on high-value screens rather than every page permutation.

### Files to touch
- `frontend/e2e/` visual spec(s)
- `frontend/playwright.config.ts`
- `frontend/test-results/` or snapshot directories
- `.github/workflows/frontend-ci.yml`

---

## 6.8 - Accessibility Audit

**Goal**: Add automated accessibility checks and raise the UI toward WCAG 2.1 AA compliance.

### Requirements
1. Add `axe-core` based automation:
   - `@axe-core/playwright` for page-level scans
   - optional component-level a11y assertions in Vitest where they add value
2. Cover accessibility-critical surfaces:
   - login/reset password
   - navigation shell
   - dialogs and drawers
   - forms
   - tables and filters
   - dashboards and reports
3. Fix or flag common issues:
   - missing labels
   - missing accessible names
   - broken focus order
   - missing keyboard support
   - color contrast problems
   - semantic table or heading issues
4. Add an accessibility CI job or fold checks into Playwright CI without making results invisible.
5. Document any temporary exceptions explicitly; do not silently suppress violations.

### Files to touch
- `frontend/package.json`
- `frontend/e2e/` accessibility spec(s)
- `frontend/src/components/`
- `frontend/src/features/`
- `frontend/src/styles/index.css`
- `.github/workflows/frontend-ci.yml`

---

## Implementation Rules

1. Follow the phase order strictly: `6.1` before `6.2`, `6.2` before `6.3`, and so on through `6.8`.
2. Every completed task must include code, tests, and CI workflow updates unless the repo already has an equivalent gate.
3. Prefer shared test harnesses and fixtures over copy-pasted setup.
4. Keep tests deterministic: fixed clocks, stable IDs, controlled randomness, mocked external systems.
5. Do not hide instability with retries except where the underlying tool genuinely requires it.
6. Prefer behavior-focused assertions over implementation-detail assertions.
7. Coverage percentages are a floor, not the objective; meaningful regression protection is the objective.
8. When adding generated files or snapshots, document how to refresh them.
9. If a task uncovers missing architecture seams, add lightweight testability helpers rather than bending tests around hard-to-isolate code.
10. Before moving to the next task, verify the current task locally with the narrowest high-signal commands available and update docs/CI accordingly.
