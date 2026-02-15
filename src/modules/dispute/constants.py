"""Dispute state machine transitions, event types, and SLA defaults."""

from __future__ import annotations

from src.models.enums import DisputeStatus

# Valid transitions: from_status -> [allowed to_statuses]
VALID_DISPUTE_TRANSITIONS: dict[DisputeStatus, list[DisputeStatus]] = {
    DisputeStatus.OPEN: [DisputeStatus.UNDER_REVIEW, DisputeStatus.CLOSED],
    DisputeStatus.UNDER_REVIEW: [
        DisputeStatus.AWAITING_SUPPLIER,
        DisputeStatus.AWAITING_BUYER,
        DisputeStatus.RESOLVED,
        DisputeStatus.ESCALATED,
    ],
    DisputeStatus.AWAITING_SUPPLIER: [DisputeStatus.UNDER_REVIEW],
    DisputeStatus.AWAITING_BUYER: [DisputeStatus.UNDER_REVIEW],
    DisputeStatus.RESOLVED: [DisputeStatus.CLOSED],
    DisputeStatus.ESCALATED: [DisputeStatus.RESOLVED, DisputeStatus.CLOSED],
}

# Terminal statuses (no further transitions possible)
TERMINAL_STATUSES: set[DisputeStatus] = {
    DisputeStatus.CLOSED,
}

# Event type strings for the outbox
EVENT_DISPUTE_CREATED = "dispute.created"
EVENT_DISPUTE_ASSIGNED = "dispute.assigned"
EVENT_DISPUTE_COMMENTED = "dispute.commented"
EVENT_DISPUTE_RESOLVED = "dispute.resolved"
EVENT_DISPUTE_ESCALATED = "dispute.escalated"
EVENT_DISPUTE_SLA_BREACHED = "dispute.sla_breached"

# SLA defaults (in hours)
SLA_RESPONSE_HOURS = 48
SLA_RESOLUTION_HOURS = 168  # 7 days
