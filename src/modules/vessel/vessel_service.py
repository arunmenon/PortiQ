"""VesselService — CRUD operations for vessel registry."""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import ConflictException, NotFoundException
from src.models.enums import VesselStatus, VesselType
from src.models.vessel import Vessel
from src.modules.vessel.schemas import VesselCreate, VesselUpdate

logger = __import__("logging").getLogger(__name__)


class VesselService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_vessel(self, data: VesselCreate) -> Vessel:
        existing = await self.session.execute(
            select(Vessel).where(Vessel.imo_number == data.imo_number)
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictException(f"Vessel with IMO {data.imo_number} already exists")

        vessel = Vessel(**data.model_dump())
        self.session.add(vessel)
        await self.session.flush()
        return vessel

    async def get_vessel(self, vessel_id: uuid.UUID) -> Vessel:
        result = await self.session.execute(
            select(Vessel).where(Vessel.id == vessel_id)
        )
        vessel = result.scalar_one_or_none()
        if vessel is None:
            raise NotFoundException(f"Vessel {vessel_id} not found")
        return vessel

    async def get_vessel_by_imo(self, imo_number: str) -> Vessel:
        result = await self.session.execute(
            select(Vessel).where(Vessel.imo_number == imo_number)
        )
        vessel = result.scalar_one_or_none()
        if vessel is None:
            raise NotFoundException(f"Vessel with IMO {imo_number} not found")
        return vessel

    async def get_vessel_by_mmsi(self, mmsi: str) -> Vessel | None:
        result = await self.session.execute(
            select(Vessel).where(Vessel.mmsi == mmsi)
        )
        return result.scalar_one_or_none()

    async def update_vessel(self, vessel_id: uuid.UUID, data: VesselUpdate) -> Vessel:
        vessel = await self.get_vessel(vessel_id)
        update_fields = data.model_dump(exclude_unset=True)
        for field_name, field_value in update_fields.items():
            setattr(vessel, field_name, field_value)
        await self.session.flush()
        return vessel

    async def list_vessels(
        self,
        vessel_type: VesselType | None = None,
        status: VesselStatus | None = None,
        owner_organization_id: uuid.UUID | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Vessel], int]:
        query = select(Vessel)
        count_query = select(func.count()).select_from(Vessel)

        if vessel_type is not None:
            query = query.where(Vessel.vessel_type == vessel_type)
            count_query = count_query.where(Vessel.vessel_type == vessel_type)
        if status is not None:
            query = query.where(Vessel.status == status)
            count_query = count_query.where(Vessel.status == status)
        if owner_organization_id is not None:
            query = query.where(Vessel.owner_organization_id == owner_organization_id)
            count_query = count_query.where(Vessel.owner_organization_id == owner_organization_id)
        if search:
            search_pattern = f"%{search}%"
            search_filter = or_(
                Vessel.name.ilike(search_pattern),
                Vessel.imo_number.ilike(search_pattern),
                Vessel.mmsi.ilike(search_pattern),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(Vessel.name).offset(offset).limit(limit)
        result = await self.session.execute(query)
        vessels = list(result.scalars().all())

        return vessels, total

    async def decommission_vessel(self, vessel_id: uuid.UUID) -> Vessel:
        vessel = await self.get_vessel(vessel_id)
        vessel.status = VesselStatus.DECOMMISSIONED
        await self.session.flush()
        return vessel

    async def bulk_import_vessels(self, vessels: list[VesselCreate]) -> dict:
        created_count = 0
        skipped_count = 0
        errors: list[str] = []

        for vessel_data in vessels:
            try:
                await self.create_vessel(vessel_data)
                created_count += 1
            except ConflictException:
                skipped_count += 1
            except Exception as exc:
                logger.warning(
                    "Error importing vessel %s: %s", vessel_data.imo_number, exc,
                )
                errors.append(f"Error creating vessel {vessel_data.imo_number}: {exc}")

        return {
            "created": created_count,
            "skipped": skipped_count,
            "errors": errors,
        }
