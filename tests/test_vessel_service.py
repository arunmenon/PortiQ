"""Tests for VesselService — CRUD operations."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions import ConflictException, NotFoundException
from src.models.enums import VesselStatus, VesselType
from src.models.vessel import Vessel
from src.modules.vessel.schemas import VesselCreate, VesselUpdate
from src.modules.vessel.vessel_service import VesselService


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def vessel_service(mock_session):
    return VesselService(mock_session)


@pytest.fixture
def sample_vessel_create():
    return VesselCreate(
        imo_number="1234567",
        name="MV Test Vessel",
        vessel_type=VesselType.CONTAINER,
        mmsi="123456789",
        flag_state="IND",
        gross_tonnage=Decimal("50000.00"),
        deadweight_tonnage=Decimal("65000.00"),
    )


@pytest.fixture
def sample_vessel():
    vessel = Vessel(
        id=uuid.uuid4(),
        imo_number="1234567",
        name="MV Test Vessel",
        vessel_type=VesselType.CONTAINER,
        status=VesselStatus.ACTIVE,
        mmsi="123456789",
        flag_state="IND",
        gross_tonnage=Decimal("50000.00"),
        deadweight_tonnage=Decimal("65000.00"),
        metadata_extra={},
    )
    return vessel


class TestCreateVessel:
    @pytest.mark.asyncio
    async def test_create_vessel_success(self, vessel_service, mock_session, sample_vessel_create):
        # Mock: no existing vessel with same IMO
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        vessel = await vessel_service.create_vessel(sample_vessel_create)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_vessel_duplicate_imo_raises_conflict(
        self, vessel_service, mock_session, sample_vessel_create, sample_vessel,
    ):
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_vessel
        mock_session.execute.return_value = mock_result

        with pytest.raises(ConflictException, match="already exists"):
            await vessel_service.create_vessel(sample_vessel_create)


class TestGetVessel:
    @pytest.mark.asyncio
    async def test_get_vessel_success(self, vessel_service, mock_session, sample_vessel):
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_vessel
        mock_session.execute.return_value = mock_result

        vessel = await vessel_service.get_vessel(sample_vessel.id)

        assert vessel.imo_number == "1234567"
        assert vessel.name == "MV Test Vessel"

    @pytest.mark.asyncio
    async def test_get_vessel_not_found_raises(self, vessel_service, mock_session):
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(NotFoundException, match="not found"):
            await vessel_service.get_vessel(uuid.uuid4())


class TestListVessels:
    @pytest.mark.asyncio
    async def test_list_vessels_with_filters(self, vessel_service, mock_session, sample_vessel):
        # Mock count query
        count_result = AsyncMock()
        count_result.scalar_one.return_value = 1

        # Mock vessel query
        vessel_result = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_vessel]
        vessel_result.scalars.return_value = mock_scalars

        mock_session.execute.side_effect = [count_result, vessel_result]

        vessels, total = await vessel_service.list_vessels(
            vessel_type=VesselType.CONTAINER,
            status=VesselStatus.ACTIVE,
        )

        assert total == 1
        assert len(vessels) == 1
        assert vessels[0].imo_number == "1234567"


class TestDecommissionVessel:
    @pytest.mark.asyncio
    async def test_decommission_vessel(self, vessel_service, mock_session, sample_vessel):
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_vessel
        mock_session.execute.return_value = mock_result

        vessel = await vessel_service.decommission_vessel(sample_vessel.id)

        assert vessel.status == VesselStatus.DECOMMISSIONED
        mock_session.flush.assert_awaited()
