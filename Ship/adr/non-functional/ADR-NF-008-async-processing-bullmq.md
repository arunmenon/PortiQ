# ADR-NF-008: Async Processing (Celery)

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

The platform requires reliable asynchronous job processing for long-running tasks, background work, and event-driven operations.

### Business Context
Async processing needs:
- Document AI pipeline (parsing, extraction, matching)
- Email and notification delivery
- Report generation
- Data import/export operations
- Scheduled tasks (cleanup, sync, reminders)
- Webhook delivery with retries

### Technical Context
- FastAPI backend with Python
- Redis available for caching (ADR-NF-005)
- Need for job retries, priorities, and scheduling
- Worker scaling independent of API
- Job monitoring and visibility

### Assumptions
- Redis is the queue backend
- Job persistence needed for reliability
- Multiple worker instances possible
- Job monitoring UI helpful for operations

---

## Decision Drivers

- Reliability and durability
- Python support
- FastAPI integration
- Redis compatibility
- Job monitoring capabilities
- Scalability

---

## Considered Options

### Option 1: Celery
**Description:** Distributed task queue with Redis broker and rich Python ecosystem.

**Pros:**
- Mature Python task queue (10+ years)
- Redis and RabbitMQ broker support
- Advanced features (priorities, delays, retries, canvas workflows)
- Rate limiting built-in
- Flower for monitoring
- Excellent ecosystem (celery-beat for scheduling)

**Cons:**
- Redis dependency for broker
- Memory usage for large queues

### Option 2: AWS SQS + Lambda
**Description:** Cloud-native serverless queue processing.

**Pros:**
- Fully managed
- Auto-scaling
- Pay per use
- High durability

**Cons:**
- AWS lock-in
- Cold starts
- Different programming model
- Limited to Lambda constraints

### Option 3: RabbitMQ
**Description:** Traditional message broker.

**Pros:**
- Mature and proven
- Complex routing patterns
- Multiple protocols
- Clustering

**Cons:**
- Additional infrastructure
- More complex operations
- Heavier than Redis-based solutions

### Option 4: Database-Backed Queue
**Description:** PostgreSQL table as job queue.

**Pros:**
- No additional infrastructure
- ACID guarantees
- Simple setup

**Cons:**
- Polling overhead
- Limited features
- Performance ceiling
- Not purpose-built

---

## Decision

**Chosen Option:** Celery

We will use Celery for asynchronous job processing, leveraging its Python ecosystem, Redis broker support, and advanced queue features.

### Rationale
Celery is the natural choice given our Python backend and existing Redis infrastructure (ADR-NF-005). As the most mature Python task queue, it provides excellent developer experience with canvas workflows (chains, groups, chords), beat scheduler for periodic tasks, and Flower for monitoring. Advanced features like priorities, retries, and rate limiting handle our complex processing needs.

---

## Consequences

### Positive
- Excellent Python ecosystem integration
- Advanced queue features out of the box (canvas, beat, result backends)
- Unified with caching infrastructure (Redis)
- Flower for monitoring
- Reliable job processing with retries

### Negative
- Redis memory usage for large queues
- **Mitigation:** Job data in database, only references in queue
- Single Redis dependency
- **Mitigation:** Redis Cluster for HA if needed

### Risks
- Redis failure loses queue: Redis persistence, HA configuration
- Job processing bottlenecks: Horizontal worker scaling
- Memory exhaustion: Job TTL, data externalization

---

## Implementation Notes

### Celery Configuration

```python
# celery_app.py
from celery import Celery
from src.config import settings

celery = Celery(
    "portiq",
    broker=settings.celery_broker_url,   # redis://localhost:6379/0
    backend=settings.celery_result_backend,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    task_default_retry_delay=60,
    task_max_retries=3,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=86400,  # 24 hours
    task_routes={
        "src.modules.search.tasks.*": {"queue": "embedding"},
        "src.modules.document_ai.tasks.*": {"queue": "document-processing"},
        "src.modules.notifications.tasks.*": {"queue": "notifications"},
    },
)

# Auto-discover tasks in all modules
celery.autodiscover_tasks(["src.modules.search", "src.modules.notifications"])

# Queue names
QUEUES = {
    "DOCUMENT_PROCESSING": "document-processing",
    "EMAIL": "email",
    "NOTIFICATIONS": "notifications",
    "DATA_IMPORT": "data-import",
    "REPORTS": "reports",
    "WEBHOOKS": "webhooks",
    "EMBEDDING": "embedding",
}
```

### Task Producer

