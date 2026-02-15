"""Export type configurations, content types, and file naming."""

from __future__ import annotations

from src.models.enums import ExportFormat, ExportType

# ---------------------------------------------------------------------------
# Content types per export format
# ---------------------------------------------------------------------------

FORMAT_CONTENT_TYPES: dict[ExportFormat, str] = {
    ExportFormat.CSV: "text/csv",
    ExportFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ExportFormat.PDF: "application/pdf",
}

FORMAT_EXTENSIONS: dict[ExportFormat, str] = {
    ExportFormat.CSV: ".csv",
    ExportFormat.XLSX: ".xlsx",
    ExportFormat.PDF: ".pdf",
}

# ---------------------------------------------------------------------------
# Allowed formats per export type
# ---------------------------------------------------------------------------

EXPORT_TYPE_ALLOWED_FORMATS: dict[ExportType, set[ExportFormat]] = {
    ExportType.INVOICES: {ExportFormat.CSV, ExportFormat.XLSX, ExportFormat.PDF},
    ExportType.ORDERS: {ExportFormat.CSV, ExportFormat.XLSX},
    ExportType.DELIVERIES: {ExportFormat.CSV, ExportFormat.XLSX},
    ExportType.SETTLEMENTS: {ExportFormat.CSV, ExportFormat.XLSX},
    ExportType.INVOICE_SINGLE: {ExportFormat.PDF},
    ExportType.DELIVERY_REPORT: {ExportFormat.PDF},
}

# ---------------------------------------------------------------------------
# S3 configuration defaults
# ---------------------------------------------------------------------------

EXPORT_S3_BUCKET = "portiq-exports"
EXPORT_S3_PREFIX = "exports"
EXPORT_FILE_TTL_DAYS = 7
EXPORT_PRESIGNED_URL_EXPIRY_SECONDS = 3600  # 1 hour

# ---------------------------------------------------------------------------
# Event type strings for the outbox
# ---------------------------------------------------------------------------

EVENT_EXPORT_REQUESTED = "export.requested"
EVENT_EXPORT_COMPLETED = "export.completed"
EVENT_EXPORT_FAILED = "export.failed"
