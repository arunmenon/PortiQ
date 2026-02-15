"""Order status transitions, event types, and terminal states."""

from __future__ import annotations

from src.models.enums import (
    FulfillmentLineItemStatus,
    FulfillmentStatus,
    OrderStatus,
    VendorOrderStatus,
)

# ---------------------------------------------------------------------------
# Valid status transitions: current_status -> set of allowed next statuses
# ---------------------------------------------------------------------------

ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING_PAYMENT: {
        OrderStatus.CONFIRMED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.CONFIRMED: {
        OrderStatus.PROCESSING,
        OrderStatus.CANCELLED,
    },
    OrderStatus.PROCESSING: {
        OrderStatus.PARTIALLY_FULFILLED,
        OrderStatus.FULFILLED,
        OrderStatus.CANCELLED,
        OrderStatus.DISPUTED,
    },
    OrderStatus.PARTIALLY_FULFILLED: {
        OrderStatus.FULFILLED,
        OrderStatus.CANCELLED,
        OrderStatus.DISPUTED,
    },
    OrderStatus.FULFILLED: {
        OrderStatus.COMPLETED,
        OrderStatus.DISPUTED,
    },
    OrderStatus.DISPUTED: {
        OrderStatus.PROCESSING,
        OrderStatus.COMPLETED,
        OrderStatus.CANCELLED,
    },
}

VENDOR_ORDER_TRANSITIONS: dict[VendorOrderStatus, set[VendorOrderStatus]] = {
    VendorOrderStatus.PENDING_CONFIRMATION: {
        VendorOrderStatus.CONFIRMED,
        VendorOrderStatus.CANCELLED,
    },
    VendorOrderStatus.CONFIRMED: {
        VendorOrderStatus.PREPARING,
        VendorOrderStatus.CANCELLED,
    },
    VendorOrderStatus.PREPARING: {
        VendorOrderStatus.READY_FOR_PICKUP,
        VendorOrderStatus.IN_TRANSIT,
        VendorOrderStatus.CANCELLED,
    },
    VendorOrderStatus.READY_FOR_PICKUP: {
        VendorOrderStatus.IN_TRANSIT,
        VendorOrderStatus.CANCELLED,
    },
    VendorOrderStatus.IN_TRANSIT: {
        VendorOrderStatus.DELIVERED,
        VendorOrderStatus.DISPUTED,
    },
    VendorOrderStatus.DELIVERED: {
        VendorOrderStatus.FULFILLED,
        VendorOrderStatus.DISPUTED,
    },
    VendorOrderStatus.DISPUTED: {
        VendorOrderStatus.DELIVERED,
        VendorOrderStatus.CANCELLED,
    },
}

FULFILLMENT_TRANSITIONS: dict[FulfillmentStatus, set[FulfillmentStatus]] = {
    FulfillmentStatus.PENDING: {
        FulfillmentStatus.PICKING,
        FulfillmentStatus.PACKED,
        FulfillmentStatus.SHIPPED,
    },
    FulfillmentStatus.PICKING: {
        FulfillmentStatus.PACKED,
    },
    FulfillmentStatus.PACKED: {
        FulfillmentStatus.SHIPPED,
    },
    FulfillmentStatus.SHIPPED: {
        FulfillmentStatus.IN_TRANSIT,
    },
    FulfillmentStatus.IN_TRANSIT: {
        FulfillmentStatus.OUT_FOR_DELIVERY,
        FulfillmentStatus.DELIVERED,
    },
    FulfillmentStatus.OUT_FOR_DELIVERY: {
        FulfillmentStatus.DELIVERED,
    },
    FulfillmentStatus.DELIVERED: {
        FulfillmentStatus.ACCEPTED,
        FulfillmentStatus.REJECTED,
        FulfillmentStatus.PARTIALLY_ACCEPTED,
    },
}

# Terminal statuses (no further transitions)
ORDER_TERMINAL_STATUSES: set[OrderStatus] = {
    OrderStatus.COMPLETED,
    OrderStatus.CANCELLED,
}

VENDOR_ORDER_TERMINAL_STATUSES: set[VendorOrderStatus] = {
    VendorOrderStatus.FULFILLED,
    VendorOrderStatus.CANCELLED,
}

FULFILLMENT_TERMINAL_STATUSES: set[FulfillmentStatus] = {
    FulfillmentStatus.ACCEPTED,
    FulfillmentStatus.REJECTED,
    FulfillmentStatus.PARTIALLY_ACCEPTED,
}

# ---------------------------------------------------------------------------
# Event type strings for the outbox
# ---------------------------------------------------------------------------

EVENT_ORDER_CREATED = "order.created"
EVENT_ORDER_CONFIRMED = "order.confirmed"
EVENT_ORDER_CANCELLED = "order.cancelled"
EVENT_ORDER_COMPLETED = "order.completed"
EVENT_VENDOR_ORDER_STATUS_UPDATED = "vendor_order.status_updated"
EVENT_FULFILLMENT_CREATED = "fulfillment.created"
EVENT_FULFILLMENT_STATUS_UPDATED = "fulfillment.status_updated"