```python
# src/modules/document_ai/service.py
from src.modules.document_ai.tasks import parse_document

class DocumentProcessorService:
    def process_document(self, document_id: str, urgent: bool = False) -> str:
        result = parse_document.apply_async(
            args=[document_id],
            priority=1 if urgent else 5,
            task_id=f"doc-{document_id}",  # Deduplication
        )
        return result.id

    def process_document_batch(self, document_ids: list[str]) -> list[str]:
        from celery import group
        job_group = group(
            parse_document.s(doc_id) for doc_id in document_ids
        )
        result = job_group.apply_async()
        return [r.id for r in result.children]

    def get_job_status(self, job_id: str) -> dict | None:
        from celery.result import AsyncResult
        result = AsyncResult(job_id)
        if not result.id:
            return None
        return {
            "id": result.id,
            "state": result.state,
            "progress": result.info if isinstance(result.info, dict) else None,
        }
```

### Task Consumer (Worker)

```python
# src/modules/document_ai/tasks.py
import logging
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@shared_task(bind=True, max_retries=5, default_retry_delay=30, rate_limit="10/s")
def parse_document(self, document_id: str):
    """Process a document through the AI pipeline."""
    logger.info(f"Processing document {document_id}")

    try:
        # Step 1: Parse document
        self.update_state(state="PROGRESS", meta={"step": "parsing", "progress": 10})
        parsed = parsing_service.parse(document_id)

        # Step 2: Extract line items
        self.update_state(state="PROGRESS", meta={"step": "extraction", "progress": 40})
        extracted = extraction_service.extract(parsed)

        # Step 3: Match to SKUs
        self.update_state(state="PROGRESS", meta={"step": "matching", "progress": 70})
        matched = matching_service.match(extracted)

        # Step 4: Save results
        self.update_state(state="PROGRESS", meta={"step": "saving", "progress": 90})
        save_results(document_id, matched)

        return {
            "document_id": document_id,
            "line_items_extracted": len(extracted),
            "matched_items": sum(1 for m in matched if m.confidence > 0.8),
            "requires_review": sum(1 for m in matched if m.confidence <= 0.8),
        }

    except Exception as exc:
        logger.error(f"Failed to process document {document_id}: {exc}")
        raise self.retry(exc=exc)
```

### Email Task

```python
# src/modules/notifications/tasks.py
from celery import shared_task, group

@shared_task(bind=True, max_retries=3, default_retry_delay=60, queue="email")
def send_email(self, to: str, template: str, data: dict, attachments: list | None = None):
    """Send a single email."""
    rendered = template_service.render(template, data)
    email_service.send(to=to, subject=rendered.subject, html=rendered.html, text=rendered.text,
                       attachments=attachments)

# Usage
def send_order_confirmation(order):
    send_email.delay(
        to=order.buyer_email,
        template="order-confirmation",
        data={"order_number": order.order_number, "items": order.line_items, "total": order.total},
    )

def send_bulk_notification(emails: list[str], template: str, data: dict):
    job_group = group(
        send_email.s(email, template, data).set(priority=10) for email in emails
    )
    job_group.apply_async()
```

### Scheduled Jobs (Celery Beat)

```python
# celery_app.py — Beat schedule
from celery.schedules import crontab

celery.conf.beat_schedule = {
    "sync-impa-catalog": {
        "task": "src.modules.catalog.tasks.sync_impa_catalog",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    "cleanup-expired-sessions": {
        "task": "src.modules.auth.tasks.cleanup_expired_sessions",
        "schedule": 3600.0,  # Every hour
    },
}
# Run: celery -A celery_app beat --loglevel=info
```

### Flower Monitoring Dashboard

```bash
# Run Flower for Celery monitoring (equivalent to Bull Board)
celery -A celery_app flower --port=5555 --broker=redis://localhost:6379/0

# Access dashboard at http://localhost:5555
# Features: real-time task monitoring, worker status, task history, rate control
```

### Task Flow (Multi-Step Processing via Celery Canvas)

```python
# src/modules/document_ai/flows.py
from celery import chain
from .tasks import parse_document_step, extract_items_step, match_skus_step, save_results_step

def create_processing_flow(document_id: str) -> str:
    """Chain tasks sequentially: parse -> extract -> match -> save."""
    workflow = chain(
        parse_document_step.s(document_id),
        extract_items_step.s(),
        match_skus_step.s(),
        save_results_step.s(document_id),
    )
    result = workflow.apply_async()
    return result.id
```

### Dependencies
- ADR-NF-005: Caching Strategy (Redis)
- ADR-FN-006: Document AI Pipeline Architecture
- ADR-NF-009: Event-Driven Communication

### Migration Strategy
1. Set up Celery with Redis broker
2. Create task routing and queue configurations
3. Implement document processing tasks
4. Add email/notification tasks
5. Set up scheduled jobs via Celery Beat
6. Deploy Flower for monitoring
7. Scale workers as needed

---

## Retry and Error Handling

### Retry Policy by Job Type

