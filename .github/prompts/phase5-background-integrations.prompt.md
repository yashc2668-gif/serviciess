---
description: "Implement Phase 5 background processing & integrations for M2N Construction ERP — Redis/Celery task queue, email/SMS notifications, PDF generation, scheduled reports, bank/Tally/GST integrations"
agent: "agent"
argument-hint: "Task number (e.g. 5.1) or keyword (e.g. celery, email, pdf, reports, sms, bank, tally, gst)"
---

# Phase 5 — Background Processing & Integrations

You are implementing async background processing and external integrations for the **M2N Construction ERP** backend (FastAPI + SQLAlchemy 2 + Pydantic v2). Follow the project conventions in [copilot-instructions.md](../../.github/copilot-instructions.md).

## Current State

- **Task placeholders exist** at `backend/app/tasks/` — `pdf_tasks.py`, `notification_tasks.py`, `report_tasks.py` are empty stubs.
- **Integration placeholders** at `backend/app/integrations/` — `email.py` (has OTP email log-only), `future_bank.py` (empty), `storage.py` (local file adapter).
- **Workflow placeholders** at `backend/app/workflows/` — 4 empty files for contract revision, payment approval, RA bill approval, requisition approval.
- **Notification model** at `backend/app/models/notification.py` is a skeleton (id, title, created_at) — needs user_id, message, channel, status, read tracking.
- **ReportLab 4.4.10** already in `requirements.txt`. No Celery/Redis/WeasyPrint/SMS deps yet.
- **Reporting schemas** exist at `backend/app/schemas/reporting.py` (ProjectCostReport, ContractCommercialReport, AgeingBucket).
- **Config** at `backend/app/core/config.py` has no Redis, Celery, SMTP, or SMS settings.

## Task Manifest

When the user specifies a task number or keyword, implement ONLY that task. When no argument is given, present the task list and ask which to start.

| #   | Task                        | Layer   | Priority | Status      |
|-----|-----------------------------|---------|----------|-------------|
| 5.1 | Redis + Celery setup        | Backend | HIGH     | Not started |
| 5.2 | Email notifications         | Backend | HIGH     | Not started |
| 5.3 | PDF generation              | Backend | HIGH     | Not started |
| 5.4 | Scheduled reports           | Backend | MEDIUM   | Not started |
| 5.5 | SMS/WhatsApp alerts         | Backend | MEDIUM   | Not started |
| 5.6 | Bank integration (SFMS)     | Backend | MEDIUM   | Not started |
| 5.7 | Tally/accounting sync       | Backend | MEDIUM   | Not started |
| 5.8 | GST integration             | Both    | MEDIUM   | Not started |

---

## 5.1 — Redis + Celery Setup

**Goal**: Add Celery with Redis broker as the async task queue for PDF, email, and report jobs.

### Requirements
1. Add `celery[redis]>=5.4`, `redis>=5.0` to `requirements.txt`.
2. Create `backend/app/core/celery_app.py`:
   - Celery app factory reading `REDIS_URL` from settings.
   - Autodiscover tasks from `app.tasks`.
   - Config: `task_serializer="json"`, `result_serializer="json"`, `accept_content=["json"]`, `task_track_started=True`, `task_acks_late=True` (at-least-once delivery).
3. Extend `backend/app/core/config.py`:
   - `REDIS_URL: str = "redis://localhost:6379/0"`
   - `CELERY_RESULT_BACKEND: str | None = None` (optional)
   - `CELERY_TASK_ALWAYS_EAGER: bool = False` (set `True` in tests for sync execution).
4. Add Celery worker + Redis services to `docker-compose.yml`.
5. Create `backend/celeryconfig.py` or integrate config into the app factory.
6. Add a health-check endpoint `GET /api/v1/health/celery` that pings the broker.
7. Write unit tests with `CELERY_TASK_ALWAYS_EAGER=True` so tasks execute synchronously in test.

### Files to touch
- `backend/requirements.txt`
- `backend/app/core/config.py`
- `backend/app/core/celery_app.py` (new)
- `backend/docker-compose.yml`
- `backend/app/api/v1/endpoints/health.py` (new or extend)
- `backend/app/tests/test_celery_setup.py` (new)

---

## 5.2 — Email Notifications

**Goal**: Send templated emails on workflow state changes (submitted, approved, rejected) via Celery tasks.

### Requirements
1. Extend `backend/app/core/config.py` with SMTP settings:
   - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `EMAIL_FROM_NAME`, `EMAIL_FROM_ADDRESS`.
2. Create `backend/app/integrations/email.py` → full SMTP client using `smtplib` + `email.mime`:
   - `send_email(to, subject, html_body, attachments=None)` — synchronous, called from Celery task.
   - Support HTML templates from `backend/app/templates/email/`.
