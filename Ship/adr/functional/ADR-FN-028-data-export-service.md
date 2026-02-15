# ADR-FN-028: Data Export Service (CSV/Excel/PDF)

**Status:** Accepted
**Date:** 2026-02-12
**Technical Area:** Backend

---

## Context

Users need to export platform data (invoices, orders, deliveries, settlements) into standard formats for accounting systems, reporting, and offline analysis. The platform currently has no export functionality.

### Business Context
Maritime procurement teams require data exports for:
- Accounting system integration — invoices and settlement data in Excel/CSV for import into ERP/accounting software
- Audit compliance — PDF invoices with proper formatting for regulatory filing
- Management reporting — delivery performance, spend analysis, supplier scorecards
- Vessel-level cost reporting — per-port-call cost breakdowns for fleet management
- Offline access — downloaded reports for use during vessel operations with limited connectivity

### Technical Context
- Large datasets (thousands of line items per settlement period) require async processing
- PDF generation is CPU-intensive and should not block API responses
- Generated files stored in S3 for download via presigned URLs (ADR-NF-013)
- Celery for async job processing (ADR-NF-008)
- Small exports (<1000 rows) can be streamed directly without async processing

### Assumptions
- Three export formats required for MVP: CSV, Excel (xlsx), PDF
- Export jobs are user-initiated and async for large datasets
- Generated files are stored in S3 with a 7-day expiration
- Users download via presigned URLs — no streaming through the API server for large files
- Invoice PDF is the most common single-document export (synchronous)

---

## Decision Drivers

- Support CSV, Excel, and PDF formats
- Handle large datasets without blocking the API
- Secure file storage with time-limited download URLs
- Simple, consistent API across all exportable entities
- Minimal library dependencies

---

## Considered Options

### Option 1: Synchronous Streaming Exports Only
**Description:** All exports stream directly from the API response. No S3 storage.

**Pros:**
- Simple implementation — no job queue needed
- Immediate response
- No S3 storage costs

**Cons:**
- Blocks API process for large exports
- Timeouts for large datasets
- No retry on failure
- PDF generation blocks the request thread

### Option 2: Async Export via Celery with S3 Storage (Chosen)
**Description:** Large exports processed as Celery tasks, stored in S3, downloaded via presigned URLs. Small exports (<1000 rows) streamed directly.

**Pros:**
- Large exports don't block the API
- Retry support for failed exports
- Progress tracking via job status
- S3 storage with presigned URLs for secure download
- Small exports still fast (synchronous path)

**Cons:**
- More infrastructure (Celery + S3 required)
- Polling or websocket needed for completion notification
- Job cleanup needed for expired files

### Option 3: Third-Party Export/Report Service
**Description:** Use a reporting service (Jasper, BIRT, or SaaS like DocSpring) for document generation.

**Pros:**
- Rich report templates
- Advanced PDF layouts
- Built-in scheduling

**Cons:**
- Vendor lock-in and ongoing costs
- Data must be sent to external service
- Over-engineered for MVP export needs
- Latency from external service calls

---

## Decision

**Chosen Option:** Async Export via Celery with S3 Storage

We implement an export service with a dual-path approach: small exports (<1000 rows for CSV/Excel) are streamed directly, while large exports and all PDFs are processed as Celery tasks with output stored in S3. Users poll for job completion and download via presigned URLs.

### Rationale
The async approach ensures the API remains responsive even for large exports. S3 storage with presigned URLs provides secure, time-limited downloads without proxying large files through the API server. The dual-path approach gives immediate results for small exports while handling large datasets gracefully. Standard Python libraries (csv, openpyxl, weasyprint) minimize dependencies.

---

## Consequences

### Positive
- API remains responsive for all export sizes
- Large datasets handled without timeouts
- Retry support for failed exports
- Secure download via presigned URLs with expiration
- Progress tracking for long-running exports
- Reusable export infrastructure for any future exportable entity

### Negative
- Additional infrastructure dependency (Celery + S3 must be available)
- **Mitigation:** Both are already required by the platform (ADR-NF-008, ADR-NF-013)
- Polling or callback needed for async exports
- **Mitigation:** Simple status endpoint; future WebSocket notification

### Risks
- weasyprint has system-level dependencies (cairo, pango): Document in deployment requirements, use Docker image with pre-installed deps
- Large PDF generation may be memory-intensive: Set Celery worker memory limits, paginate large PDFs
- S3 storage costs for generated files: 7-day TTL with lifecycle policy auto-deletion

---

## Implementation Notes

### Database Schema

