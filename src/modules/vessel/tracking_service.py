"""TrackingService — position recording, port call management, event publishing."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from typing import TYPE_CHECKING

from src.exceptions import NotFoundException, ValidationException
from src.models.enums import AisProvider, NavigationStatus, PortCallStatus
from src.models.port_call import PortCall
from src.models.vessel_position import VesselPosition
from src.modules.events.outbox_service import OutboxService
from src.modules.vessel.constants import (
    MAX_SPEED_KNOTS,
    MIN_SIGNAL_CONFIDENCE,
    VESSEL_EVENT_TYPES,
)

if TYPE_CHECKING:
    from src.modules.vessel.schemas import ManualPortCallCreate, PortCallUpdate


class TrackingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.outbox = OutboxService(session)

    # ------------------------------------------------------------------
    # Position tracking
    # ------------------------------------------------------------------

    async def record_position(
        self,
        vessel_id: uuid.UUID,
        latitude: float,
        longitude: float,
        speed_knots: float | None = None,
        course: float | None = None,
        heading: float | None = None,
        navigation_status: NavigationStatus | None = None,
        source: AisProvider | None = None,
        recorded_at: datetime | None = None,
        signal_confidence: float | None = None,
        raw_data: dict | None = None,
    ) -> VesselPosition:
        if not self.validate_position(latitude, longitude, speed_knots, signal_confidence):
            raise ValidationException(
                "Invalid position data: coordinates out of range, excessive speed, or low confidence"
            )

        position = VesselPosition(
            vessel_id=vessel_id,
            latitude=Decimal(str(latitude)),
            longitude=Decimal(str(longitude)),
            speed_knots=Decimal(str(speed_knots)) if speed_knots is not None else None,
            course=Decimal(str(course)) if course is not None else None,
            heading=Decimal(str(heading)) if heading is not None else None,
            navigation_status=navigation_status,
            source=source,
            signal_confidence=Decimal(str(signal_confidence)) if signal_confidence is not None else None,
            recorded_at=recorded_at or datetime.now(UTC),
            raw_data=raw_data,
        )
        self.session.add(position)
        await self.session.flush()

        await self.outbox.publish_event(
            event_type=VESSEL_EVENT_TYPES["position_updated"],
            aggregate_type="vessel",
            aggregate_id=str(vessel_id),
            payload={
                "vessel_id": str(vessel_id),
                "latitude": latitude,
                "longitude": longitude,
                "speed_knots": speed_knots,
                "recorded_at": position.recorded_at.isoformat(),
            },
        )

        return position

    async def get_latest_position(self, vessel_id: uuid.UUID) -> VesselPosition | None:
        result = await self.session.execute(
            select(VesselPosition)
            .where(VesselPosition.vessel_id == vessel_id)
            .order_by(VesselPosition.recorded_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_position_history(
        self,
        vessel_id: uuid.UUID,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[VesselPosition]:
        query = (
            select(VesselPosition)
            .where(VesselPosition.vessel_id == vessel_id)
        )
        if since is not None:
            query = query.where(VesselPosition.recorded_at >= since)
        if until is not None:
            query = query.where(VesselPosition.recorded_at <= until)
        query = query.order_by(VesselPosition.recorded_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Port calls
    # ------------------------------------------------------------------

    async def record_port_call(
        self,
        vessel_id: uuid.UUID,
        port_code: str,
        status: PortCallStatus,
        source: AisProvider | None = None,
        port_name: str | None = None,
        eta: datetime | None = None,
        ata: datetime | None = None,
        atd: datetime | None = None,
        berth: str | None = None,
        pilot_time: datetime | None = None,
        distance_nm: float | None = None,
        eta_confidence: float | None = None,
        raw_data: dict | None = None,
    ) -> PortCall:
        # Check for existing active port call at the same port
        existing_result = await self.session.execute(
            select(PortCall).where(
                PortCall.vessel_id == vessel_id,
                PortCall.port_code == port_code,
                PortCall.status.notin_([PortCallStatus.DEPARTED, PortCallStatus.CANCELLED]),
            )
        )
        existing_port_call = existing_result.scalar_one_or_none()

        if existing_port_call is not None:
            # Update existing active port call
            existing_port_call.status = status
            if eta is not None:
                existing_port_call.eta = eta
            if ata is not None:
                existing_port_call.ata = ata
            if atd is not None:
                existing_port_call.atd = atd
            if berth is not None:
                existing_port_call.berth = berth
            if pilot_time is not None:
                existing_port_call.pilot_time = pilot_time
            if distance_nm is not None:
                existing_port_call.distance_nm = Decimal(str(distance_nm))
            if eta_confidence is not None:
                existing_port_call.eta_confidence = Decimal(str(eta_confidence))
            if source is not None:
                existing_port_call.source = source
            if raw_data is not None:
                existing_port_call.raw_data = raw_data
            await self.session.flush()
            port_call = existing_port_call
        else:
            port_call = PortCall(
                vessel_id=vessel_id,
                port_code=port_code,
                port_name=port_name,
                status=status,
                eta=eta,
                ata=ata,
                atd=atd,
                berth=berth,
                pilot_time=pilot_time,
                distance_nm=Decimal(str(distance_nm)) if distance_nm is not None else None,
                eta_confidence=Decimal(str(eta_confidence)) if eta_confidence is not None else None,
                source=source,
                raw_data=raw_data,
            )
            self.session.add(port_call)
            await self.session.flush()

        # Publish appropriate event based on status
        event_type_map = {
            PortCallStatus.APPROACHING: VESSEL_EVENT_TYPES["approaching"],
            PortCallStatus.ARRIVED: VESSEL_EVENT_TYPES["arrived"],
            PortCallStatus.BERTHED: VESSEL_EVENT_TYPES["arrived"],
            PortCallStatus.DEPARTED: VESSEL_EVENT_TYPES["departed"],
        }
        event_type = event_type_map.get(status)
        if event_type:
            await self.outbox.publish_event(
                event_type=event_type,
                aggregate_type="vessel",
                aggregate_id=str(vessel_id),
                payload={
                    "vessel_id": str(vessel_id),
                    "port_code": port_code,
                    "status": status.value,
                    "port_call_id": str(port_call.id),
                },
            )

        return port_call

    # ------------------------------------------------------------------
    # Manual port call CRUD
    # ------------------------------------------------------------------

    async def create_manual_port_call(
        self,
        data: ManualPortCallCreate,
    ) -> PortCall:
        port_call = PortCall(
            vessel_id=data.vessel_id,
            port_code=data.port_code,
            port_name=data.port_name,
            eta=data.eta,
            berth=data.berth,
            status=PortCallStatus.APPROACHING,
            source=AisProvider.MANUAL,
            raw_data={},
        )
        self.session.add(port_call)
        await self.session.flush()
        return port_call

    async def update_port_call(
        self,
        port_call_id: uuid.UUID,
        data: PortCallUpdate,
    ) -> PortCall:
        result = await self.session.execute(
            select(PortCall).where(PortCall.id == port_call_id)
        )
        port_call = result.scalar_one_or_none()
        if port_call is None:
            raise NotFoundException(f"Port call {port_call_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        model_fields = {c.key for c in PortCall.__table__.columns}
        for field, value in update_data.items():
            if field in model_fields:
                setattr(port_call, field, value)

        await self.session.flush()
        return port_call

    async def list_port_calls(
        self,
        vessel_id: uuid.UUID | None = None,
        port_code: str | None = None,
        status: PortCallStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PortCall], int]:
        query = select(PortCall)
        count_query = select(func.count()).select_from(PortCall)

        if vessel_id is not None:
            query = query.where(PortCall.vessel_id == vessel_id)
            count_query = count_query.where(PortCall.vessel_id == vessel_id)
        if port_code is not None:
            query = query.where(PortCall.port_code == port_code)
            count_query = count_query.where(PortCall.port_code == port_code)
        if status is not None:
            query = query.where(PortCall.status == status)
            count_query = count_query.where(PortCall.status == status)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(PortCall.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_port_call(self, port_call_id: uuid.UUID) -> PortCall:
        result = await self.session.execute(
            select(PortCall).where(PortCall.id == port_call_id)
        )
        port_call = result.scalar_one_or_none()
        if port_call is None:
            raise NotFoundException(f"Port call {port_call_id} not found")
        return port_call

    async def get_active_port_calls(self, vessel_id: uuid.UUID) -> list[PortCall]:
        result = await self.session.execute(
            select(PortCall).where(
                PortCall.vessel_id == vessel_id,
                PortCall.status.notin_([PortCallStatus.DEPARTED, PortCallStatus.CANCELLED]),
            )
        )
        return list(result.scalars().all())

    async def get_port_call_history(
        self,
        vessel_id: uuid.UUID,
        limit: int = 50,
    ) -> list[PortCall]:
        result = await self.session.execute(
            select(PortCall)
            .where(PortCall.vessel_id == vessel_id)
            .order_by(PortCall.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_port_arrivals(
        self,
        port_code: str,
        limit: int = 50,
    ) -> list[PortCall]:
        result = await self.session.execute(
            select(PortCall).where(
                PortCall.port_code == port_code,
                PortCall.status.in_([
                    PortCallStatus.APPROACHING,
                    PortCallStatus.ARRIVED,
                    PortCallStatus.BERTHED,
                ]),
            ).order_by(PortCall.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_position(
        self,
        latitude: float,
        longitude: float,
        speed: float | None = None,
        confidence: float | None = None,
    ) -> bool:
        if not (-90 <= latitude <= 90):
            return False
        if not (-180 <= longitude <= 180):
            return False
        if speed is not None and speed > MAX_SPEED_KNOTS:
            return False
        if confidence is not None and confidence < MIN_SIGNAL_CONFIDENCE:
            return False
        return True