3. Create email templates (Jinja2 HTML):
   - `workflow_submitted.html`, `workflow_approved.html`, `workflow_rejected.html`, `payment_released.html`.
4. Implement `backend/app/tasks/notification_tasks.py`:
   - `send_workflow_notification.delay(entity_type, entity_id, action, recipient_ids)`.
   - Look up user emails from DB, render template, call `send_email`.
5. Expand the **Notification model** (`backend/app/models/notification.py`):
   - Add: `user_id` (FK→users), `message` (Text), `channel` (Enum: email/sms/in_app), `status` (Enum: pending/sent/failed/read), `entity_type`, `entity_id`, `sent_at`, `read_at`.
   - Create Alembic migration.
6. Create `backend/app/schemas/notification.py` — `NotificationCreate`, `NotificationOut`, `NotificationUpdate`.
7. Create `backend/app/services/notification_service.py` — `create_notification()`, `mark_as_read()`, `list_user_notifications()`.
8. Wire workflow services to dispatch notification tasks after state transitions.
9. Write tests with mocked SMTP.

### Files to touch
- `backend/app/core/config.py`
- `backend/app/integrations/email.py` (rewrite)
- `backend/app/templates/email/` (new directory + templates)
- `backend/app/tasks/notification_tasks.py`
- `backend/app/models/notification.py`
- `backend/app/schemas/notification.py` (new)
- `backend/app/services/notification_service.py` (new)
- `backend/alembic/versions/` (new migration)
- `backend/app/tests/test_notifications.py` (new)

---

## 5.3 — PDF Generation

**Goal**: Generate downloadable PDFs for RA Bills, Measurement Sheets, and Payment Vouchers using ReportLab.

### Requirements
1. Create `backend/app/services/pdf_service.py`:
   - `generate_ra_bill_pdf(ra_bill_id) -> bytes` — header, line items table, totals, signatures block.
   - `generate_measurement_sheet_pdf(measurement_id) -> bytes` — measurement items with dimensions.
   - `generate_payment_voucher_pdf(payment_id) -> bytes` — payment details, deductions, net amount.
   - Use `Decimal` formatting for all amounts; no floats.
2. Implement `backend/app/tasks/pdf_tasks.py`:
   - `generate_and_store_pdf.delay(doc_type, entity_id)` — generate PDF, store via `StorageAdapter`, create a `Document` record.
3. Add API endpoints:
   - `GET /api/v1/ra-bills/{id}/pdf` — returns PDF or triggers async generation and returns 202.
   - `GET /api/v1/measurements/{id}/pdf`
   - `GET /api/v1/payments/{id}/pdf`
4. PDF layout requirements:
   - Company header (name, address, GSTIN from project/company model).
   - Table with alternating-row shading.
   - Footer with page numbers and generation timestamp.
5. Write tests with golden-file comparison (verify PDF byte-stream is non-empty and valid).

### Files to touch
- `backend/app/services/pdf_service.py` (new)
- `backend/app/tasks/pdf_tasks.py`
- `backend/app/api/v1/endpoints/ra_bills.py` (add PDF endpoint)
- `backend/app/api/v1/endpoints/measurements.py` (add PDF endpoint)
- `backend/app/api/v1/endpoints/payments.py` (add PDF endpoint)
- `backend/app/tests/test_pdf_generation.py` (new)

---

## 5.4 — Scheduled Reports

**Goal**: Weekly/monthly MIS reports emailed automatically via Celery Beat.

### Requirements
1. Add `celery[redis]` beat schedule to `celery_app.py`:
   - `weekly-project-cost-report` — every Monday 8 AM IST.
   - `monthly-commercial-report` — 1st of month, 8 AM IST.
2. Implement `backend/app/tasks/report_tasks.py`:
   - `generate_project_cost_report()` — query all active projects, build tabular report, generate PDF, email to project managers.
   - `generate_monthly_commercial_report()` — contract-level commercial summary, email to accountants.
3. Use the existing reporting schemas in `app/schemas/reporting.py` for data assembly.
4. Add config: `REPORT_RECIPIENTS_PROJECT_COST`, `REPORT_RECIPIENTS_COMMERCIAL` (comma-separated email lists or role-based).
5. Write tests for report generation logic (mock email sending).

### Files to touch
- `backend/app/core/celery_app.py` (add beat schedule)
- `backend/app/core/config.py` (report recipient settings)
- `backend/app/tasks/report_tasks.py`
- `backend/app/tests/test_scheduled_reports.py` (new)

---

## 5.5 — SMS/WhatsApp Alerts

**Goal**: Send SMS/WhatsApp notifications for payment releases and critical approvals.

**Decision**: Default to `MSG91` for India-first transactional SMS and WhatsApp. Keep a provider abstraction so `Gupshup` (WhatsApp-first) or `Twilio` can be added later without changing workflow code.

