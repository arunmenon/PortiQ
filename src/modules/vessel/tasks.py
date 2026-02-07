"""Celery tasks for vessel tracking — polling, on-demand fetch, cleanup."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from celery_app import celery
from src.database.engine import async_session, sync_engine
from src.models.enums import AisProvider, PortCallStatus, VesselStatus
from src.models.port_call import PortCall
from src.models.vessel import Vessel
from src.models.vessel_position import VesselPosition
from src.modules.vessel.providers.factory import (
    close_all_providers,
    get_provider,
    get_provider_for_port,
)

logger = logging.getLogger(__name__)


async def _poll_positions_async() -> dict:
    """Async implementation: fetch positions for all active vessels."""
    from src.modules.vessel.tracking_service import TrackingService

    provider = get_provider(AisProvider.VESSEL_FINDER)
    stats = {"polled": 0, "updated": 0, "errors": 0}

    try:
        async with async_session() as session:
            result = await session.execute(
                select(Vessel).where(Vessel.status == VesselStatus.ACTIVE)
            )
            active_vessels = list(result.scalars().all())

            tracking = TrackingService(session)
            for vessel in active_vessels:
                stats["polled"] += 1
                try:
                    position_data = await provider.get_vessel_position(vessel.imo_number)
                    if position_data is None:
                        continue
                    await tracking.record_position(
                        vessel_id=vessel.id,
                        latitude=position_data["latitude"],
                        longitude=position_data["longitude"],
                        speed_knots=position_data.get("speed_knots"),
                        course=position_data.get("course"),
                        heading=position_data.get("heading"),
                        navigation_status=position_data.get("navigation_status"),
                        source=AisProvider.VESSEL_FINDER,
                        recorded_at=position_data.get("recorded_at"),
                    )
                    stats["updated"] += 1
                except Exception:
                    logger.exception("Error polling position for vessel %s", vessel.imo_number)
                    stats["errors"] += 1

            await session.commit()
    finally:
        await close_all_providers()

    return stats


async def _poll_eta_async() -> dict:
    """Async implementation: fetch ETA updates for vessels with approaching port calls."""
    from src.modules.vessel.tracking_service import TrackingService

    stats = {"polled": 0, "updated": 0, "errors": 0}

    try:
        async with async_session() as session:
            result = await session.execute(
                select(PortCall)
                .join(Vessel, PortCall.vessel_id == Vessel.id)
                .where(
                    PortCall.status == PortCallStatus.APPROACHING,
                    Vessel.status == VesselStatus.ACTIVE,
                )
            )
            approaching_calls = list(result.scalars().all())

            for port_call in approaching_calls:
                stats["polled"] += 1
                try:
                    vessel_result = await session.execute(
                        select(Vessel).where(Vessel.id == port_call.vessel_id)
                    )
                    vessel = vessel_result.scalar_one()
                    provider = get_provider_for_port(port_call.port_code)
                    eta_data = await provider.get_vessel_eta(vessel.imo_number)
                    if eta_data is None:
                        continue

                    tracking = TrackingService(session)
                    await tracking.record_port_call(
                        vessel_id=vessel.id,
                        port_code=port_call.port_code,
                        status=PortCallStatus.APPROACHING,
                        source=AisProvider.VESSEL_FINDER,
                        eta=eta_data.get("eta"),
                        distance_nm=eta_data.get("distance_nm"),
                        eta_confidence=eta_data.get("eta_confidence"),
                    )
                    stats["updated"] += 1
                except Exception:
                    logger.exception("Error polling ETA for port call %s", port_call.id)
                    stats["errors"] += 1

            await session.commit()
    finally:
        await close_all_providers()

    return stats


async def _poll_port_arrivals_async() -> dict:
    """Async implementation: poll arrivals for watched Indian ports and persist to DB."""
    from src.modules.vessel.constants import PCS1X_PORTS
    from src.modules.vessel.tracking_service import TrackingService

    stats = {"ports_checked": 0, "arrivals_found": 0, "persisted": 0, "errors": 0}

    try:
        async with async_session() as session:
            tracking = TrackingService(session)
            for port_code in PCS1X_PORTS:
                stats["ports_checked"] += 1
                try:
                    provider = get_provider_for_port(port_code)
                    arrivals = await provider.get_port_arrivals(port_code)
                    stats["arrivals_found"] += len(arrivals)

                    for arrival in arrivals:
                        imo = arrival.get("imo_number")
                        if not imo:
                            continue
                        # Match arrival to existing vessel
                        vessel_result = await session.execute(
                            select(Vessel).where(Vessel.imo_number == imo)
                        )
                        vessel = vessel_result.scalar_one_or_none()
                        if vessel is None:
                            continue
                        try:
                            await tracking.record_port_call(
                                vessel_id=vessel.id,
                                port_code=port_code,
                                status=PortCallStatus.APPROACHING,
                                source=AisProvider.PCS1X,
                                port_name=arrival.get("vessel_name"),
                                eta=arrival.get("eta"),
                                distance_nm=arrival.get("distance_nm"),
                                berth=arrival.get("berth"),
                            )
                            stats["persisted"] += 1
                        except Exception:
                            logger.exception(
                                "Error persisting arrival for vessel %s at port %s",
                                imo, port_code,
                            )

                    logger.info("Port %s: %d arrivals found", port_code, len(arrivals))
                except Exception:
                    logger.exception("Error polling arrivals for port %s", port_code)
                    stats["errors"] += 1

            await session.commit()
    finally:
        await close_all_providers()

    return stats


async def _fetch_single_position_async(vessel_id_str: str) -> dict | None:
    """Async implementation: fetch position for a single vessel on demand."""
    from src.modules.vessel.tracking_service import TrackingService

    vessel_uuid = uuid.UUID(vessel_id_str)

    try:
        async with async_session() as session:
            result = await session.execute(
                select(Vessel).where(Vessel.id == vessel_uuid)
            )
            vessel = result.scalar_one_or_none()
            if vessel is None:
                logger.warning("Vessel %s not found for on-demand fetch", vessel_id_str)
                return None

            provider = get_provider(AisProvider.VESSEL_FINDER)
            position_data = await provider.get_vessel_position(vessel.imo_number)
            if position_data is None:
                logger.info("No position data returned for vessel %s", vessel.imo_number)
                return None

            tracking = TrackingService(session)
            position = await tracking.record_position(
                vessel_id=vessel.id,
                latitude=position_data["latitude"],
                longitude=position_data["longitude"],
                speed_knots=position_data.get("speed_knots"),
                course=position_data.get("course"),
                heading=position_data.get("heading"),
                navigation_status=position_data.get("navigation_status"),
                source=AisProvider.VESSEL_FINDER,
                recorded_at=position_data.get("recorded_at"),
            )
            await session.commit()
            return {"position_id": str(position.id)}
    finally:
        await close_all_providers()


async def _backfill_history_async(vessel_id_str: str, days: int) -> dict:
    """Async implementation: pull historical track data for a vessel."""
    from src.modules.vessel.tracking_service import TrackingService

    vessel_uuid = uuid.UUID(vessel_id_str)
    hours = days * 24

    try:
        async with async_session() as session:
            result = await session.execute(
                select(Vessel).where(Vessel.id == vessel_uuid)
            )
            vessel = result.scalar_one_or_none()
            if vessel is None:
                logger.warning("Vessel %s not found for backfill", vessel_id_str)
                return {"error": "Vessel not found"}

            provider = get_provider(AisProvider.VESSEL_FINDER)
            track_data = await provider.get_vessel_track(vessel.imo_number, hours=hours)

            tracking = TrackingService(session)
            recorded_count = 0
            for point in track_data:
                try:
                    await tracking.record_position(
                        vessel_id=vessel.id,
                        latitude=point["latitude"],
                        longitude=point["longitude"],
                        speed_knots=point.get("speed_knots"),
                        course=point.get("course"),
                        heading=point.get("heading"),
                        source=AisProvider.VESSEL_FINDER,
                        recorded_at=point.get("recorded_at"),
                    )
                    recorded_count += 1
                except Exception:
                    logger.exception("Error recording backfill point for vessel %s", vessel.imo_number)

            await session.commit()
            return {"vessel_id": vessel_id_str, "points_recorded": recorded_count}
    finally:
        await close_all_providers()


# ---------------------------------------------------------------------------
# Celery task definitions
# ---------------------------------------------------------------------------


@celery.task(name="src.modules.vessel.tasks.poll_vessel_positions")
def poll_vessel_positions():
    """Poll VesselFinder for all ACTIVE vessels' positions."""
    stats = asyncio.run(_poll_positions_async())
    logger.info("poll_vessel_positions complete: %s", stats)
    return stats


