"""Celery tasks for asynchronous embedding generation."""

import logging
from uuid import UUID

from celery import shared_task
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.database.engine import sync_engine
from src.modules.search.constants import EMBEDDING_BATCH_SIZE, EMBEDDING_DIMENSIONS, EMBEDDING_MODEL

logger = logging.getLogger(__name__)


def _build_product_text(row) -> str:
    """Build embedding text from a product row (sync context)."""
    parts: list[str] = [row.name]
    if row.description:
        parts.append(row.description)
    parts.append(f"IMPA {row.impa_code}")
    if row.category_name:
        parts.append(row.category_name)
    return " | ".join(parts)


@shared_task(bind=True, name="search.generate_embeddings")
def generate_embeddings(self, product_ids: list[str]) -> dict:
    """Generate and store embeddings for the given product IDs.

    Runs synchronously inside a Celery worker. Uses the synchronous OpenAI
    client and the sync SQLAlchemy engine.
    """
    import openai

    from src.config import settings

    client = openai.OpenAI(api_key=settings.openai_api_key)
    processed = 0
    errors = 0

    for batch_start in range(0, len(product_ids), EMBEDDING_BATCH_SIZE):
        batch_ids = product_ids[batch_start : batch_start + EMBEDDING_BATCH_SIZE]

        with Session(sync_engine) as session:
            # Fetch products for this batch using ANY(:ids) with array parameter
            # to avoid f-string SQL interpolation
            rows = session.execute(
                text("""
                    SELECT p.id, p.impa_code, p.name, p.description, c.name AS category_name
                    FROM products p
                    LEFT JOIN categories c ON c.id = p.category_id
                    WHERE p.id = ANY(:ids::uuid[])
                """),
                {"ids": batch_ids},
            ).fetchall()

            if not rows:
                continue

            texts = [_build_product_text(row) for row in rows]

            try:
                response = client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=texts,
                    dimensions=EMBEDDING_DIMENSIONS,
                )
                sorted_data = sorted(response.data, key=lambda d: d.index)
            except Exception:
                logger.exception("OpenAI embedding request failed for batch starting at %d", batch_start)
                errors += len(batch_ids)
                continue

            # Update each product's embedding
            for row, embedding_data in zip(rows, sorted_data):
                try:
                    session.execute(
                        text(
                            "UPDATE products SET embedding = :emb::vector, "
                            "embedding_updated_at = NOW() "
                            "WHERE id = :id"
                        ),
                        {"emb": str(embedding_data.embedding), "id": str(row.id)},
                    )
                    processed += 1
                except Exception:
                    logger.exception("Failed to update embedding for product %s", row.id)
                    errors += 1

            session.commit()

        # Update Celery task progress
        self.update_state(
            state="PROGRESS",
            meta={"processed": processed, "total": len(product_ids), "errors": errors},
        )

    return {"processed": processed, "total": len(product_ids), "errors": errors}