### Requirements
1. Add SMS/WhatsApp provider dependency and implement `MSG91` first; do not treat `TextLocal` as the default path.
2. Extend `backend/app/core/config.py`:
   - `SMS_PROVIDER` (enum: msg91/gupshup/twilio/disabled), `SMS_API_KEY`, `SMS_SENDER_ID`, `SMS_DLT_ENTITY_ID`, `WHATSAPP_PROVIDER`, `WHATSAPP_ENABLED`.
3. Create `backend/app/integrations/sms.py`:
   - `send_sms(phone_number, template_key, params)` — provider-agnostic interface that resolves approved templates and India DLT metadata instead of sending raw free-form text.
   - `send_whatsapp(phone_number, template_name, params)` — template-based WhatsApp Business API.
   - Implement `MSG91SmsClient` first and keep adapters for additional providers behind the same interface.
4. Create Celery tasks `backend/app/tasks/notification_tasks.py`:
   - `send_sms_alert.delay(phone, template_key, params)`.
   - `send_whatsapp_alert.delay(phone, template, params)`.
5. Trigger on: payment approved/released, RA bill approved, contract awarded.
6. Write tests for template resolution, mocked provider delivery, and provider fallback/disabled behavior.

### Files to touch
- `backend/requirements.txt`
- `backend/app/core/config.py`
- `backend/app/integrations/sms.py` (new)
- `backend/app/tasks/notification_tasks.py`
- `backend/app/tests/test_sms_alerts.py` (new)

---

## 5.6 — Bank Integration (SFMS Format)

**Goal**: Generate NEFT/RTGS payment instruction files in SFMS format for bulk bank uploads.

**Decision**: Make bank-file generation configurable by bank profile. Do not assume one universal SFMS layout. Implement one production-ready profile first for the client's live bank, then add more profiles behind the same renderer interface.

### Requirements
1. Create `backend/app/integrations/bank.py` (replace `future_bank.py`):
   - `generate_bank_file(payments: list[Payment], bank_profile: str | None = None) -> str`.
   - Introduce a `BankFileRenderer` abstraction with concrete bank profiles such as `sbi_corp`, `hdfc_enet`, or `icici_cib`.
   - Keep bank-specific field widths, headers, trailers, file naming, encoding, and checksum rules out of the payment service layer.
   - Validate IFSC codes, account numbers, amounts, debit account, and profile-specific mandatory fields.
2. Extend `backend/app/core/config.py`:
   - `BANK_EXPORT_PROFILE` (enum: sbi_corp/hdfc_enet/icici_cib), `BANK_EXPORT_ENCODING`.
3. Add API endpoint: `POST /api/v1/payments/bank-file` — accepts payment IDs plus optional `bank_profile`, returns downloadable `.txt`.
4. Add `bank_reference`, `bank_file_generated_at` columns to Payment model (migration).
5. Write tests with one concrete profile fixture for the primary deployment bank and shared contract tests for the renderer interface.

### Files to touch
- `backend/app/integrations/bank.py` (new, replaces `future_bank.py`)
- `backend/app/core/config.py`
- `backend/app/api/v1/endpoints/payments.py`
- `backend/app/models/payment.py`
- `backend/alembic/versions/` (new migration)
- `backend/app/tests/test_bank_integration.py` (new)

---

## 5.7 — Tally/Accounting Sync

**Goal**: Export financial vouchers in Tally-compatible XML format.

**Decision**: Target Tally Prime first. Keep the XML within the common import envelope used by Tally Prime and standard legacy Tally.ERP 9 voucher imports where practical, but do not design around ERP 9-only behavior.

### Requirements
1. Create `backend/app/integrations/tally.py`:
   - `export_payment_voucher_xml(payment) -> str` — Tally XML voucher format.
   - `export_receipt_voucher_xml(ra_bill) -> str`.
   - `export_journal_voucher_xml(entries) -> str`.
   - XML must follow the standard import envelope shape (`ENVELOPE > BODY > DATA > TALLYMESSAGE`) expected by Tally Prime for voucher imports.
   - Stay on XML for v1 even though newer Tally Prime releases also support JSON import.
2. Add API endpoint: `POST /api/v1/export/tally` — accepts date range + voucher types, returns `.xml` file.
3. Use `xml.etree.ElementTree` — no third-party XML lib needed.
4. Write tests validating XML structure against Tally Prime import fixtures and a minimal legacy-compatible envelope for standard vouchers.

### Files to touch
- `backend/app/integrations/tally.py` (new)
- `backend/app/api/v1/endpoints/export.py` (new)
- `backend/app/tests/test_tally_export.py` (new)

---

## 5.8 — GST Integration

**Goal**: Capture HSN/SAC tax metadata, compute GST on RA bills, and surface GST-ready summaries in payment flows.

