"""Pydantic v2 schemas for Delivery & Proof-of-Delivery API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import (
    DeliveryItemStatus,
    DeliveryPhotoType,
    DeliveryStatus,
    DeliveryType,
)

# ---------------------------------------------------------------------------
# Delivery Item schemas
# ---------------------------------------------------------------------------


class DeliveryItemRecordInput(BaseModel):
    """Per-item quantities submitted when recording a delivery."""

    delivery_item_id: uuid.UUID
    quantity_delivered: int = Field(..., ge=0)
    quantity_accepted: int | None = Field(None, ge=0)
    quantity_rejected: int | None = Field(None, ge=0)
    rejection_reason: str | None = Field(None, max_length=1000)
    notes: str | None = Field(None, max_length=1000)


class DeliveryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    delivery_id: uuid.UUID
    fulfillment_item_id: uuid.UUID
    order_line_item_id: uuid.UUID
    quantity_expected: int
    quantity_delivered: int | None = None
    quantity_accepted: int | None = None
    quantity_rejected: int = 0
    status: DeliveryItemStatus
    rejection_reason: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Delivery Photo schemas
# ---------------------------------------------------------------------------


class PhotoUploadRequest(BaseModel):
    """Request to generate an S3 presigned upload URL for a photo."""

    photo_type: DeliveryPhotoType = DeliveryPhotoType.DELIVERY
    file_name: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field("image/jpeg", max_length=50)
    delivery_item_id: uuid.UUID | None = None
    caption: str | None = Field(None, max_length=1000)


class PhotoUploadResponse(BaseModel):
    """Response containing the presigned URL and photo record."""

    photo_id: uuid.UUID
    upload_url: str
    s3_key: str
    s3_bucket: str


class DeliveryPhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    delivery_id: uuid.UUID
    delivery_item_id: uuid.UUID | None = None
    s3_key: str
    s3_bucket: str
    file_name: str | None = None
    content_type: str
    file_size_bytes: int | None = None
    photo_type: DeliveryPhotoType
    caption: str | None = None
    taken_at: datetime
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    uploaded_by: uuid.UUID | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Delivery schemas
# ---------------------------------------------------------------------------


class DeliveryCreate(BaseModel):
    """Create a new delivery linked to a fulfillment."""

    fulfillment_id: uuid.UUID
    delivery_type: DeliveryType | None = None
    estimated_arrival: datetime | None = None


class DeliveryDispatchRequest(BaseModel):
    """Optional data for dispatch action."""

    estimated_arrival: datetime | None = None


class DeliveryRecordRequest(BaseModel):
    """Record delivery evidence — GPS, receiver, signature, item quantities."""

    delivery_latitude: Decimal | None = Field(None, ge=-90, le=90)
    delivery_longitude: Decimal | None = Field(None, ge=-180, le=180)
    gps_accuracy_meters: Decimal | None = Field(None, ge=0)
    receiver_name: str = Field(..., min_length=1, max_length=200)
    receiver_designation: str | None = Field(None, max_length=100)
    receiver_contact: str | None = Field(None, max_length=50)
    signature_s3_key: str | None = Field(None, max_length=500)
    delivery_type: DeliveryType | None = None
    items: list[DeliveryItemRecordInput] = Field(default_factory=list)


class DeliveryAcceptRequest(BaseModel):
    """Buyer acceptance of a delivery."""

    notes: str | None = Field(None, max_length=2000)


class DisputeItemInput(BaseModel):
    """Item-level dispute detail."""

    delivery_item_id: uuid.UUID
    reason: str = Field(..., min_length=1, max_length=1000)


class DeliveryDisputeRequest(BaseModel):
    """Flag a delivery as disputed."""

    reason: str = Field(..., min_length=1, max_length=2000)
    items: list[DisputeItemInput] = Field(default_factory=list)


class DeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    delivery_number: str
    fulfillment_id: uuid.UUID
    vendor_order_id: uuid.UUID
    order_id: uuid.UUID
    organization_id: uuid.UUID
    status: DeliveryStatus
    dispatched_at: datetime | None = None
    dispatched_by: uuid.UUID | None = None
    estimated_arrival: datetime | None = None
    delivered_at: datetime | None = None
    delivered_by: uuid.UUID | None = None
    delivery_type: DeliveryType | None = None
    delivery_latitude: Decimal | None = None
    delivery_longitude: Decimal | None = None
    gps_accuracy_meters: Decimal | None = None
    receiver_name: str
    receiver_designation: str | None = None
    receiver_contact: str | None = None
    signature_s3_key: str | None = None
    signature_captured_at: datetime | None = None
    sla_target_time: datetime | None = None
    sla_met: bool | None = None
    delay_reason: str | None = None
    accepted_at: datetime | None = None
    accepted_by: uuid.UUID | None = None
    acceptance_notes: str | None = None
    disputed_at: datetime | None = None
    dispute_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class DeliveryDetailResponse(DeliveryResponse):
    """Delivery with items and photos included."""

    items: list[DeliveryItemResponse] = Field(default_factory=list)
    photos: list[DeliveryPhotoResponse] = Field(default_factory=list)


class DeliveryListResponse(BaseModel):
    items: list[DeliveryResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# SLA Config schemas
# ---------------------------------------------------------------------------


class DeliverySlaConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    buyer_org_id: uuid.UUID
    supplier_org_id: uuid.UUID
    port_code: str | None = None
    delivery_window_hours: int
    max_delay_hours: int
    late_delivery_penalty_percent: Decimal | None = None
    no_show_penalty_percent: Decimal | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