@celery.task(name="src.modules.vessel.tasks.poll_vessel_eta")
def poll_vessel_eta():
    """Poll ETA updates for vessels with APPROACHING port calls."""
    stats = asyncio.run(_poll_eta_async())
    logger.info("poll_vessel_eta complete: %s", stats)
    return stats


@celery.task(name="src.modules.vessel.tasks.poll_port_arrivals")
def poll_port_arrivals():
    """Poll arrivals for watched ports."""
    stats = asyncio.run(_poll_port_arrivals_async())
    logger.info("poll_port_arrivals complete: %s", stats)
    return stats


@celery.task(name="src.modules.vessel.tasks.fetch_vessel_position", bind=True, max_retries=3)
def fetch_vessel_position(self, vessel_id: str):
    """Fetch position for a single vessel (on-demand)."""
    try:
        result = asyncio.run(_fetch_single_position_async(vessel_id))
        logger.info("fetch_vessel_position complete for %s: %s", vessel_id, result)
        return result
    except Exception as exc:
        logger.exception("fetch_vessel_position failed for %s", vessel_id)
        raise self.retry(exc=exc, countdown=30)


@celery.task(name="src.modules.vessel.tasks.backfill_vessel_history", bind=True, max_retries=3)
def backfill_vessel_history(self, vessel_id: str, days: int = 90):
    """Pull historical track data for a vessel."""
    try:
        result = asyncio.run(_backfill_history_async(vessel_id, days))
        logger.info("backfill_vessel_history complete for %s: %s", vessel_id, result)
        return result
    except Exception as exc:
        logger.exception("backfill_vessel_history failed for %s", vessel_id)
        raise self.retry(exc=exc, countdown=60)


@celery.task(name="src.modules.vessel.tasks.cleanup_vessel_data")
def cleanup_vessel_data():
    """Daily cleanup: prune old positions (>90d), old port calls (>2y)."""
    now = datetime.now(UTC)
    position_cutoff = now - timedelta(days=90)
    port_call_cutoff = now - timedelta(days=730)

    with Session(sync_engine) as session:
        # Delete old vessel positions
        position_result = session.execute(
            delete(VesselPosition).where(VesselPosition.recorded_at < position_cutoff)
        )
        positions_deleted = position_result.rowcount

        # Delete old completed port calls
        port_call_result = session.execute(
            delete(PortCall).where(
                PortCall.atd.isnot(None),
                PortCall.atd < port_call_cutoff,
            )
        )
        port_calls_deleted = port_call_result.rowcount

        session.commit()

    logger.info(
        "cleanup_vessel_data: deleted %d positions, %d port calls",
        positions_deleted,
        port_calls_deleted,
    )
    return {
        "positions_deleted": positions_deleted,
        "port_calls_deleted": port_calls_deleted,
    }
