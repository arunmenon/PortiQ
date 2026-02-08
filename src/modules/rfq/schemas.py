"""Pydantic v2 schemas for RFQ & Bidding API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import (
    AuctionType,
    InvitationStatus,
    QuoteStatus,
    RfqStatus,
    RfqTransitionType,
)

# ---------------------------------------------------------------------------
# RFQ Line Item schemas
# ---------------------------------------------------------------------------


class RfqLineItemCreate(BaseModel):
    line_number: int = Field(..., ge=1)
    product_id: uuid.UUID | None = None
    impa_code: str | None = Field(None, max_length=10)
    description: str = Field(..., min_length=1, max_length=500)
    quantity: Decimal = Field(..., gt=0)
    unit_of_measure: str = Field(..., min_length=1, max_length=20)
    specifications: dict | None = None
    notes: str | None = Field(None, max_length=500)


class RfqLineItemUpdate(BaseModel):
    product_id: uuid.UUID | None = None
    impa_code: str | None = Field(None, max_length=10)
    description: str | None = Field(None, min_length=1, max_length=500)
    quantity: Decimal | None = Field(None, gt=0)
    unit_of_measure: str | None = Field(None, min_length=1, max_length=20)
    specifications: dict | None = None
    notes: str | None = Field(None, max_length=500)


class RfqLineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rfq_id: uuid.UUID
    line_number: int
    product_id: uuid.UUID | None = None
    impa_code: str | None = None
    description: str
    quantity: Decimal
    unit_of_measure: str
    specifications: dict | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# RFQ schemas
# ---------------------------------------------------------------------------


class RfqCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    auction_type: AuctionType = AuctionType.SEALED_BID
    currency: str = Field("USD", max_length=3)
    vessel_id: uuid.UUID | None = None
    delivery_port: str | None = Field(None, max_length=10)
    delivery_date: datetime | None = None
    bidding_deadline: datetime | None = None
    allow_partial_quotes: bool = False
    allow_quote_revision: bool = True
    require_all_line_items: bool = False
    notes: str | None = None
    line_items: list[RfqLineItemCreate] = Field(default_factory=list)


class RfqUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    auction_type: AuctionType | None = None
    currency: str | None = Field(None, max_length=3)
    vessel_id: uuid.UUID | None = None
    delivery_port: str | None = Field(None, max_length=10)
    delivery_date: datetime | None = None
    bidding_deadline: datetime | None = None
    allow_partial_quotes: bool | None = None
    allow_quote_revision: bool | None = None
    require_all_line_items: bool | None = None
    notes: str | None = None


class RfqResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference_number: str
    buyer_organization_id: uuid.UUID
    title: str
    description: str | None = None
    status: RfqStatus
    auction_type: AuctionType
    currency: str
    vessel_id: uuid.UUID | None = None
    delivery_port: str | None = None
    delivery_date: datetime | None = None
    bidding_start: datetime | None = None
    bidding_deadline: datetime | None = None
    allow_partial_quotes: bool
    allow_quote_revision: bool
    require_all_line_items: bool
    awarded_quote_id: uuid.UUID | None = None
    awarded_supplier_id: uuid.UUID | None = None
    awarded_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None
    notes: str | None = None
    metadata_extra: dict = Field(default_factory=dict)
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    line_items: list[RfqLineItemResponse] = Field(default_factory=list)


class RfqListResponse(BaseModel):
    items: list[RfqResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Invitation schemas
# ---------------------------------------------------------------------------


class InvitationCreate(BaseModel):
    supplier_organization_ids: list[uuid.UUID] = Field(..., min_length=1)


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rfq_id: uuid.UUID
    supplier_organization_id: uuid.UUID
    status: InvitationStatus
    invited_by: uuid.UUID
    invited_at: datetime
    responded_at: datetime | None = None
    decline_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class InvitationRespondRequest(BaseModel):
    accept: bool
    decline_reason: str | None = Field(None, max_length=500)


# ---------------------------------------------------------------------------
# Quote Line Item schemas
# ---------------------------------------------------------------------------


class QuoteLineItemCreate(BaseModel):
    rfq_line_item_id: uuid.UUID
    unit_price: Decimal = Field(..., ge=0)
    quantity: Decimal = Field(..., gt=0)
    total_price: Decimal = Field(..., ge=0)
    lead_time_days: int | None = Field(None, ge=0)
    notes: str | None = Field(None, max_length=500)


class QuoteLineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quote_id: uuid.UUID
    rfq_line_item_id: uuid.UUID
    unit_price: Decimal
    quantity: Decimal
    total_price: Decimal
    lead_time_days: int | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Quote schemas
# ---------------------------------------------------------------------------


class QuoteCreate(BaseModel):
    currency: str = Field("USD", max_length=3)
    valid_until: datetime | None = None
    delivery_port: str | None = Field(None, max_length=10)
    estimated_delivery_days: int | None = Field(None, ge=0)
    payment_terms: str | None = Field(None, max_length=255)
    shipping_terms: str | None = Field(None, max_length=255)
    warranty_terms: str | None = Field(None, max_length=500)
    notes: str | None = None
    line_items: list[QuoteLineItemCreate] = Field(default_factory=list)


class QuoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rfq_id: uuid.UUID
    supplier_organization_id: uuid.UUID
    status: QuoteStatus
    version: int
    total_amount: Decimal | None = None
    currency: str
    valid_until: datetime | None = None
    delivery_port: str | None = None
    estimated_delivery_days: int | None = None
    payment_terms: str | None = None
    shipping_terms: str | None = None
    warranty_terms: str | None = None
    price_rank: int | None = None
    is_complete: bool
    notes: str | None = None
    metadata_extra: dict = Field(default_factory=dict)
    submitted_by: uuid.UUID | None = None
    submitted_at: datetime | None = None
    withdrawn_at: datetime | None = None
    withdrawal_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    line_items: list[QuoteLineItemResponse] = Field(default_factory=list)


class QuoteListResponse(BaseModel):
    items: list[QuoteResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Transition schemas
# ---------------------------------------------------------------------------


class TransitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rfq_id: uuid.UUID
    from_status: RfqStatus
    to_status: RfqStatus
    transition_type: RfqTransitionType
    triggered_by: uuid.UUID | None = None
    trigger_source: str
    reason: str | None = None
    metadata_extra: dict = Field(default_factory=dict)
    created_at: datetime


# ---------------------------------------------------------------------------
# Action request schemas
# ---------------------------------------------------------------------------


class AwardRequest(BaseModel):
    quote_id: uuid.UUID


class CancelRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)


class PublishResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference_number: str
    status: RfqStatus
    bidding_start: datetime | None = None
    bidding_deadline: datetime | None = None