| Queue | Max Retries | Backoff | Initial Delay | Max Delay |
|-------|-------------|---------|---------------|-----------|
| document-processing | 5 | Exponential | 30s | 10min |
| email-delivery | 3 | Exponential | 60s | 15min |
| webhook-delivery | 5 | Exponential | 10s | 5min |
| data-export | 2 | Fixed | 5min | 5min |
| scheduled-tasks | 1 | None | - | - |

```python
# Celery task with retry policy
@shared_task(bind=True, max_retries=5, default_retry_delay=30,
             autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=600)
def process_document(self, document_id: str):
    ...
```

### Dead Letter Queue (DLQ) Handling

```python
# Celery signal-based DLQ handling
from celery.signals import task_failure

@task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None, args=None, kwargs=None,
                        traceback=None, einfo=None, **kw):
    """Move permanently failed tasks to DLQ for manual review."""
    if sender.request.retries >= sender.max_retries:
        logger.error(f"Task permanently failed: {sender.name}", extra={
            "task_id": task_id, "error": str(exception), "args": args,
        })
        # Store for manual review
        failed_job_repository.save(
            queue=sender.name, payload={"args": args, "kwargs": kwargs},
            error=str(exception), failed_at=datetime.utcnow(),
        )
        # Alert on critical failures
        if _is_critical(sender.name):
            alert_service.send_pagerduty(
                title=f"Critical task failed: {sender.name}", details=str(exception),
            )
```

### Job Idempotency

| Job Type | Idempotency Key | Duplicate Window |
|----------|-----------------|------------------|
| Document processing | `doc:${documentId}` | 1 hour |
| Email delivery | `email:${userId}:${templateId}:${hash}` | 24 hours |
| Webhook delivery | `webhook:${eventId}` | 1 hour |
| Report generation | `report:${reportId}:${params}` | 5 minutes |

```python
# Idempotent task creation
from celery.result import AsyncResult

def queue_document_processing(document_id: str):
    task_id = f"doc:{document_id}"
    existing = AsyncResult(task_id)
    if existing.state in ("PENDING", "STARTED", "RETRY"):
        return existing  # Task already queued

    return parse_document.apply_async(
        args=[document_id], task_id=task_id,
    )
```

## Redis High Availability

### Redis Cluster Configuration

```
┌─────────────────────────────────────────────────────────────┐
│                     Redis Cluster (AWS ElastiCache)          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐                │
│   │ Primary │    │ Primary │    │ Primary │                │
│   │ (Shard1)│    │ (Shard2)│    │ (Shard3)│                │
│   └────┬────┘    └────┬────┘    └────┬────┘                │
│        │              │              │                      │
│   ┌────┴────┐    ┌────┴────┐    ┌────┴────┐                │
│   │ Replica │    │ Replica │    │ Replica │                │
│   └─────────┘    └─────────┘    └─────────┘                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Failover Behavior

| Scenario | Detection | Recovery | Data Loss |
|----------|-----------|----------|-----------|
| Replica failure | Auto (<30s) | Promote standby | None |
| Primary failure | Auto (<30s) | Promote replica | <30s jobs |
| Network partition | Auto | Reconnect | Jobs retry |
| Full cluster failure | Alert | Manual recovery | Recover from AOF |

### Celery Redis Failover Configuration

```python
# celery_app.py — Redis connection with failover
celery.conf.broker_transport_options = {
    "max_retries": 10,
    "interval_start": 0.2,
    "interval_step": 0.5,
    "interval_max": 5.0,
    "retry_on_timeout": True,
    "socket_keepalive": True,
    "visibility_timeout": 60,  # 60s lock
}

# Worker graceful shutdown: celery -A celery_app worker --concurrency=5
# Celery handles SIGTERM gracefully, finishing current tasks before shutdown
```

## Job Latency Requirements

### Maximum Acceptable Latency by Job Type

| Job Type | Queue Latency | Processing Time | End-to-End SLA |
|----------|---------------|-----------------|----------------|
| **Critical (document AI)** | <5s | <60s | <2 min |
| **Standard (notifications)** | <30s | <10s | <1 min |
| **Background (reports)** | <5min | <30min | <1 hour |
| **Scheduled (cleanup)** | N/A | <10min | Window-based |

### Latency Monitoring

```python
# Track task latency metrics via Celery signals
from celery.signals import task_postrun
import time

@task_postrun.connect
def track_task_latency(sender=None, task_id=None, state=None, retval=None, **kwargs):
    runtime = kwargs.get("runtime", 0)
    metrics_service.record_histogram("task_process_time", runtime, labels={
        "task": sender.name, "state": state,
    })
    sla = get_sla(sender.name)
    if runtime > sla:
        logger.warning(f"Task SLA breached: {sender.name} took {runtime}s (SLA: {sla}s)")
```

---

## References
- [Celery Documentation](https://docs.celeryq.dev/)
- [Celery Best Practices](https://docs.celeryq.dev/en/stable/userguide/tasks.html)
- [Flower Monitoring](https://flower.readthedocs.io/)
