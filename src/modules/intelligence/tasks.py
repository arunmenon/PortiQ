"""Celery tasks for market intelligence — materialized view refreshes."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from celery_app import celery
from src.database.engine import sync_engine

logger = logging.getLogger(__name__)


@celery.task(name="src.modules.intelligence.tasks.refresh_price_benchmarks")
def refresh_price_benchmarks() -> dict:
    """Refresh the price benchmarks materialized view.

    Called daily by Celery beat schedule. Uses CONCURRENTLY to avoid
    locking reads during refresh.
    """
    logger.info("Refreshing mv_price_benchmarks materialized view")
    try:
        with Session(sync_engine) as session:
            session.execute(
                text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_price_benchmarks")
            )
            session.commit()
        logger.info("mv_price_benchmarks refresh completed")
        return {"status": "ok", "view": "mv_price_benchmarks"}
    except Exception:
        logger.exception("Failed to refresh mv_price_benchmarks")
        raise


@celery.task(name="src.modules.intelligence.tasks.refresh_supplier_scores")
def refresh_supplier_scores() -> dict:
    """Refresh the supplier scores materialized view.

    Called daily by Celery beat schedule. Uses CONCURRENTLY to avoid
    locking reads during refresh.
    """
    logger.info("Refreshing mv_supplier_scores materialized view")
    try:
        with Session(sync_engine) as session:
            session.execute(
                text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_supplier_scores")
            )
            session.commit()
        logger.info("mv_supplier_scores refresh completed")
        return {"status": "ok", "view": "mv_supplier_scores"}
    except Exception:
        logger.exception("Failed to refresh mv_supplier_scores")
        raise
