"""Pydantic v2 schemas for Market Intelligence API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Price Benchmark schemas
# ---------------------------------------------------------------------------


class PriceBenchmark(BaseModel):
    """Price percentiles for a single IMPA code over a given period."""

    model_config = ConfigDict(from_attributes=True)

    impa_code: str
    p25: Decimal | None = None
    p50: Decimal | None = None
    p75: Decimal | None = None
    quote_count: int = 0
    has_data: bool = False
    currency: str = "USD"
    period_days: int = 90


class BudgetEstimate(BaseModel):
    """Aggregated budget estimate across all line items."""

    low: Decimal = Decimal("0")
    likely: Decimal = Decimal("0")
    high: Decimal = Decimal("0")
    items_with_data: int = 0
    items_without_data: int = 0
    currency: str = "USD"


# ---------------------------------------------------------------------------
# Supplier Matching schemas
# ---------------------------------------------------------------------------


class SupplierMatch(BaseModel):
    """A single matched supplier with score breakdown."""

    supplier_id: uuid.UUID
    organization_id: uuid.UUID
    organization_name: str
    tier: str
    score: float
    coverage_score: float
    is_recommended: bool = False


class SupplierMatchResult(BaseModel):
    """Full supplier matching result with recommendations."""

    total_count: int = 0
    verified_plus_count: int = 0
    recommended: list[SupplierMatch] = Field(default_factory=list)
    other: list[SupplierMatch] = Field(default_factory=list)
    single_source_risk: bool = False


# ---------------------------------------------------------------------------
# Risk Analysis schemas
# ---------------------------------------------------------------------------


class RiskFlag(BaseModel):
    """A single identified risk with severity and context."""

    risk_type: str
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    message: str
    details: dict | None = None


# ---------------------------------------------------------------------------
# Timing Advice schemas
# ---------------------------------------------------------------------------


class TimingAdvice(BaseModel):
    """Timing recommendations for procurement action."""

    recommendation: str
    optimal_window_days: int = 0
    vessel_eta: datetime | None = None
    timeline_assessment: Literal["sufficient", "tight", "risky"] = "sufficient"
    avg_response_days: float | None = None


# ---------------------------------------------------------------------------
# Combined Intelligence Request / Response
# ---------------------------------------------------------------------------


class IntelligenceResponse(BaseModel):
    """Combined intelligence response containing all analysis sections."""

    suppliers: SupplierMatchResult | None = None
    price_benchmarks: list[PriceBenchmark] = Field(default_factory=list)
    budget_estimate: BudgetEstimate | None = None
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    timing: TimingAdvice | None = None
