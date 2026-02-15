"""Pydantic v2 schemas for Invoice & Settlement API endpoints."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import InvoiceStatus, SettlementPeriodStatus, SettlementPeriodType


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class InvoiceMarkPaidRequest(BaseModel):
    paid_reference: str | None = Field(None, max_length=200)
    notes: str | None = Field(None, max_length=1000)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class InvoiceLineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_id: uuid.UUID
    order_line_item_id: uuid.UUID
    delivery_item_id: uuid.UUID | None = None
    dispute_id: uuid.UUID | None = None
    impa_code: str | None = None
    product_name: str
    description: str | None = None
    quantity_ordered: int
    quantity_delivered: int
    quantity_accepted: int
    quantity_rejected: int
    unit_price: Decimal
    line_subtotal: Decimal
    credit_amount: Decimal
    line_total: Decimal
    notes: str | None = None
    created_at: datetime


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_number: str
    organization_id: uuid.UUID
    order_id: uuid.UUID
    vendor_order_id: uuid.UUID
    delivery_id: uuid.UUID | None = None
    settlement_period_id: uuid.UUID | None = None
    buyer_org_id: uuid.UUID
    supplier_org_id: uuid.UUID
    status: InvoiceStatus
    subtotal: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    credit_adjustment: Decimal
    total_amount: Decimal
    currency: str
    buyer_po_number: str | None = None
    supplier_invoice_ref: str | None = None
    invoice_date: date
    due_date: date | None = None
    sent_at: datetime | None = None
    acknowledged_at: datetime | None = None
    paid_at: datetime | None = None
    paid_reference: str | None = None
    notes: str | None = None
    internal_notes: str | None = None
    line_items: list[InvoiceLineItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class InvoiceListResponse(BaseModel):
    items: list[InvoiceResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Reconciliation schemas
# ---------------------------------------------------------------------------


class ReconciliationLineItem(BaseModel):
    order_line_item_id: uuid.UUID
    impa_code: str | None = None
    product_name: str
    quantity_ordered: int
    quantity_delivered: int
    quantity_accepted: int
    quantity_rejected: int
    unit_price: Decimal
    ordered_total: Decimal
    delivered_total: Decimal
    invoiced_total: Decimal
    credit_amount: Decimal
    variance: Decimal


class ReconciliationResponse(BaseModel):
    invoice_id: uuid.UUID
    invoice_number: str
    order_id: uuid.UUID
    delivery_id: uuid.UUID | None = None
    line_items: list[ReconciliationLineItem]
    ordered_total: Decimal
    delivered_total: Decimal
    invoiced_total: Decimal
    total_credits: Decimal
    net_variance: Decimal


# ---------------------------------------------------------------------------
# Settlement schemas
# ---------------------------------------------------------------------------


class SettlementPeriodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    period_type: SettlementPeriodType
    period_start: date
    period_end: date
    period_label: str | None = None
    total_invoices: int
    total_amount: Decimal
    total_credits: Decimal
    net_amount: Decimal
    status: SettlementPeriodStatus
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SettlementListResponse(BaseModel):
    items: list[SettlementPeriodResponse]
    total: int
    limit: int
    offset: int
