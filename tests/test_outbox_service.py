"""Unit tests for OutboxService — event outbox lifecycle management."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database.base import Base
from src.models.enums import EventStatus
from src.models.event_outbox import EventOutbox
from src.models.processed_event import ProcessedEvent
from src.modules.events.outbox_service import OutboxService


# Use SQLite for lightweight in-process testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"


@pytest_asyncio.fixture
async def async_test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def async_test_session(async_test_engine):
    session_factory = async_sessionmaker(
        async_test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


class TestOutboxServicePublish:
    """Tests for OutboxService.publish_event."""

    @pytest.mark.asyncio
    async def test_publish_event_creates_pending_event(self, async_test_session):
        service = OutboxService(async_test_session)

        event = await service.publish_event(
            event_type="vessel.approaching",
            aggregate_type="vessel",
            aggregate_id=str(uuid.uuid4()),
            payload={"port_code": "INMUN", "eta": "2026-02-10T08:00:00Z"},
        )

        assert event.id is not None
        assert event.event_type == "vessel.approaching"
        assert event.aggregate_type == "vessel"
        assert event.status == EventStatus.PENDING
        assert event.retry_count == 0
        assert event.schema_version == 1
        assert event.payload["port_code"] == "INMUN"

    @pytest.mark.asyncio
    async def test_publish_event_with_custom_schema_version(self, async_test_session):
        service = OutboxService(async_test_session)

        event = await service.publish_event(
            event_type="vessel.departed",
            aggregate_type="vessel",
            aggregate_id=str(uuid.uuid4()),
            payload={"port_code": "SGSIN"},
            schema_version=2,
        )

        assert event.schema_version == 2


class TestOutboxServiceGetPending:
    """Tests for OutboxService.get_pending_events."""

    @pytest.mark.asyncio
    async def test_get_pending_events_returns_only_pending(self, async_test_session):
        service = OutboxService(async_test_session)
        vessel_id = str(uuid.uuid4())

        # Create a pending event
        await service.publish_event(
            event_type="vessel.approaching",
            aggregate_type="vessel",
            aggregate_id=vessel_id,
            payload={},
        )
        # Create another and mark it completed
        completed_event = await service.publish_event(
            event_type="vessel.departed",
            aggregate_type="vessel",
            aggregate_id=vessel_id,
            payload={},
        )
        await service.mark_completed(completed_event.id)

        pending = await service.get_pending_events(batch_size=10)
        assert len(pending) == 1
        assert pending[0].event_type == "vessel.approaching"

    @pytest.mark.asyncio
    async def test_get_pending_events_respects_batch_size(self, async_test_session):
        service = OutboxService(async_test_session)

        for i in range(5):
            await service.publish_event(
                event_type=f"test.event.{i}",
                aggregate_type="test",
                aggregate_id=str(uuid.uuid4()),
                payload={},
            )

        pending = await service.get_pending_events(batch_size=3)
        assert len(pending) == 3


class TestOutboxServiceMarkCompleted:
    """Tests for OutboxService.mark_completed."""

    @pytest.mark.asyncio
    async def test_mark_completed_sets_status_and_timestamp(self, async_test_session):
        service = OutboxService(async_test_session)

        event = await service.publish_event(
            event_type="vessel.approaching",
            aggregate_type="vessel",
            aggregate_id=str(uuid.uuid4()),
            payload={},
        )

        await service.mark_completed(event.id)

        # Refresh the event from DB
        await async_test_session.refresh(event)
        assert event.status == EventStatus.COMPLETED
        assert event.processed_at is not None


class TestOutboxServiceMarkFailed:
    """Tests for OutboxService.mark_failed."""

    @pytest.mark.asyncio
    async def test_mark_failed_increments_retry_and_stays_pending(self, async_test_session):
        service = OutboxService(async_test_session)

        event = await service.publish_event(
            event_type="vessel.approaching",
            aggregate_type="vessel",
            aggregate_id=str(uuid.uuid4()),
            payload={},
        )

        await service.mark_failed(event.id, "Connection timeout")

        await async_test_session.refresh(event)
        assert event.retry_count == 1
        assert event.last_error == "Connection timeout"
        # max_retries default is 3, so after 1 failure it should go back to PENDING
        assert event.status == EventStatus.PENDING

    @pytest.mark.asyncio
    async def test_mark_failed_sets_failed_when_max_retries_reached(self, async_test_session):
        service = OutboxService(async_test_session)

        event = await service.publish_event(
            event_type="vessel.approaching",
            aggregate_type="vessel",
            aggregate_id=str(uuid.uuid4()),
            payload={},
        )

        # Fail 3 times (default max_retries=3)
        for i in range(3):
            await service.mark_failed(event.id, f"Failure #{i + 1}")
            await async_test_session.refresh(event)

        assert event.retry_count == 3
        assert event.status == EventStatus.FAILED
        assert event.last_error == "Failure #3"

    @pytest.mark.asyncio
    async def test_mark_failed_transitions_from_pending_to_failed_at_boundary(
        self, async_test_session
    ):
        service = OutboxService(async_test_session)

        event = await service.publish_event(
            event_type="vessel.approaching",
            aggregate_type="vessel",
            aggregate_id=str(uuid.uuid4()),
            payload={},
        )

        # After 2 failures, should still be PENDING
        await service.mark_failed(event.id, "Error 1")
        await async_test_session.refresh(event)
        assert event.status == EventStatus.PENDING

        await service.mark_failed(event.id, "Error 2")
        await async_test_session.refresh(event)
        assert event.status == EventStatus.PENDING

        # Third failure should push it to FAILED
        await service.mark_failed(event.id, "Error 3")
        await async_test_session.refresh(event)
        assert event.status == EventStatus.FAILED


class TestOutboxServiceMarkProcessing:
    """Tests for OutboxService.mark_processing."""

    @pytest.mark.asyncio
    async def test_mark_processing_sets_status(self, async_test_session):
        service = OutboxService(async_test_session)

        event = await service.publish_event(
            event_type="vessel.berthed",
            aggregate_type="vessel",
            aggregate_id=str(uuid.uuid4()),
            payload={},
        )

        await service.mark_processing(event.id)

        await async_test_session.refresh(event)
        assert event.status == EventStatus.PROCESSING
