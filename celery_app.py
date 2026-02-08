"""Celery application configuration for PortiQ background tasks."""

from celery import Celery
from celery.schedules import crontab

from src.config import settings

celery = Celery("portiq")

celery.conf.update(
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # --- Queue routing per job type ---
    task_routes={
        "search.generate_embeddings": {"queue": "embedding"},
        "search.sync_search_index": {"queue": "search-sync"},
        "search.bulk_generate_embeddings": {"queue": "embedding"},
        "src.modules.notifications.*": {"queue": "notifications"},
        "src.modules.document_ai.*": {"queue": "document-processing"},
        "src.modules.supplier.*": {"queue": "supplier-verification"},
        "src.modules.vessel.tasks.poll_vessel_positions": {"queue": "vessel-tracking"},
        "src.modules.vessel.tasks.poll_vessel_eta": {"queue": "vessel-tracking"},
        "src.modules.vessel.tasks.poll_port_arrivals": {"queue": "vessel-tracking"},
        "src.modules.vessel.tasks.fetch_vessel_position": {"queue": "vessel-tracking"},
        "src.modules.vessel.tasks.backfill_vessel_history": {"queue": "vessel-tracking"},
        "src.modules.vessel.tasks.cleanup_vessel_data": {"queue": "vessel-tracking"},
        "src.modules.events.tasks.process_outbox": {"queue": "event-outbox"},
        "src.modules.events.tasks.cleanup_processed_events": {"queue": "event-outbox"},
        "src.modules.rfq.tasks.auto_open_bidding": {"queue": "rfq-bidding"},
        "src.modules.rfq.tasks.auto_close_bidding": {"queue": "rfq-bidding"},
        "src.modules.rfq.tasks.auto_archive_drafts": {"queue": "rfq-bidding"},
        "src.modules.rfq.tasks.expire_pending_invitations": {"queue": "rfq-bidding"},
    },
    # --- Reliability settings ---
    task_default_retry_delay=60,
    task_max_retries=3,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=86400,  # 24 hours
    # --- Broker transport options (Redis reliability) ---
    broker_transport_options={
        "max_retries": 10,
        "interval_start": 0.2,
        "interval_step": 0.5,
        "interval_max": 5.0,
        "retry_on_timeout": True,
        "visibility_timeout": 3600,
    },
    # --- Beat schedule ---
    beat_schedule={
        "poll-vessel-positions": {
            "task": "src.modules.vessel.tasks.poll_vessel_positions",
            "schedule": settings.vessel_position_poll_seconds,
        },
        "poll-vessel-eta": {
            "task": "src.modules.vessel.tasks.poll_vessel_eta",
            "schedule": settings.vessel_eta_poll_seconds,
        },
        "poll-port-arrivals": {
            "task": "src.modules.vessel.tasks.poll_port_arrivals",
            "schedule": settings.vessel_arrival_poll_seconds,
        },
        "process-event-outbox": {
            "task": "src.modules.events.tasks.process_outbox",
            "schedule": settings.event_outbox_poll_seconds,
        },
        "cleanup-vessel-data-daily": {
            "task": "src.modules.vessel.tasks.cleanup_vessel_data",
            "schedule": crontab(hour=3, minute=0),
        },
        "cleanup-processed-events-daily": {
            "task": "src.modules.events.tasks.cleanup_processed_events",
            "schedule": crontab(hour=3, minute=30),
        },
        "rfq-auto-open-bidding": {
            "task": "src.modules.rfq.tasks.auto_open_bidding",
            "schedule": settings.rfq_auto_close_poll_seconds,
        },
        "rfq-auto-close-bidding": {
            "task": "src.modules.rfq.tasks.auto_close_bidding",
            "schedule": settings.rfq_auto_close_poll_seconds,
        },
        "rfq-auto-archive-drafts": {
            "task": "src.modules.rfq.tasks.auto_archive_drafts",
            "schedule": crontab(hour=4, minute=0),
        },
        "rfq-expire-pending-invitations": {
            "task": "src.modules.rfq.tasks.expire_pending_invitations",
            "schedule": 300,
        },
    },
)

celery.autodiscover_tasks([
    "src.modules.search",
    "src.modules.supplier",
    "src.modules.vessel",
    "src.modules.events",
    "src.modules.rfq",
])
