"""OutboxService — async service for publishing and managing outbox events."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.enums import EventStatus
from src.models.event_outbox import EventOutbox


class OutboxService:
    """Manages the event outbox lifecycle (publish, fetch, mark)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def publish_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict,
        schema_version: int = 1,
    ) -> EventOutbox:
        """Create a new event in the outbox with PENDING status."""
        event = EventOutbox(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            status=EventStatus.PENDING,
            schema_version=schema_version,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def get_pending_events(self, batch_size: int = 50) -> list[EventOutbox]:
        """Get pending events ordered by created_at, limited to batch_size."""
        statement = (
            select(EventOutbox)
            .where(EventOutbox.status == EventStatus.PENDING)
            .order_by(EventOutbox.created_at.asc())
            .limit(batch_size)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def mark_processing(self, event_id: uuid.UUID) -> None:
        """Set event status to PROCESSING."""
        statement = (
            update(EventOutbox)
            .where(EventOutbox.id == event_id)
            .values(status=EventStatus.PROCESSING)
        )
        await self.session.execute(statement)
        await self.session.flush()

    async def mark_completed(self, event_id: uuid.UUID) -> None:
        """Set event status to COMPLETED and record processed_at timestamp."""
        statement = (
            update(EventOutbox)
            .where(EventOutbox.id == event_id)
            .values(
                status=EventStatus.COMPLETED,
                processed_at=datetime.now(UTC),
            )
        )
        await self.session.execute(statement)
        await self.session.flush()

    async def mark_failed(self, event_id: uuid.UUID, error: str) -> None:
        """Increment retry_count and set last_error.

        If retry_count >= max_retries, set status to FAILED.
        Otherwise, set status back to PENDING for retry.
        """
        # Fetch the current event to check retry state
        statement = select(EventOutbox).where(EventOutbox.id == event_id)
        result = await self.session.execute(statement)
        event = result.scalar_one()

        new_retry_count = event.retry_count + 1
        new_status = (
            EventStatus.FAILED
            if new_retry_count >= event.max_retries
            else EventStatus.PENDING
        )

        update_statement = (
            update(EventOutbox)
            .where(EventOutbox.id == event_id)
            .values(
                retry_count=new_retry_count,
                last_error=error,
                status=new_status,
            )
        )
        await self.session.execute(update_statement)
        await self.session.flush()
