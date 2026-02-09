"""Pydantic v2 schemas for TCO module."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.models.enums import TcoCalculationStatus, TcoTemplateType

# ── Request schemas ──────────────────────────────────────────────────────────


class TcoConfigCreate(BaseModel):
    """Request to create a TCO configuration."""

    name: str = Field(..., max_length=100)
    template_type: TcoTemplateType = TcoTemplateType.COMMODITY
    weight_unit_price: Decimal = Field(default=Decimal("0.4000"), ge=0, le=1)
    weight_shipping: Decimal = Field(default=Decimal("0.1500"), ge=0, le=1)
    weight_lead_time: Decimal = Field(default=Decimal("0.1500"), ge=0, le=1)
    weight_quality: Decimal = Field(default=Decimal("0.1500"), ge=0, le=1)
    weight_payment_terms: Decimal = Field(default=Decimal("0.1000"), ge=0, le=1)
    weight_supplier_rating: Decimal = Field(default=Decimal("0.0500"), ge=0, le=1)
    is_default: bool = False

    @model_validator(mode="after")
    def validate_weights_sum(self) -> TcoConfigCreate:
        total = (
            self.weight_unit_price
            + self.weight_shipping
            + self.weight_lead_time
            + self.weight_quality
            + self.weight_payment_terms
            + self.weight_supplier_rating
        )
        if abs(total - Decimal("1.0")) >= Decimal("0.001"):
            raise ValueError(
                f"Weights must sum to 1.0 (got {total})"
            )
        return self


class TcoConfigUpdate(BaseModel):
    """Request to update a TCO configuration."""

    name: str | None = Field(default=None, max_length=100)
    template_type: TcoTemplateType | None = None
    weight_unit_price: Decimal | None = Field(default=None, ge=0, le=1)
    weight_shipping: Decimal | None = Field(default=None, ge=0, le=1)
    weight_lead_time: Decimal | None = Field(default=None, ge=0, le=1)
    weight_quality: Decimal | None = Field(default=None, ge=0, le=1)
    weight_payment_terms: Decimal | None = Field(default=None, ge=0, le=1)
    weight_supplier_rating: Decimal | None = Field(default=None, ge=0, le=1)
    is_default: bool | None = None
    is_active: bool | None = None


class TcoCalculationRequest(BaseModel):
    """Request to run a TCO calculation on an RFQ."""

    rfq_id: uuid.UUID
    configuration_id: uuid.UUID | None = None
    base_currency: str = Field(default="USD", max_length=3)
    missing_data_strategy: Literal["penalize", "neutral", "exclude"] = "penalize"


class TcoSplitOrderRequest(BaseModel):
    """Request to compute a split-order allocation."""

    calculation_id: uuid.UUID
    max_suppliers: int = Field(default=3, ge=2, le=10)
    min_allocation_percent: Decimal = Field(default=Decimal("10.0"), ge=Decimal("5"), le=Decimal("50"))


# ── Response schemas ─────────────────────────────────────────────────────────


class TcoConfigResponse(BaseModel):
    """Response for a TCO configuration."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    template_type: TcoTemplateType
    weight_unit_price: Decimal
    weight_shipping: Decimal
    weight_lead_time: Decimal
    weight_quality: Decimal
    weight_payment_terms: Decimal
    weight_supplier_rating: Decimal
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TcoTemplateResponse(BaseModel):
    """Response for a built-in industry template."""

    template_type: TcoTemplateType
    weight_unit_price: Decimal
    weight_shipping: Decimal
    weight_lead_time: Decimal
    weight_quality: Decimal
    weight_payment_terms: Decimal
    weight_supplier_rating: Decimal


class TcoFactorScore(BaseModel):
    """Individual factor score for a quote."""

    factor: str
    raw_value: float
    normalized_score: float = Field(ge=0, le=100)
    weight: Decimal
    weighted_score: float


class TcoQuoteResult(BaseModel):
    """TCO result for a single quote."""

    quote_id: uuid.UUID
    supplier_organization_id: uuid.UUID | None = None
    supplier_name: str | None = None
    total_score: float
    factor_scores: list[TcoFactorScore]
    rank: int


class TcoSplitAllocation(BaseModel):
    """A single supplier allocation in a split order."""

    quote_id: uuid.UUID
    supplier_name: str | None = None
    allocation_percent: Decimal
    allocated_items: list[str] = Field(default_factory=list)
    score: float


class TcoSplitOrderResult(BaseModel):
    """Result of a split-order optimization."""

    allocations: list[TcoSplitAllocation]
    total_blended_score: float
    strategy_notes: list[str] = Field(default_factory=list)


class TcoCalculationResponse(BaseModel):
    """Response for a TCO calculation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rfq_id: uuid.UUID
    configuration_id: uuid.UUID | None
    status: TcoCalculationStatus
    base_currency: str
    results: list[TcoQuoteResult] | None = None
    split_order_result: TcoSplitOrderResult | None = None
    created_at: datetime
    updated_at: datetime


class TcoAuditTrailEntry(BaseModel):
    """Response for a single audit trail entry."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    calculation_id: uuid.UUID
    rfq_id: uuid.UUID
    action: str
    actor_id: uuid.UUID
    actor_organization_id: uuid.UUID
    details: dict | None
    created_at: datetime


class TcoAuditTrailResponse(BaseModel):
    """Paginated response for audit trail entries."""

    items: list[TcoAuditTrailEntry]
    total: int


class CalculationListResponse(BaseModel):
    """List response for TCO calculations."""

    items: list[TcoCalculationResponse]
    total: int
