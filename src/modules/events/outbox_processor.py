"""OutboxProcessor — synchronous batch processor for Celery workers."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.database.engine import sync_engine
from src.modules.events.handlers import EventHandlerRegistry

logger = logging.getLogger(__name__)


class OutboxProcessor:
    """Processes pending outbox events using sync sessions (for Celery workers).

    Uses SELECT ... FOR UPDATE SKIP LOCKED for safe multi-worker concurrency.
    Tracks idempotency via the processed_events table.
    """

    def process_batch(self, batch_size: int = 50) -> dict:
        """Process a batch of pending events.

        Returns dict with 'processed' and 'failed' counts.
        """
        processed_count = 0
        failed_count = 0

        with Session(sync_engine) as session:
            # Fetch pending events with row-level locking, skipping already-locked rows
            pending_rows = session.execute(
                text("""
                    SELECT id, event_type, aggregate_type, aggregate_id,
                           payload, retry_count, max_retries
                    FROM event_outbox
                    WHERE status = 'PENDING'
                    ORDER BY created_at ASC
                    LIMIT :batch_size
                    FOR UPDATE SKIP LOCKED
                """),
                {"batch_size": batch_size},
            ).fetchall()

            for row in pending_rows:
                event_id = row.id
                event_type = row.event_type
                payload = row.payload
                retry_count = row.retry_count
                max_retries = row.max_retries

                try:
                    # Check idempotency — skip if already processed
                    already_processed = session.execute(
                        text("""
                            SELECT 1 FROM processed_events
                            WHERE event_id = :event_id
                            LIMIT 1
                        """),
                        {"event_id": event_id},
                    ).fetchone()

                    if already_processed:
                        # Mark as completed and skip
                        session.execute(
                            text("""
                                UPDATE event_outbox
                                SET status = 'COMPLETED', processed_at = now()
                                WHERE id = :event_id
                            """),
                            {"event_id": event_id},
                        )
                        session.commit()
                        processed_count += 1
                        continue

                    # Mark as PROCESSING (no commit yet — stays in same txn
                    # so a crash rolls back to PENDING automatically)
                    session.execute(
                        text("""
                            UPDATE event_outbox SET status = 'PROCESSING'
                            WHERE id = :event_id
                        """),
                        {"event_id": event_id},
                    )

                    # Dispatch to registered handlers
                    results = EventHandlerRegistry.dispatch(event_type, payload)

                    # Check if any handler failed
                    handler_errors = [r for r in results if r["status"] == "error"]
                    if handler_errors:
                        error_messages = "; ".join(
                            f"{r['handler']}: {r['error']}" for r in handler_errors
                        )
                        raise RuntimeError(f"Handler errors: {error_messages}")

                    # Record in processed_events for idempotency
                    expires_at = datetime.now(UTC) + timedelta(days=7)
                    session.execute(
                        text("""
                            INSERT INTO processed_events
                                (event_id, event_type, handler_name, processed_at, expires_at)
                            VALUES
                                (:event_id, :event_type, :handler_name, now(), :expires_at)
                        """),
                        {
                            "event_id": event_id,
                            "event_type": event_type,
                            "handler_name": ",".join(
                                r["handler"] for r in results
                            ) if results else "no_handlers",
                            "expires_at": expires_at,
                        },
                    )

                    # Mark COMPLETED
                    session.execute(
                        text("""
                            UPDATE event_outbox
                            SET status = 'COMPLETED', processed_at = now()
                            WHERE id = :event_id
                        """),
                        {"event_id": event_id},
                    )
                    session.commit()
                    processed_count += 1

                except Exception as exc:
                    session.rollback()
                    logger.exception(
                        "Failed to process event %s (type=%s)", event_id, event_type
                    )

                    new_retry_count = retry_count + 1
                    new_status = (
                        "FAILED" if new_retry_count >= max_retries else "PENDING"
                    )

                    session.execute(
                        text("""
                            UPDATE event_outbox
                            SET status = :new_status,
                                retry_count = :retry_count,
                                last_error = :error
                            WHERE id = :event_id
                        """),
                        {
                            "new_status": new_status,
                            "retry_count": new_retry_count,
                            "error": str(exc),
                            "event_id": event_id,
                        },
                    )
                    session.commit()
                    failed_count += 1

        return {"processed": processed_count, "failed": failed_count}

    def cleanup_expired(self) -> int:
        """Delete expired processed_events and old completed outbox events.

        Returns total number of rows deleted.
        """
        total_deleted = 0

        with Session(sync_engine) as session:
            # Delete processed_events past their TTL
            result = session.execute(
                text("DELETE FROM processed_events WHERE expires_at < now()")
            )
            total_deleted += result.rowcount

            # Delete completed outbox events older than 30 days
            result = session.execute(
                text("""
                    DELETE FROM event_outbox
                    WHERE status = 'COMPLETED'
                      AND processed_at < now() - INTERVAL '30 days'
                """)
            )
            total_deleted += result.rowcount

            session.commit()

        logger.info("Cleaned up %d expired event records", total_deleted)
        return total_deleted
