"""Celery tasks for RFQ lifecycle automation."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from celery_app import celery
from src.config import settings
from src.database.engine import async_session
from src.models.enums import (
    InvitationStatus,
    RfqStatus,
    RfqTransitionType,
)
from src.models.rfq import Rfq
from src.models.rfq_invitation import RfqInvitation

logger = logging.getLogger(__name__)

# System user UUID for automated transitions
_SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"


async def _auto_open_bidding_async() -> dict:
    """Transition PUBLISHED RFQs to BIDDING_OPEN when bidding_start <= now."""
    from src.modules.rfq.rfq_service import RfqService

    stats = {"checked": 0, "opened": 0, "errors": 0}
    now = datetime.now(UTC)

    async with async_session() as session:
        result = await session.execute(
            select(Rfq).where(
                Rfq.status == RfqStatus.PUBLISHED,
                Rfq.bidding_start.isnot(None),
                Rfq.bidding_start <= now,
            )
        )
        rfqs = list(result.scalars().all())
        stats["checked"] = len(rfqs)

        svc = RfqService(session)
        for rfq in rfqs:
            try:
                await svc.transition(
                    rfq_id=rfq.id,
                    transition_type=RfqTransitionType.OPEN_BIDDING,
                    triggered_by=_SYSTEM_USER_ID,
                    trigger_source="SYSTEM",
                    reason="Automated: bidding_start reached",
                )
                stats["opened"] += 1
            except Exception:
                logger.exception("Error auto-opening bidding for RFQ %s", rfq.id)
                stats["errors"] += 1

        await session.commit()

    return stats


async def _auto_close_bidding_async() -> dict:
    """Transition BIDDING_OPEN RFQs to BIDDING_CLOSED when bidding_deadline <= now."""
    from src.modules.rfq.rfq_service import RfqService

    stats = {"checked": 0, "closed": 0, "errors": 0}
    now = datetime.now(UTC)

    async with async_session() as session:
        result = await session.execute(
            select(Rfq).where(
                Rfq.status == RfqStatus.BIDDING_OPEN,
                Rfq.bidding_deadline.isnot(None),
                Rfq.bidding_deadline <= now,
            )
        )
        rfqs = list(result.scalars().all())
        stats["checked"] = len(rfqs)

        svc = RfqService(session)
        for rfq in rfqs:
            try:
                await svc.transition(
                    rfq_id=rfq.id,
                    transition_type=RfqTransitionType.CLOSE_BIDDING,
                    triggered_by=_SYSTEM_USER_ID,
                    trigger_source="SYSTEM",
                    reason="Automated: bidding_deadline reached",
                )
                stats["closed"] += 1
            except Exception:
                logger.exception("Error auto-closing bidding for RFQ %s", rfq.id)
                stats["errors"] += 1

        await session.commit()

    return stats


async def _auto_archive_drafts_async() -> dict:
    """Cancel DRAFT RFQs older than rfq_draft_ttl_days."""
    from src.modules.rfq.rfq_service import RfqService

    stats = {"checked": 0, "archived": 0, "errors": 0}
    cutoff = datetime.now(UTC) - timedelta(days=settings.rfq_draft_ttl_days)

    async with async_session() as session:
        result = await session.execute(
            select(Rfq).where(
                Rfq.status == RfqStatus.DRAFT,
                Rfq.created_at < cutoff,
            )
        )
        rfqs = list(result.scalars().all())
        stats["checked"] = len(rfqs)

        svc = RfqService(session)
        for rfq in rfqs:
            try:
                await svc.transition(
                    rfq_id=rfq.id,
                    transition_type=RfqTransitionType.CANCEL,
                    triggered_by=_SYSTEM_USER_ID,
                    trigger_source="SYSTEM",
                    reason=f"Automated: DRAFT older than {settings.rfq_draft_ttl_days} days",
                )
                stats["archived"] += 1
            except Exception:
                logger.exception("Error auto-archiving DRAFT RFQ %s", rfq.id)
                stats["errors"] += 1

        await session.commit()

    return stats


async def _expire_pending_invitations_async() -> dict:
    """Expire PENDING invitations for RFQs past BIDDING_OPEN."""
    stats = {"expired": 0}

    async with async_session() as session:
        # Find RFQs that are past the BIDDING_OPEN phase
        past_bidding_statuses = [
            RfqStatus.BIDDING_CLOSED,
            RfqStatus.EVALUATION,
            RfqStatus.AWARDED,
            RfqStatus.COMPLETED,
            RfqStatus.CANCELLED,
        ]
        rfq_ids_subquery = (
            select(Rfq.id)
            .where(Rfq.status.in_(past_bidding_statuses))
            .scalar_subquery()
        )

        result = await session.execute(
            update(RfqInvitation)
            .where(
                RfqInvitation.status == InvitationStatus.PENDING,
                RfqInvitation.rfq_id.in_(rfq_ids_subquery),
            )
            .values(status=InvitationStatus.EXPIRED)
        )
        stats["expired"] = result.rowcount
        await session.commit()

    return stats


# ---------------------------------------------------------------------------
# Celery task definitions
# ---------------------------------------------------------------------------


@celery.task(name="src.modules.rfq.tasks.auto_open_bidding")
def auto_open_bidding():
    """Auto-transition PUBLISHED RFQs to BIDDING_OPEN."""
    stats = asyncio.run(_auto_open_bidding_async())
    logger.info("auto_open_bidding complete: %s", stats)
    return stats


@celery.task(name="src.modules.rfq.tasks.auto_close_bidding")
def auto_close_bidding():
    """Auto-transition BIDDING_OPEN RFQs to BIDDING_CLOSED."""
    stats = asyncio.run(_auto_close_bidding_async())
    logger.info("auto_close_bidding complete: %s", stats)
    return stats


@celery.task(name="src.modules.rfq.tasks.auto_archive_drafts")
def auto_archive_drafts():
    """Cancel stale DRAFT RFQs."""
    stats = asyncio.run(_auto_archive_drafts_async())
    logger.info("auto_archive_drafts complete: %s", stats)
    return stats


@celery.task(name="src.modules.rfq.tasks.expire_pending_invitations")
def expire_pending_invitations():
    """Expire PENDING invitations on RFQs past bidding phase."""
    stats = asyncio.run(_expire_pending_invitations_async())
    logger.info("expire_pending_invitations complete: %s", stats)
    return stats
