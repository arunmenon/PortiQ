"""TCO Engine API router — configuration, calculation, and comparison endpoints."""

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.exceptions import ForbiddenException, NotFoundException
from src.models.rfq import Rfq
from src.models.tco_audit_trail import TcoAuditTrail
from src.modules.tco.comparison import QuoteComparisonService
from src.modules.tco.config_service import TcoConfigService
from src.modules.tco.engine import TcoEngineService
from src.modules.tco.schemas import (
    CalculationListResponse,
    TcoAuditTrailEntry,
    TcoAuditTrailResponse,
    TcoCalculationRequest,
    TcoCalculationResponse,
    TcoConfigCreate,
    TcoConfigResponse,
    TcoConfigUpdate,
    TcoSplitOrderRequest,
    TcoTemplateResponse,
)
from src.modules.tenancy.auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/tco", tags=["TCO Engine"])


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _verify_rfq_access(
    rfq_id: uuid.UUID,
    user: AuthenticatedUser,
    db: AsyncSession,
) -> Rfq:
    """Verify the user has access to the RFQ (owner org or platform admin)."""
    result = await db.execute(select(Rfq).where(Rfq.id == rfq_id))
    rfq = result.scalar_one_or_none()
    if rfq is None:
        raise NotFoundException(f"RFQ {rfq_id} not found")
    if not user.is_platform_admin and rfq.buyer_organization_id != user.organization_id:
        raise ForbiddenException("You do not have access to this RFQ")
    return rfq


def _require_buyer_or_platform(user: AuthenticatedUser) -> None:
    """Check that the user is from a BUYER or PLATFORM organization."""
    if user.organization_type not in ("BUYER", "PLATFORM", "BOTH"):
        raise ForbiddenException("TCO configurations are available to buyer organizations only")


# ── 1. POST /tco/configurations ──────────────────────────────────────────


