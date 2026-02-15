"""Pydantic v2 schemas for Order Management API endpoints."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import (
    DeliveryType,
    FulfillmentLineItemStatus,
    FulfillmentStatus,
    OrderStatus,
    VendorOrderStatus,
)

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class OrderCreate(BaseModel):
    rfq_id: uuid.UUID
    delivery_port: str | None = Field(None, max_length=10)
    vessel_imo: str | None = Field(None, max_length=10)
    vessel_name: str | None = Field(None, max_length=100)
    requested_delivery_date: date | None = None
    notes: str | None = None


class OrderCancelRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)


class VendorOrderStatusUpdate(BaseModel):
    new_status: VendorOrderStatus
    reason: str | None = Field(None, max_length=1000)


class FulfillmentItemCreate(BaseModel):
    line_item_id: uuid.UUID
    quantity: int = Field(..., gt=0)


class FulfillmentCreate(BaseModel):
    delivery_type: DeliveryType | None = None
    delivery_address: str | None = None
    carrier: str | None = Field(None, max_length=100)
    items: list[FulfillmentItemCreate] = Field(..., min_length=1)


class FulfillmentStatusUpdate(BaseModel):
    new_status: FulfillmentStatus
    reason: str | None = Field(None, max_length=1000)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class OrderLineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vendor_order_id: uuid.UUID
    product_id: uuid.UUID | None = None
    impa_code: str
    product_name: str
    quantity_ordered: int
    quantity_fulfilled: int
    quantity_accepted: int
    unit_price: Decimal
    line_total: Decimal
    status: FulfillmentLineItemStatus
    created_at: datetime
    updated_at: datetime


class FulfillmentItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fulfillment_id: uuid.UUID
    order_line_item_id: uuid.UUID
    status: FulfillmentLineItemStatus
    quantity_shipped: int
    quantity_delivered: int | None = None
    quantity_accepted: int | None = None
    quantity_rejected: int | None = None
    rejection_reason: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class FulfillmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fulfillment_number: str
    vendor_order_id: uuid.UUID
    status: FulfillmentStatus
    carrier: str | None = None
    tracking_number: str | None = None
    shipped_at: datetime | None = None
    estimated_delivery: datetime | None = None
    delivered_at: datetime | None = None
    delivery_type: DeliveryType | None = None
    delivery_address: str | None = None
    delivery_contact: str | None = None
    delivery_phone: str | None = None
    accepted_at: datetime | None = None
    accepted_by: str | None = None
    acceptance_notes: str | None = None
    items: list[FulfillmentItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class VendorOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vendor_order_number: str
    order_id: uuid.UUID
    supplier_id: uuid.UUID
    status: VendorOrderStatus
    amount: Decimal
    commission_rate: Decimal | None = None
    commission_amount: Decimal | None = None
    confirmed_at: datetime | None = None
    estimated_ready_date: date | None = None
    line_items: list[OrderLineItemResponse] = Field(default_factory=list)
    fulfillments: list[FulfillmentResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_number: str
    rfq_id: uuid.UUID | None = None
    buyer_org_id: uuid.UUID
    status: OrderStatus
    total_amount: Decimal
    currency: str
    delivery_port: str | None = None
    vessel_imo: str | None = None
    vessel_name: str | None = None
    requested_delivery_date: date | None = None
    payment_status: str | None = None
    payment_method: str | None = None
    payment_reference: str | None = None
    metadata_extra: dict = Field(default_factory=dict)
    vendor_orders: list[VendorOrderResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    total: int
    limit: int
    offset: int


class VendorOrderListResponse(BaseModel):
    items: list[VendorOrderResponse]
    total: int
    limit: int
    offset: int
