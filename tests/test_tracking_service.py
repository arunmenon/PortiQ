"""Tests for TrackingService — position recording, port calls, validation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions import ValidationException
from src.models.enums import AisProvider, NavigationStatus, PortCallStatus
from src.models.port_call import PortCall
from src.models.vessel_position import VesselPosition
from src.modules.vessel.tracking_service import TrackingService


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def tracking_service(mock_session):
    with patch("src.modules.vessel.tracking_service.OutboxService") as mock_outbox_cls:
        mock_outbox_instance = AsyncMock()
        mock_outbox_cls.return_value = mock_outbox_instance
        service = TrackingService(mock_session)
        service.outbox = mock_outbox_instance
        return service


class TestValidatePosition:
    def test_valid_position(self, tracking_service):
        assert tracking_service.validate_position(18.9220, 72.8347) is True

    def test_valid_position_with_speed_and_confidence(self, tracking_service):
        assert tracking_service.validate_position(18.9220, 72.8347, speed=12.5, confidence=0.9) is True

    def test_invalid_latitude_too_high(self, tracking_service):
        assert tracking_service.validate_position(91.0, 72.8347) is False

    def test_invalid_latitude_too_low(self, tracking_service):
        assert tracking_service.validate_position(-91.0, 72.8347) is False

    def test_invalid_longitude_too_high(self, tracking_service):
        assert tracking_service.validate_position(18.9220, 181.0) is False

    def test_invalid_longitude_too_low(self, tracking_service):
        assert tracking_service.validate_position(18.9220, -181.0) is False

    def test_excessive_speed_rejected(self, tracking_service):
        assert tracking_service.validate_position(18.9220, 72.8347, speed=55.0) is False

    def test_low_confidence_rejected(self, tracking_service):
        assert tracking_service.validate_position(18.9220, 72.8347, confidence=0.5) is False

    def test_boundary_speed_accepted(self, tracking_service):
        assert tracking_service.validate_position(18.9220, 72.8347, speed=50.0) is True

    def test_boundary_confidence_accepted(self, tracking_service):
        assert tracking_service.validate_position(18.9220, 72.8347, confidence=0.7) is True


class TestRecordPosition:
    @pytest.mark.asyncio
    async def test_record_position_valid(self, tracking_service, mock_session):
        vessel_id = uuid.uuid4()
        recorded_at = datetime.now(timezone.utc)

        position = await tracking_service.record_position(
            vessel_id=vessel_id,
            latitude=18.9220,
            longitude=72.8347,
            speed_knots=12.5,
            course=180.0,
            heading=175.0,
            navigation_status=NavigationStatus.UNDER_WAY,
            source=AisProvider.VESSEL_FINDER,
            recorded_at=recorded_at,
            signal_confidence=0.95,
        )

        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited()
        tracking_service.outbox.publish_event.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_record_position_invalid_raises(self, tracking_service):
        vessel_id = uuid.uuid4()

        with pytest.raises(ValidationException, match="Invalid position data"):
            await tracking_service.record_position(
                vessel_id=vessel_id,
                latitude=100.0,  # invalid
                longitude=72.8347,
            )


class TestGetLatestPosition:
    @pytest.mark.asyncio
    async def test_get_latest_position(self, tracking_service, mock_session):
        vessel_id = uuid.uuid4()
        expected_position = VesselPosition(
            id=uuid.uuid4(),
            vessel_id=vessel_id,
            latitude=Decimal("18.9220000"),
            longitude=Decimal("72.8347000"),
            recorded_at=datetime.now(timezone.utc),
        )

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = expected_position
        mock_session.execute.return_value = mock_result

        position = await tracking_service.get_latest_position(vessel_id)

        assert position is not None
        assert position.vessel_id == vessel_id


class TestRecordPortCall:
    @pytest.mark.asyncio
    async def test_record_new_port_call(self, tracking_service, mock_session):
        vessel_id = uuid.uuid4()

        # Mock: no existing active port call
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        port_call = await tracking_service.record_port_call(
            vessel_id=vessel_id,
            port_code="INBOM",
            status=PortCallStatus.APPROACHING,
            source=AisProvider.PCS1X,
            port_name="Mumbai",
            eta=datetime.now(timezone.utc),
        )

        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited()
        tracking_service.outbox.publish_event.assert_awaited()


class TestGetActivePortCalls:
    @pytest.mark.asyncio
    async def test_get_active_port_calls(self, tracking_service, mock_session):
        vessel_id = uuid.uuid4()
        expected_port_call = PortCall(
            id=uuid.uuid4(),
            vessel_id=vessel_id,
            port_code="INBOM",
            status=PortCallStatus.BERTHED,
        )

        mock_result = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [expected_port_call]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        port_calls = await tracking_service.get_active_port_calls(vessel_id)

        assert len(port_calls) == 1
        assert port_calls[0].port_code == "INBOM"
