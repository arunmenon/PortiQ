"""Market Intelligence API router — 5 endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.modules.intelligence.price_benchmark_service import PriceBenchmarkService
from src.modules.intelligence.risk_analyzer import RiskAnalyzer
from src.modules.intelligence.schemas import (
    IntelligenceResponse,
    PriceBenchmark,
    RiskFlag,
    SupplierMatchResult,
    TimingAdvice,
)
from src.modules.intelligence.supplier_matching import SupplierMatchingService
from src.modules.intelligence.timing_advisor import TimingAdvisor
from src.modules.tenancy.auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


# ---------------------------------------------------------------------------
# Combined endpoint
# ---------------------------------------------------------------------------


@router.get("/", response_model=IntelligenceResponse)
async def get_intelligence(
    delivery_port: str | None = Query(None, max_length=10),
    impa_codes: str | None = Query(None, description="Comma-separated IMPA codes"),
    vessel_id: uuid.UUID | None = Query(None),
    delivery_date: datetime | None = Query(None),
    bidding_deadline: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> IntelligenceResponse:
    """Single debounced intelligence endpoint.

    Returns all intelligence sections based on which parameters are provided.
    Each section is optional — only populated when relevant params are given.
    """
    buyer_organization_id = current_user.organization_id

    parsed_impa_codes = (
        [code.strip() for code in impa_codes.split(",") if code.strip()]
        if impa_codes
        else None
    )

    response = IntelligenceResponse()

    # Price Benchmarks — requires impa_codes
    if parsed_impa_codes:
        benchmark_svc = PriceBenchmarkService(db)
        response.price_benchmarks = await benchmark_svc.get_price_benchmarks(
            impa_codes=parsed_impa_codes,
            delivery_port=delivery_port,
        )
        response.budget_estimate = await benchmark_svc.estimate_budget(
            line_items=[
                {"impa_code": code, "quantity": 1} for code in parsed_impa_codes
            ],
            delivery_port=delivery_port,
        )

    # Supplier Matching — requires delivery_port
    if delivery_port:
        matching_svc = SupplierMatchingService(db)
        response.suppliers = await matching_svc.match_suppliers(
            delivery_port=delivery_port,
            impa_codes=parsed_impa_codes,
            buyer_organization_id=buyer_organization_id,
        )

    # Risk Analysis — requires at least one parameter
    if delivery_port or parsed_impa_codes or delivery_date:
        risk_svc = RiskAnalyzer(db)
        response.risk_flags = await risk_svc.analyze_risks(
            delivery_port=delivery_port,
            delivery_date=delivery_date,
            vessel_id=vessel_id,
            impa_codes=parsed_impa_codes,
            bidding_deadline=bidding_deadline,
            buyer_organization_id=buyer_organization_id,
        )

    # Timing Advice — requires delivery_port or delivery_date or vessel_id
    if delivery_port or delivery_date or vessel_id:
        timing_svc = TimingAdvisor(db)
        response.timing = await timing_svc.get_timing_advice(
            delivery_port=delivery_port,
            delivery_date=delivery_date,
            bidding_deadline=bidding_deadline,
            vessel_id=vessel_id,
        )

    return response


# ---------------------------------------------------------------------------
# Standalone endpoints
# ---------------------------------------------------------------------------


@router.get("/price-benchmarks", response_model=list[PriceBenchmark])
async def get_price_benchmarks(
    impa_codes: str = Query(..., description="Comma-separated IMPA codes"),
    delivery_port: str | None = Query(None, max_length=10),
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[PriceBenchmark]:
    """Get price percentiles for specified IMPA codes."""
    parsed_codes = [code.strip() for code in impa_codes.split(",") if code.strip()]
    svc = PriceBenchmarkService(db)
    return await svc.get_price_benchmarks(
        impa_codes=parsed_codes,
        delivery_port=delivery_port,
        days=days,
    )


@router.get("/suppliers", response_model=SupplierMatchResult)
async def match_suppliers(
    delivery_port: str = Query(..., max_length=10),
    impa_codes: str | None = Query(None, description="Comma-separated IMPA codes"),
    min_tier: str = Query("VERIFIED"),
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> SupplierMatchResult:
    """Find and rank suppliers for a given delivery port and requirements."""
    parsed_codes = (
        [code.strip() for code in impa_codes.split(",") if code.strip()]
        if impa_codes
        else None
    )
    svc = SupplierMatchingService(db)
    return await svc.match_suppliers(
        delivery_port=delivery_port,
        impa_codes=parsed_codes,
        buyer_organization_id=current_user.organization_id,
        min_tier=min_tier,
    )


@router.get("/risks", response_model=list[RiskFlag])
async def analyze_risks(
    delivery_port: str | None = Query(None, max_length=10),
    delivery_date: datetime | None = Query(None),
    vessel_id: uuid.UUID | None = Query(None),
    impa_codes: str | None = Query(None, description="Comma-separated IMPA codes"),
    bidding_deadline: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[RiskFlag]:
    """Identify procurement risks for the given context."""
    parsed_codes = (
        [code.strip() for code in impa_codes.split(",") if code.strip()]
        if impa_codes
        else None
    )
    svc = RiskAnalyzer(db)
    return await svc.analyze_risks(
        delivery_port=delivery_port,
        delivery_date=delivery_date,
        vessel_id=vessel_id,
        impa_codes=parsed_codes,
        bidding_deadline=bidding_deadline,
        buyer_organization_id=current_user.organization_id,
    )


@router.get("/timing", response_model=TimingAdvice)
async def get_timing_advice(
    delivery_port: str | None = Query(None, max_length=10),
    delivery_date: datetime | None = Query(None),
    bidding_deadline: datetime | None = Query(None),
    vessel_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TimingAdvice:
    """Get timing recommendations for procurement action."""
    svc = TimingAdvisor(db)
    return await svc.get_timing_advice(
        delivery_port=delivery_port,
        delivery_date=delivery_date,
        bidding_deadline=bidding_deadline,
        vessel_id=vessel_id,
    )
