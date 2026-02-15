"""Delivery state machine transitions, event types, and S3 config."""

from __future__ import annotations

from src.models.enums import DeliveryStatus

# Valid status transitions: from_status -> set of allowed to_statuses
VALID_TRANSITIONS: dict[DeliveryStatus, set[DeliveryStatus]] = {
    DeliveryStatus.PENDING: {DeliveryStatus.DISPATCHED, DeliveryStatus.CANCELLED},
    DeliveryStatus.DISPATCHED: {DeliveryStatus.IN_TRANSIT, DeliveryStatus.DELIVERED, DeliveryStatus.CANCELLED},
    DeliveryStatus.IN_TRANSIT: {DeliveryStatus.ARRIVED, DeliveryStatus.DELIVERED, DeliveryStatus.CANCELLED},
    DeliveryStatus.ARRIVED: {DeliveryStatus.DELIVERED, DeliveryStatus.CANCELLED},
    DeliveryStatus.DELIVERED: {DeliveryStatus.ACCEPTED, DeliveryStatus.DISPUTED},
    DeliveryStatus.ACCEPTED: set(),
    DeliveryStatus.DISPUTED: set(),
    DeliveryStatus.CANCELLED: set(),
}

# Domain event type strings
EVENT_DELIVERY_CREATED = "delivery.created"
EVENT_DELIVERY_DISPATCHED = "delivery.dispatched"
EVENT_DELIVERY_RECORDED = "delivery.recorded"
EVENT_DELIVERY_ACCEPTED = "delivery.accepted"
EVENT_DELIVERY_DISPUTED = "delivery.disputed"
EVENT_DELIVERY_PHOTO_UPLOADED = "delivery.photo.uploaded"

# S3 configuration defaults
S3_DELIVERY_BUCKET = "portiq-deliveries"
S3_PHOTO_PREFIX = "delivery-photos"
S3_SIGNATURE_PREFIX = "delivery-signatures"
S3_PRESIGNED_URL_EXPIRY_SECONDS = 3600  # 1 hour

# Terminal statuses — no further transitions allowed
TERMINAL_STATUSES: set[DeliveryStatus] = {
    DeliveryStatus.ACCEPTED,
    DeliveryStatus.DISPUTED,
    DeliveryStatus.CANCELLED,
}