@router.post("/configurations", response_model=TcoConfigResponse, status_code=201)
async def create_configuration(
    body: TcoConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TcoConfigResponse:
    """Create a new TCO weight configuration."""
    _require_buyer_or_platform(current_user)
    service = TcoConfigService(db)
    config = await service.create_config(current_user.organization_id, body)
    return TcoConfigResponse.model_validate(config)


# ── 2. GET /tco/configurations ───────────────────────────────────────────


@router.get("/configurations", response_model=list[TcoConfigResponse])
async def list_configurations(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[TcoConfigResponse]:
    """List all TCO configurations for the current organization."""
    _require_buyer_or_platform(current_user)
    service = TcoConfigService(db)
    configs = await service.list_configs(current_user.organization_id)
    return [TcoConfigResponse.model_validate(c) for c in configs]


# ── 3. GET /tco/configurations/{config_id} ───────────────────────────────


@router.get("/configurations/{config_id}", response_model=TcoConfigResponse)
async def get_configuration(
    config_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TcoConfigResponse:
    """Get a single TCO configuration."""
    _require_buyer_or_platform(current_user)
    service = TcoConfigService(db)
    config = await service.get_config(config_id)
    if not current_user.is_platform_admin and config.organization_id != current_user.organization_id:
        raise ForbiddenException("You do not have access to this configuration")
    return TcoConfigResponse.model_validate(config)


# ── 4. PATCH /tco/configurations/{config_id} ─────────────────────────────


@router.patch("/configurations/{config_id}", response_model=TcoConfigResponse)
async def update_configuration(
    config_id: uuid.UUID,
    body: TcoConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TcoConfigResponse:
    """Update a TCO configuration."""
    _require_buyer_or_platform(current_user)
    service = TcoConfigService(db)
    config = await service.update_config(
        config_id, current_user.organization_id, body
    )
    return TcoConfigResponse.model_validate(config)


# ── 5. GET /tco/templates ────────────────────────────────────────────────


@router.get("/templates", response_model=list[TcoTemplateResponse])
async def list_templates(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[TcoTemplateResponse]:
    """List built-in industry TCO weight templates."""
    from src.modules.tco.config_service import TcoConfigService

    service = TcoConfigService(None)  # type: ignore[arg-type]
    return service.get_templates()


# ── 6. POST /tco/rfqs/{rfq_id}/calculate ────────────────────────────────


@router.post(
    "/rfqs/{rfq_id}/calculate",
    response_model=TcoCalculationResponse,
    status_code=201,
)
async def calculate_tco(
    rfq_id: uuid.UUID,
    body: TcoCalculationRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TcoCalculationResponse:
    """Trigger a TCO calculation for an RFQ."""
    await _verify_rfq_access(rfq_id, current_user, db)
    engine = TcoEngineService(db)
    calculation = await engine.calculate_tco(
        rfq_id=rfq_id,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        configuration_id=body.configuration_id if body else None,
        base_currency=body.base_currency if body else "USD",
        missing_data_strategy=body.missing_data_strategy if body else "penalize",
    )
    return TcoCalculationResponse.model_validate(calculation)


# ── 7. GET /tco/rfqs/{rfq_id}/calculations ──────────────────────────────


@router.get(
    "/rfqs/{rfq_id}/calculations",
    response_model=CalculationListResponse,
)
async def list_calculations(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> CalculationListResponse:
    """List all TCO calculations for an RFQ."""
    await _verify_rfq_access(rfq_id, current_user, db)
    service = QuoteComparisonService(db)
    calculations = await service.list_calculations(rfq_id)
    return CalculationListResponse(
        items=[TcoCalculationResponse.model_validate(c) for c in calculations],
        total=len(calculations),
    )


# ── 8. GET /tco/rfqs/{rfq_id}/calculations/{calculation_id} ─────────────


@router.get(
    "/rfqs/{rfq_id}/calculations/{calculation_id}",
    response_model=TcoCalculationResponse,
)
async def get_calculation(
    rfq_id: uuid.UUID,
    calculation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TcoCalculationResponse:
    """Get a specific TCO calculation with results."""
    await _verify_rfq_access(rfq_id, current_user, db)
    service = QuoteComparisonService(db)
    calculation = await service.get_calculation(calculation_id)
    if calculation.rfq_id != rfq_id:
        from src.exceptions import NotFoundException

        raise NotFoundException("Calculation not found for this RFQ")
    return TcoCalculationResponse.model_validate(calculation)


# ── 9. POST /tco/rfqs/{rfq_id}/calculations/{calculation_id}/split-order ─


@router.post(
    "/rfqs/{rfq_id}/calculations/{calculation_id}/split-order",
    response_model=TcoCalculationResponse,
)
async def generate_split_order(
    rfq_id: uuid.UUID,
    calculation_id: uuid.UUID,
    body: TcoSplitOrderRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TcoCalculationResponse:
    """Generate a split-order optimization for a calculation."""
    await _verify_rfq_access(rfq_id, current_user, db)
    # Verify calculation belongs to this RFQ
    comparison_svc = QuoteComparisonService(db)
    existing = await comparison_svc.get_calculation(calculation_id)
    if existing.rfq_id != rfq_id:
        from src.exceptions import NotFoundException

        raise NotFoundException("Calculation not found for this RFQ")
    engine = TcoEngineService(db)
    calculation = await engine.generate_split_order(
        calculation_id=calculation_id,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        max_suppliers=body.max_suppliers if body else 3,
        min_allocation_percent=body.min_allocation_percent if body else Decimal("10.0"),
    )
    return TcoCalculationResponse.model_validate(calculation)


# ── 10. GET /tco/rfqs/{rfq_id}/audit-trail ──────────────────────────────


@router.get(
    "/rfqs/{rfq_id}/audit-trail",
    response_model=TcoAuditTrailResponse,
)
async def get_audit_trail(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TcoAuditTrailResponse:
    """Get audit trail for all TCO calculations on an RFQ."""
    await _verify_rfq_access(rfq_id, current_user, db)
    result = await db.execute(
        select(TcoAuditTrail)
        .where(TcoAuditTrail.rfq_id == rfq_id)
        .order_by(TcoAuditTrail.created_at.desc())
    )
    entries = list(result.scalars().all())
    return TcoAuditTrailResponse(
        items=[TcoAuditTrailEntry.model_validate(e) for e in entries],
        total=len(entries),
    )