@shared_task(
    bind=True,
    name="search.sync_search_index",
    max_retries=3,
    default_retry_delay=60,
)
def sync_search_index(self) -> dict:
    """Periodic re-embedding of stale products.

    Finds products where updated_at > embedding_updated_at (stale embedding)
    or embedding IS NULL (missing embedding) and regenerates their embeddings.
    """
    import openai

    from src.config import settings

    client = openai.OpenAI(api_key=settings.openai_api_key)
    processed = 0
    errors = 0

    with Session(sync_engine) as session:
        # Count total stale/missing embeddings
        total_row = session.execute(
            text("""
                SELECT count(*) AS cnt FROM products
                WHERE embedding IS NULL
                   OR embedding_updated_at IS NULL
                   OR updated_at > embedding_updated_at
            """)
        ).scalar_one()
        total = int(total_row)

    if total == 0:
        return {"processed": 0, "total": 0, "errors": 0}

    batch_offset = 0
    while batch_offset < total:
        with Session(sync_engine) as session:
            rows = session.execute(
                text("""
                    SELECT p.id, p.impa_code, p.name, p.description, c.name AS category_name
                    FROM products p
                    LEFT JOIN categories c ON c.id = p.category_id
                    WHERE p.embedding IS NULL
                       OR p.embedding_updated_at IS NULL
                       OR p.updated_at > p.embedding_updated_at
                    ORDER BY p.updated_at DESC
                    LIMIT :batch_size
                """),
                {"batch_size": EMBEDDING_BATCH_SIZE},
            ).fetchall()

            if not rows:
                break

            texts = [_build_product_text(row) for row in rows]

            try:
                response = client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=texts,
                    dimensions=EMBEDDING_DIMENSIONS,
                )
                sorted_data = sorted(response.data, key=lambda d: d.index)
            except Exception as exc:
                logger.exception("OpenAI embedding request failed in sync_search_index at offset %d", batch_offset)
                errors += len(rows)
                try:
                    raise self.retry(exc=exc)
                except self.MaxRetriesExceededError:
                    return {"processed": processed, "total": total, "errors": errors}

            for row, embedding_data in zip(rows, sorted_data):
                try:
                    session.execute(
                        text(
                            "UPDATE products SET embedding = :emb::vector, "
                            "embedding_updated_at = NOW(), embedding_model = :model "
                            "WHERE id = :id"
                        ),
                        {
                            "emb": str(embedding_data.embedding),
                            "model": EMBEDDING_MODEL,
                            "id": str(row.id),
                        },
                    )
                    processed += 1
                except Exception:
                    logger.exception("Failed to update embedding for product %s", row.id)
                    errors += 1

            session.commit()

        batch_offset += EMBEDDING_BATCH_SIZE
        self.update_state(
            state="PROGRESS",
            meta={"processed": processed, "total": total, "errors": errors},
        )

    return {"processed": processed, "total": total, "errors": errors}


@shared_task(
    bind=True,
    name="search.bulk_generate_embeddings",
    max_retries=5,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
)
def bulk_generate_embeddings(self, batch_size: int = 100) -> dict:
    """Batch generate embeddings for all products missing embeddings.

    Idempotent -- skips products that already have embeddings.
    Uses exponential backoff for retries per ADR-NF-008.
    """
    import openai

    from src.config import settings

    client = openai.OpenAI(api_key=settings.openai_api_key)
    processed = 0
    errors = 0

    with Session(sync_engine) as session:
        total = int(
            session.execute(
                text("SELECT count(*) FROM products WHERE embedding IS NULL")
            ).scalar_one()
        )

    if total == 0:
        return {"processed": 0, "total": 0, "errors": 0}

    while True:
        with Session(sync_engine) as session:
            rows = session.execute(
                text("""
                    SELECT p.id, p.impa_code, p.name, p.description, c.name AS category_name
                    FROM products p
                    LEFT JOIN categories c ON c.id = p.category_id
                    WHERE p.embedding IS NULL
                    LIMIT :batch_size
                """),
                {"batch_size": batch_size},
            ).fetchall()

            if not rows:
                break

            texts = [_build_product_text(row) for row in rows]

            try:
                response = client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=texts,
                    dimensions=EMBEDDING_DIMENSIONS,
                )
                sorted_data = sorted(response.data, key=lambda d: d.index)
            except Exception:
                logger.exception("OpenAI embedding request failed in bulk_generate_embeddings")
                errors += len(rows)
                # Let autoretry_for handle the retry with backoff
                raise

            for row, embedding_data in zip(rows, sorted_data):
                try:
                    session.execute(
                        text(
                            "UPDATE products SET embedding = :emb::vector, "
                            "embedding_updated_at = NOW(), embedding_model = :model "
                            "WHERE id = :id"
                        ),
                        {
                            "emb": str(embedding_data.embedding),
                            "model": EMBEDDING_MODEL,
                            "id": str(row.id),
                        },
                    )
                    processed += 1
                except Exception:
                    logger.exception("Failed to update embedding for product %s", row.id)
                    errors += 1

            session.commit()

        self.update_state(
            state="PROGRESS",
            meta={"processed": processed, "total": total, "errors": errors},
        )

    return {"processed": processed, "total": total, "errors": errors}
