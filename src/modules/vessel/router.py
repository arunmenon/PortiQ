"""Vessel tracking API router — 15 endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.exceptions import ForbiddenException
from src.models.enums import AisProvider, PortCallStatus, VesselStatus, VesselType
from src.modules.tenancy.auth import AuthenticatedUser, get_current_user
from src.modules.vessel.schemas import (
    BulkImportRequest,
    BulkImportResponse,
    ManualPortCallCreate,
    PortCallListResponse,
    PortCallResponse,
    PortCallUpdate,
    PositionResponse,
    ProviderHealthResponse,
    TaskEnqueuedResponse,
    VesselCreate,
    VesselListResponse,
    VesselResponse,
    VesselUpdate,
)
from src.modules.vessel.tracking_service import TrackingService
from src.modules.vessel.vessel_service import VesselService

router = APIRouter(prefix="/vessels", tags=["vessels"])


# ---------------------------------------------------------------------------
# Static routes (BEFORE /{vessel_id} to avoid path conflicts)
# ---------------------------------------------------------------------------


@router.get("/by-imo/{imo_number}", response_model=VesselResponse)
async def get_vessel_by_imo(
    imo_number: str,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = VesselService(session)
    vessel = await service.get_vessel_by_imo(imo_number)
    return vessel


@router.get("/port/{port_code}/arrivals", response_model=list[PortCallResponse])
async def get_port_arrivals(
    port_code: str,
    limit: int = Query(50, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    tracking = TrackingService(session)
    arrivals = await tracking.get_port_arrivals(port_code, limit=limit)
    return arrivals


@router.post("/bulk-import", response_model=BulkImportResponse)
async def bulk_import_vessels(
    body: BulkImportRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if not user.is_platform_admin:
        raise ForbiddenException("Bulk import requires platform admin privileges")
    service = VesselService(session)
    result = await service.bulk_import_vessels(body.vessels)
    return BulkImportResponse(**result)


@router.get("/providers/health", response_model=list[ProviderHealthResponse])
async def check_provider_health(
    user: AuthenticatedUser = Depends(get_current_user),
):
    from src.modules.vessel.providers.factory import get_provider

    results = []
    for provider_enum in [AisProvider.VESSEL_FINDER, AisProvider.PCS1X]:
        try:
            provider = get_provider(provider_enum)
            healthy = await provider.health_check()
            results.append(ProviderHealthResponse(
                provider=provider_enum.value,
                healthy=healthy,
                message="OK" if healthy else "Health check failed",
            ))
        except Exception as exc:
            results.append(ProviderHealthResponse(
                provider=provider_enum.value,
                healthy=False,
                message=str(exc),
            ))
    return results


# ---------------------------------------------------------------------------
# Port Call CRUD (manual creation)
# ---------------------------------------------------------------------------


@router.post("/port-calls", response_model=PortCallResponse, status_code=201)
async def create_port_call(
    body: ManualPortCallCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    tracking = TrackingService(session)
    port_call = await tracking.create_manual_port_call(body)
    return port_call


@router.get("/port-calls", response_model=PortCallListResponse)
async def list_port_calls(
    vessel_id: uuid.UUID | None = Query(None),
    port_code: str | None = Query(None),
    status: PortCallStatus | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    tracking = TrackingService(session)
    items, total = await tracking.list_port_calls(
        vessel_id=vessel_id,
        port_code=port_code,
        status=status,
        limit=limit,
        offset=offset,
    )
    return PortCallListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/port-calls/{port_call_id}", response_model=PortCallResponse)
async def get_port_call(
    port_call_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    tracking = TrackingService(session)
    port_call = await tracking.get_port_call(port_call_id)
    return port_call


@router.put("/port-calls/{port_call_id}", response_model=PortCallResponse)
async def update_port_call(
    port_call_id: uuid.UUID,
    body: PortCallUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    tracking = TrackingService(session)
    port_call = await tracking.update_port_call(port_call_id, body)
    return port_call


# ---------------------------------------------------------------------------
# CRUD routes
# ---------------------------------------------------------------------------


@router.post("/", response_model=VesselResponse, status_code=201)
async def create_vessel(
    body: VesselCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = VesselService(session)
    vessel = await service.create_vessel(body)
    return vessel


@router.get("/", response_model=VesselListResponse)
async def list_vessels(
    vessel_type: VesselType | None = Query(None),
    status: VesselStatus | None = Query(None),
    owner_organization_id: uuid.UUID | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = VesselService(session)
    vessels, total = await service.list_vessels(
        vessel_type=vessel_type,
        status=status,
        owner_organization_id=owner_organization_id,
        search=search,
        limit=limit,
        offset=offset,
    )
    return VesselListResponse(items=vessels, total=total, limit=limit, offset=offset)


@router.get("/{vessel_id}", response_model=VesselResponse)
async def get_vessel(
    vessel_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = VesselService(session)
    vessel = await service.get_vessel(vessel_id)
    return vessel


@router.patch("/{vessel_id}", response_model=VesselResponse)
async def update_vessel(
    vessel_id: uuid.UUID,
    body: VesselUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = VesselService(session)
    vessel = await service.update_vessel(vessel_id, body)
    return vessel


@router.delete("/{vessel_id}", response_model=VesselResponse)
async def decommission_vessel(
    vessel_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = VesselService(session)
    vessel = await service.decommission_vessel(vessel_id)
    return vessel


# ---------------------------------------------------------------------------
# Position endpoints
# ---------------------------------------------------------------------------


@router.get("/{vessel_id}/positions", response_model=list[PositionResponse])
async def get_position_history(
    vessel_id: uuid.UUID,
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    tracking = TrackingService(session)
    positions = await tracking.get_position_history(
        vessel_id, since=since, until=until, limit=limit,
    )
    return positions


@router.get("/{vessel_id}/positions/latest", response_model=PositionResponse | None)
async def get_latest_position(
    vessel_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    tracking = TrackingService(session)
    position = await tracking.get_latest_position(vessel_id)
    return position


# ---------------------------------------------------------------------------
# Port call endpoints
# ---------------------------------------------------------------------------


@router.get("/{vessel_id}/port-calls", response_model=list[PortCallResponse])
async def get_port_call_history(
    vessel_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    tracking = TrackingService(session)
    port_calls = await tracking.get_port_call_history(vessel_id, limit=limit)
    return port_calls


@router.get("/{vessel_id}/port-calls/active", response_model=list[PortCallResponse])
async def get_active_port_calls(
    vessel_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    tracking = TrackingService(session)
    port_calls = await tracking.get_active_port_calls(vessel_id)
    return port_calls


# ---------------------------------------------------------------------------
# On-demand tracking actions
# ---------------------------------------------------------------------------


@router.post("/{vessel_id}/track", response_model=TaskEnqueuedResponse, status_code=202)
async def trigger_position_fetch(
    vessel_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
):
    from src.modules.vessel.tasks import fetch_vessel_position

    fetch_vessel_position.delay(str(vessel_id))
    return TaskEnqueuedResponse(message="Position fetch enqueued", vessel_id=str(vessel_id))


@router.post("/{vessel_id}/backfill", response_model=TaskEnqueuedResponse, status_code=202)
async def trigger_backfill(
    vessel_id: uuid.UUID,
    days: int = Query(90, ge=1, le=365),
    user: AuthenticatedUser = Depends(get_current_user),
):
    from src.modules.vessel.tasks import backfill_vessel_history

    backfill_vessel_history.delay(str(vessel_id), days=days)
    return TaskEnqueuedResponse(
        message="Backfill enqueued", vessel_id=str(vessel_id), days=days,
    )
