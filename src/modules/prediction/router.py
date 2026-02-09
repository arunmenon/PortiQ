"""Prediction Service API router — 6 endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.modules.prediction.co_occurrence import CoOccurrenceService
from src.modules.prediction.consumption_engine import ConsumptionEngine
from src.modules.prediction.reorder_service import ReorderService
from src.modules.prediction.schemas import (
    CoOccurrenceRequest,
    CoOccurrenceSuggestion,
    PredictedItem,
    PredictionRequest,
    ReorderRequest,
    ReorderSuggestion,
    TemplateApplyRequest,
    TemplateResponse,
)
from src.modules.prediction.template_service import TemplateService
from src.modules.tenancy.auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/predictions", tags=["predictions"])


# ---------------------------------------------------------------------------
# Consumption prediction
# ---------------------------------------------------------------------------


@router.post("/suggest", response_model=list[PredictedItem])
async def suggest_quantities(
    body: PredictionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[PredictedItem]:
    """Predict consumption quantities for a vessel voyage.

    Uses rule-based consumption rates per IMPA category, adjusted by
    vessel type multipliers and safety buffers.  When the vessel has
    sufficient historical data, predictions are blended with past
    order patterns.
    """
    engine = ConsumptionEngine(db)
    return await engine.predict_quantities(
        vessel_id=body.vessel_id,
        voyage_days=body.voyage_days,
        crew_size=body.crew_size,
        categories=body.categories,
    )


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


@router.get("/templates", response_model=list[TemplateResponse])
async def list_templates(
    vessel_type: str | None = Query(None, description="Filter by vessel type"),
    voyage_days: int | None = Query(None, gt=0, description="Filter by voyage duration"),
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[TemplateResponse]:
    """List procurement templates applicable to the given vessel type and voyage."""
    svc = TemplateService(db)
    return await svc.get_templates(vessel_type=vessel_type, voyage_days=voyage_days)


@router.post("/templates/apply", response_model=list[PredictedItem])
async def apply_template(
    body: TemplateApplyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[PredictedItem]:
    """Apply a procurement template to a vessel voyage.

    Resolves the template's categories and runs the consumption engine
    to produce predicted quantities.
    """
    svc = TemplateService(db)
    return await svc.apply_template(
        template_id=body.template_id,
        vessel_id=body.vessel_id,
        voyage_days=body.voyage_days,
        crew_size=body.crew_size,
    )


# ---------------------------------------------------------------------------
# Reorder
# ---------------------------------------------------------------------------


@router.get("/reorder", response_model=ReorderSuggestion | None)
async def get_last_order(
    vessel_id: uuid.UUID = Query(..., description="Vessel UUID"),
    port: str | None = Query(None, max_length=10, description="Port filter (UN/LOCODE)"),
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ReorderSuggestion | None:
    """Find the most recent completed RFQ for a vessel (optionally at a port).

    Returns the RFQ's line items as reorder suggestions.
    """
    svc = ReorderService(db)
    return await svc.get_last_order(vessel_id=vessel_id, port=port)


@router.post("/reorder/copy", response_model=list[PredictedItem])
async def copy_from_rfq(
    body: ReorderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[PredictedItem]:
    """Copy line items from a specific RFQ, optionally adjusting quantities.

    Provide ``source_rfq_id`` to copy from a specific RFQ, or ``vessel_id``
    to use the most recent completed order.  ``voyage_days`` and ``crew_size``
    are optional scaling parameters.
    """
    svc = ReorderService(db)

    if body.source_rfq_id is not None:
        return await svc.copy_from_rfq(
            source_rfq_id=body.source_rfq_id,
            voyage_days=body.voyage_days,
            crew_size=body.crew_size,
        )

    # Fall back to finding the last order for the vessel
    if body.vessel_id is None:
        return []

    suggestion = await svc.get_last_order(vessel_id=body.vessel_id, port=body.port)
    if suggestion is None:
        return []

    # If adjustment params provided, copy-from-rfq with adjustments
    if body.voyage_days is not None or body.crew_size is not None:
        return await svc.copy_from_rfq(
            source_rfq_id=suggestion.source_rfq_id,
            voyage_days=body.voyage_days,
            crew_size=body.crew_size,
        )

    return suggestion.line_items


# ---------------------------------------------------------------------------
# Co-occurrence
# ---------------------------------------------------------------------------


@router.post("/co-occurrences", response_model=list[CoOccurrenceSuggestion])
async def get_co_occurrences(
    body: CoOccurrenceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[CoOccurrenceSuggestion]:
    """Find items that frequently co-occur with the given IMPA codes.

    Uses association rule mining (lift score) on historical RFQ data
    to suggest "frequently bought together" items.
    """
    svc = CoOccurrenceService(db)
    return await svc.get_suggestions(
        current_impa_codes=body.impa_codes,
        min_lift=body.min_lift,
    )