**Decision**: Implement GST as a document-level tax engine, not just a material-master lookup. Capture tax classification, party GSTINs, and place-of-supply context as bill snapshots. Keep the data model aligned with GSTR-1 and e-invoice-ready fields, but defer IRP/e-way bill API integration to a later phase.

### Requirements

**Backend:**
1. Extend tax master data beyond materials:
   - Add `tax_code_type` (`hsn`/`sac`), `tax_code`, and `default_gst_rate` to `Material` and `BOQItem`.
   - Reuse existing `gst_number` fields on `Company` and `Vendor`, but add shared GSTIN validation and state-code extraction helpers.
   - Do not hardcode one universal HSN length rule; validate through a shared tax-code helper so filing-rule changes can be absorbed without schema churn.
2. Create `backend/app/calculators/gst_calculator.py`:
   - `compute_gst(taxable_amount: Decimal, gst_rate: Decimal, supplier_state_code: str, place_of_supply_state_code: str) -> GSTBreakdown` -> returns `cgst`, `sgst`, `igst`, `total_with_gst`.
   - Derive intra-state vs inter-state inside the calculator from state codes; do not trust a raw boolean from the client.
   - Include GSTIN/tax-code validators and use `Decimal(ROUND_HALF_UP)` with `MONEY_QUANTUM`.
3. Add tax snapshot fields to `RABillItem` and bill-level totals to `RABill`:
   - Item snapshot fields: `tax_code_type_snapshot`, `tax_code_snapshot`, `gst_rate_snapshot`, `taxable_amount`, `cgst_amount`, `sgst_amount`, `igst_amount`.
   - Bill totals: `taxable_value`, `cgst_total`, `sgst_total`, `igst_total`, `gross_amount_before_tax`, `gross_amount_with_tax`, `place_of_supply_state_code`.
4. Extend RA bill and payment schemas/services:
   - Freeze GST snapshots when an RA bill leaves draft so later master-data edits do not change historical tax.
   - Payment responses should expose GST summary from the linked RA bill/invoice; do not recompute GST from payment release amount.
5. Add GST summary to PDF/report outputs (from 5.3), including supplier GSTIN, recipient GSTIN, place of supply, taxable value, rate, and CGST/SGST/IGST split.
6. Write tests for GSTIN validation, state-based CGST/SGST vs IGST split, rounding, and snapshot immutability after master updates.

**Frontend:**
7. Add `HSN/SAC`, tax code, and default GST rate fields to material and BOQ create/edit forms.
8. Display a read-only GST breakdown on RA bill and payment detail pages, sourced from stored bill snapshots.
9. Block RA bill approval when mandatory GST context is missing (for example invalid GSTIN or missing place of supply).

### Files to touch
- `backend/app/models/material.py`
- `backend/app/models/boq.py`
- `backend/app/models/ra_bill.py`
- `backend/app/models/ra_bill_item.py`
- `backend/app/calculators/gst_calculator.py` (new)
- `backend/app/schemas/material.py`
- `backend/app/schemas/boq.py`
- `backend/app/schemas/ra_bill.py`
- `backend/app/schemas/payment.py`
- `backend/alembic/versions/` (new migration)
- `backend/app/tests/test_gst_calculator.py` (new)
- `backend/app/services/ra_bill_service.py`
- `backend/app/services/payment_service.py`
- `backend/app/services/pdf_service.py`
- `frontend/src/features/materials/` (edit forms)
- `frontend/src/features/boq/` (edit forms)
- `frontend/src/features/ra-bills/` (detail page)
- `frontend/src/features/payments/` (detail page)

---

## Implementation Rules

1. **Follow existing patterns**: Endpoint → Service → Repository → Model. Business logic in services, not endpoints.
2. **Financial math**: Always `Decimal` with `ROUND_HALF_UP` and `MONEY_QUANTUM = Decimal("0.01")`. Never `float`.
3. **Concurrency**: Use `apply_write_lock()` + `flush_with_conflict_handling()` for entities with `lock_version`.
4. **Audit trail**: Call `log_audit_event()` before commit for state-changing operations.
5. **Auth**: Endpoints use `Depends(get_current_user)` + `Depends(require_roles(...))`.
6. **Tests**: `unittest.TestCase` + `TestClient`, in-memory SQLite with `StaticPool`. Mock external services (SMTP, SMS, Redis).
7. **Migrations**: One Alembic revision per feature. Run `python scripts/verify_migration_discipline.py` after.
8. **Config**: All secrets/URLs via `Settings` (Pydantic). No hardcoded credentials.
9. **Error handling**: Raise `HTTPException` with proper status codes. Log failures with structured logging.
10. **Celery tasks**: Idempotent. `task_acks_late=True`. Handle retries with `max_retries=3`, `default_retry_delay=60`.
