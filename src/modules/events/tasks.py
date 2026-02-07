"""Celery tasks for event outbox processing."""

from celery_app import celery
from src.modules.events.outbox_processor import OutboxProcessor


@celery.task(name="src.modules.events.tasks.process_outbox")
def process_outbox():
    """Process a batch of pending outbox events."""
    processor = OutboxProcessor()
    return processor.process_batch()


@celery.task(name="src.modules.events.tasks.cleanup_processed_events")
def cleanup_processed_events():
    """Delete expired processed_events and old completed outbox entries."""
    processor = OutboxProcessor()
    return processor.cleanup_expired()
