"""Pydantic v2 schemas for the Prediction Service API endpoints."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Core response schemas
# ---------------------------------------------------------------------------


class PredictedItem(BaseModel):
    """A single predicted line item with quantity and confidence."""

    model_config = ConfigDict(from_attributes=True)

    impa_code: str = Field(..., description="6-digit IMPA code")
    product_id: uuid.UUID | None = Field(None, description="Catalog product UUID if matched")
    description: str = Field(..., description="Product/item description")
    quantity: Decimal = Field(..., ge=0, description="Predicted quantity")
    unit: str = Field(..., description="Unit of measure (KG, PIECE, L, M)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence 0-1")
    category_prefix: str = Field(..., description="2-digit IMPA category prefix")


class TemplateResponse(BaseModel):
    """Template metadata returned when listing available templates."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Template identifier (e.g. TANKER, DRYDOCK)")
    name: str = Field(..., description="Human-readable template name")
    description: str = Field(..., description="Template description")
    vessel_types: list[str] = Field(
        default_factory=list, description="Applicable vessel types"
    )
    categories: list[str] = Field(
        default_factory=list, description="IMPA category prefixes included"
    )
    voyage_type: str | None = Field(
        None, description="Voyage type if this is a voyage-based template"
    )


class ReorderSuggestion(BaseModel):
    """Reorder suggestion based on a previous RFQ."""

    model_config = ConfigDict(from_attributes=True)

    source_rfq_id: uuid.UUID = Field(..., description="ID of the source RFQ")
    source_rfq_reference: str = Field(..., description="Reference number of source RFQ")
    created_at: datetime = Field(..., description="When the source RFQ was created")
    delivery_port: str | None = Field(None, description="Delivery port of source RFQ")
    line_items: list[PredictedItem] = Field(
        default_factory=list, description="Line items from source RFQ"
    )
    quantity_adjustments: dict[str, str] = Field(
        default_factory=dict,
        description="Map of IMPA code -> adjustment description",
    )


class CoOccurrenceSuggestion(BaseModel):
    """A co-occurrence suggestion (items frequently ordered together)."""

    model_config = ConfigDict(from_attributes=True)

    impa_code: str = Field(..., description="IMPA code of suggested item")
    product_id: uuid.UUID | None = Field(None, description="Catalog product UUID if matched")
    description: str = Field(..., description="Product description")
    lift_score: float = Field(..., description="Association lift score")
    support_count: int = Field(..., ge=0, description="Number of RFQs containing this pair")
    co_occurs_with: list[str] = Field(
        default_factory=list,
        description="IMPA codes in the input that this item co-occurs with",
    )


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class PredictionRequest(BaseModel):
    """Request body for consumption quantity prediction."""

    vessel_id: uuid.UUID = Field(..., description="Target vessel UUID")
    voyage_days: int = Field(..., gt=0, description="Planned voyage duration in days")
    crew_size: int = Field(..., gt=0, description="Number of crew members")
    categories: list[str] | None = Field(
        None,
        description="Optional list of 2-digit IMPA category prefixes to predict for",
    )

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            for cat in v:
                if not re.match(r"^\d{2}$", cat):
                    raise ValueError(f"Invalid category prefix: {cat}. Must be 2 digits.")
        return v


class TemplateApplyRequest(BaseModel):
    """Request body for applying a template."""

    template_id: str = Field(
        ..., description="Template ID (vessel type, voyage type, or event key)"
    )
    vessel_id: uuid.UUID = Field(..., description="Target vessel UUID")
    voyage_days: int = Field(..., gt=0, description="Planned voyage duration in days")
    crew_size: int = Field(..., gt=0, description="Number of crew members")


class ReorderRequest(BaseModel):
    """Request body for copying/reordering from a previous RFQ."""

    vessel_id: uuid.UUID | None = Field(
        None, description="Vessel UUID to find last order for"
    )
    port: str | None = Field(None, max_length=10, description="Optional port filter (UN/LOCODE)")
    source_rfq_id: uuid.UUID | None = Field(
        None, description="Specific RFQ to copy from"
    )
    voyage_days: int | None = Field(
        None, gt=0, description="New voyage days for quantity adjustment"
    )
    crew_size: int | None = Field(
        None, gt=0, description="New crew size for quantity adjustment"
    )

    @model_validator(mode="after")
    def require_identifier(self) -> ReorderRequest:
        if self.vessel_id is None and self.source_rfq_id is None:
            raise ValueError("Either vessel_id or source_rfq_id must be provided")
        return self


class CoOccurrenceRequest(BaseModel):
    """Request body for co-occurrence suggestions."""

    impa_codes: list[str] = Field(
        ..., min_length=1, max_length=50, description="Current IMPA codes in the requisition"
    )
    min_lift: float = Field(
        2.0, gt=0.0, description="Minimum association lift score"
    )

    @field_validator("impa_codes")
    @classmethod
    def validate_impa_codes(cls, v: list[str]) -> list[str]:
        for code in v:
            if not re.match(r"^\d{6}$", code):
                raise ValueError(f"Invalid IMPA code format: {code}. Must be 6 digits.")
        return v