```sql
-- Export job tracking
CREATE TABLE export_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    requested_by UUID NOT NULL REFERENCES users(id),

    -- Export specification
    export_type VARCHAR(30) NOT NULL,
    -- INVOICES, ORDERS, DELIVERIES, SETTLEMENTS, INVOICE_SINGLE, DELIVERY_REPORT
    export_format VARCHAR(10) NOT NULL,
    -- CSV, XLSX, PDF
    filters JSONB DEFAULT '{}', -- applied filters: date range, status, supplier, etc.

    -- Entity reference (for single-entity exports like invoice PDF)
    entity_id UUID,
    entity_type VARCHAR(30),

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    -- PENDING, PROCESSING, COMPLETED, FAILED, EXPIRED
    progress_percent INTEGER DEFAULT 0,
    error_message TEXT,

    -- Output
    s3_key VARCHAR(500),
    s3_bucket VARCHAR(100),
    file_name VARCHAR(255),
    file_size_bytes BIGINT,
    content_type VARCHAR(50),
    download_url_expires_at TIMESTAMPTZ,

    -- Row counts
    total_rows INTEGER,
    processed_rows INTEGER DEFAULT 0,

    -- Timestamps
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ, -- when S3 object is deleted
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_export_jobs_org ON export_jobs(organization_id);
CREATE INDEX idx_export_jobs_user ON export_jobs(requested_by);
CREATE INDEX idx_export_jobs_status ON export_jobs(status);
```

### API Endpoints

```
# Data Export (4 endpoints)
POST   /api/v1/exports                             # Request export (type, format, filters)
GET    /api/v1/exports/{id}                         # Get export job status + download URL
GET    /api/v1/exports/{id}/download                # Download file (redirect to presigned URL)
GET    /api/v1/invoices/{id}/pdf                    # Inline invoice PDF (synchronous, single doc)
```

### Export Flow

```
User requests export
        │
        ▼
┌─────────────────────┐
│ Check row count     │
│ (estimate)          │
└────────┬────────────┘
         │
   ┌─────▼─────┐        ┌──────────────────┐
   │ < 1000    │        │ >= 1000 rows     │
   │ rows      │        │ or PDF format    │
   └─────┬─────┘        └───────┬──────────┘
         │                      │
   ┌─────▼──────────┐   ┌──────▼──────────┐
   │ Stream direct  │   │ Create Celery   │
   │ (sync response)│   │ export task     │
   └────────────────┘   └──────┬──────────┘
                               │
                        ┌──────▼──────────┐
                        │ Process in      │
                        │ worker          │
                        └──────┬──────────┘
                               │
                        ┌──────▼──────────┐
                        │ Upload to S3    │
                        │ (7-day TTL)     │
                        └──────┬──────────┘
                               │
                        ┌──────▼──────────┐
                        │ Return presigned│
                        │ download URL    │
                        └─────────────────┘
```

### Format Libraries

| Format | Library | Notes |
|--------|---------|-------|
| CSV | `csv` (stdlib) | StreamingResponse for sync, file write for async |
| Excel | `openpyxl` | .xlsx format, supports formatting and multiple sheets |
| PDF | `weasyprint` | HTML-to-PDF, supports CSS styling, headers/footers |

### Invoice PDF Template Structure

```html
<!-- Template rendered with Jinja2, converted to PDF by weasyprint -->
<div class="invoice">
  <header>
    <div class="company-info">{{ supplier.name }}</div>
    <div class="invoice-meta">
      <h1>INVOICE</h1>
      <p>Invoice #: {{ invoice.invoice_number }}</p>
      <p>Date: {{ invoice.invoice_date }}</p>
      <p>Due: {{ invoice.due_date }}</p>
    </div>
  </header>
  <section class="bill-to">
    <h3>Bill To:</h3>
    <p>{{ buyer.name }}</p>
    <p>Vessel: {{ order.vessel_name }} (IMO: {{ order.vessel_imo }})</p>
    <p>Port: {{ order.delivery_port }}</p>
  </section>
  <table class="line-items">
    <!-- IMPA code, description, qty ordered, qty delivered, qty accepted, unit price, total -->
  </table>
  <section class="totals">
    <!-- Subtotal, tax, credits, total -->
  </section>
</div>
```

### Dependencies
- ADR-NF-008: Async Processing (Celery tasks for large exports)
- ADR-NF-013: Object Storage (S3 for generated files)
- ADR-NF-007: API Design Principles (endpoint conventions)
- ADR-FN-027: Settlement & Invoice Generation (invoice data for export)

### Migration Strategy
1. Create `export_jobs` table
2. Implement CSV export (simplest format first)
3. Add Excel export with openpyxl
4. Add PDF export with weasyprint (invoice template first)
5. Implement async path with Celery for large exports
6. Add S3 upload and presigned URL generation
7. Set up S3 lifecycle policy for 7-day expiration

---

## References
- [openpyxl Documentation](https://openpyxl.readthedocs.io/)
- [WeasyPrint Documentation](https://doc.courtbouillon.org/weasyprint/)
- [AWS S3 Presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)
- [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
