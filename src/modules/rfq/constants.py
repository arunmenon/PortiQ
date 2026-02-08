"""RFQ state machine transitions, event types, and editable states."""

from __future__ import annotations

from src.models.enums import RfqStatus, RfqTransitionType

# Valid transitions: from_status -> {transition_type -> to_status}
VALID_TRANSITIONS: dict[RfqStatus, dict[RfqTransitionType, RfqStatus]] = {
    RfqStatus.DRAFT: {
        RfqTransitionType.PUBLISH: RfqStatus.PUBLISHED,
        RfqTransitionType.CANCEL: RfqStatus.CANCELLED,
    },
    RfqStatus.PUBLISHED: {
        RfqTransitionType.OPEN_BIDDING: RfqStatus.BIDDING_OPEN,
        RfqTransitionType.CANCEL: RfqStatus.CANCELLED,
    },
    RfqStatus.BIDDING_OPEN: {
        RfqTransitionType.CLOSE_BIDDING: RfqStatus.BIDDING_CLOSED,
        RfqTransitionType.CANCEL: RfqStatus.CANCELLED,
    },
    RfqStatus.BIDDING_CLOSED: {
        RfqTransitionType.START_EVALUATION: RfqStatus.EVALUATION,
        RfqTransitionType.CANCEL: RfqStatus.CANCELLED,
    },
    RfqStatus.EVALUATION: {
        RfqTransitionType.AWARD: RfqStatus.AWARDED,
        RfqTransitionType.CANCEL: RfqStatus.CANCELLED,
    },
    RfqStatus.AWARDED: {
        RfqTransitionType.COMPLETE: RfqStatus.COMPLETED,
        RfqTransitionType.CANCEL: RfqStatus.CANCELLED,
    },
}

# Event type strings for the outbox
EVENT_RFQ_PUBLISHED = "rfq.published"
EVENT_RFQ_BIDDING_OPENED = "rfq.bidding_opened"
EVENT_RFQ_BIDDING_CLOSED = "rfq.bidding_closed"
EVENT_RFQ_AWARDED = "rfq.awarded"
EVENT_RFQ_COMPLETED = "rfq.completed"
EVENT_RFQ_CANCELLED = "rfq.cancelled"
EVENT_QUOTE_SUBMITTED = "quote.submitted"
EVENT_QUOTE_REVISED = "quote.revised"
EVENT_QUOTE_WITHDRAWN = "quote.withdrawn"
EVENT_INVITATION_SENT = "invitation.sent"
EVENT_INVITATION_ACCEPTED = "invitation.accepted"
EVENT_INVITATION_DECLINED = "invitation.declined"

# Statuses where the RFQ content (title, line items, etc.) can still be edited
EDITABLE_STATUSES: set[RfqStatus] = {
    RfqStatus.DRAFT,
}

# Statuses where quotes can be submitted or revised
BIDDABLE_STATUSES: set[RfqStatus] = {
    RfqStatus.BIDDING_OPEN,
}

# Terminal statuses (no further transitions possible)
TERMINAL_STATUSES: set[RfqStatus] = {
    RfqStatus.COMPLETED,
    RfqStatus.CANCELLED,
}
