"""Invoice status transitions, event types, and terminal states."""

from __future__ import annotations

from src.models.enums import InvoiceStatus

# ---------------------------------------------------------------------------
# Valid status transitions: current_status -> set of allowed next statuses
# ---------------------------------------------------------------------------

INVOICE_TRANSITIONS: dict[InvoiceStatus, set[InvoiceStatus]] = {
    InvoiceStatus.DRAFT: {
        InvoiceStatus.READY,
        InvoiceStatus.CANCELLED,
    },
    InvoiceStatus.READY: {
        InvoiceStatus.SENT,
        InvoiceStatus.CANCELLED,
    },
    InvoiceStatus.SENT: {
        InvoiceStatus.ACKNOWLEDGED,
        InvoiceStatus.DISPUTED,
        InvoiceStatus.CANCELLED,
    },
    InvoiceStatus.ACKNOWLEDGED: {
        InvoiceStatus.PAID,
        InvoiceStatus.DISPUTED,
    },
    InvoiceStatus.DISPUTED: {
        InvoiceStatus.ACKNOWLEDGED,
        InvoiceStatus.CREDIT_NOTE,
        InvoiceStatus.CANCELLED,
    },
}

INVOICE_TERMINAL_STATUSES: set[InvoiceStatus] = {
    InvoiceStatus.PAID,
    InvoiceStatus.CANCELLED,
    InvoiceStatus.CREDIT_NOTE,
}

# ---------------------------------------------------------------------------
# Event type strings for the outbox
# ---------------------------------------------------------------------------

EVENT_INVOICE_GENERATED = "invoice.generated"
EVENT_INVOICE_READY = "invoice.ready"
EVENT_INVOICE_ACKNOWLEDGED = "invoice.acknowledged"
EVENT_INVOICE_PAID = "invoice.paid"
EVENT_SETTLEMENT_CLOSED = "settlement.closed"
