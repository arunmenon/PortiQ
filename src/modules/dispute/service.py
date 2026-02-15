"""Dispute resolution service — CRUD, comments, state machine."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.exceptions import BusinessRuleException, NotFoundException
from src.models.dispute import Dispute
from src.models.dispute_comment import DisputeComment
from src.models.dispute_transition import DisputeTransition
from src.models.enums import DisputeResolutionType, DisputeStatus, DisputeType
from src.modules.dispute.constants import (
    EVENT_DISPUTE_ASSIGNED,
    EVENT_DISPUTE_COMMENTED,
    EVENT_DISPUTE_CREATED,
    EVENT_DISPUTE_ESCALATED,
    EVENT_DISPUTE_RESOLVED,
    SLA_RESOLUTION_HOURS,
    SLA_RESPONSE_HOURS,
    VALID_DISPUTE_TRANSITIONS,
)
from src.modules.events.outbox_service import OutboxService
from src.modules.tenancy.auth import AuthenticatedUser

logger = logging.getLogger(__name__)


class DisputeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Reference number generation
    # ------------------------------------------------------------------

    async def _generate_dispute_number(self) -> str:
        """Generate DSP-YYYY-NNNNNN dispute number using a DB sequence."""
        result = await self.db.execute(text("SELECT nextval('dispute_number_seq')"))
        seq_val = result.scalar()
        year = datetime.now(UTC).year
        return f"DSP-{year}-{seq_val:06d}"

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_dispute(
        self,
        data: dict,
        user: AuthenticatedUser,
    ) -> Dispute:
        """Create a new dispute in OPEN status."""
        dispute_number = await self._generate_dispute_number()
        now = datetime.now(UTC)

        dispute = Dispute(
            dispute_number=dispute_number,
            organization_id=user.organization_id,
            order_id=data["order_id"],
            delivery_id=data.get("delivery_id"),
            delivery_item_id=data.get("delivery_item_id"),
            vendor_order_id=data.get("vendor_order_id"),
            raised_by_org_id=user.organization_id,
            raised_by_user_id=user.id,
            supplier_org_id=data["supplier_org_id"],
            dispute_type=data["dispute_type"],
            status=DisputeStatus.OPEN,
            priority=data.get("priority", "MEDIUM"),
            title=data["title"],
            description=data["description"],
            disputed_amount=data.get("disputed_amount"),
            currency=data.get("currency", "USD"),
            response_due_at=now + timedelta(hours=SLA_RESPONSE_HOURS),
            resolution_due_at=now + timedelta(hours=SLA_RESOLUTION_HOURS),
        )
        self.db.add(dispute)
        await self.db.flush()

        # Record initial transition
        transition = DisputeTransition(
            dispute_id=dispute.id,
            from_status=DisputeStatus.OPEN,
            to_status=DisputeStatus.OPEN,
            transitioned_by=user.id,
            reason="Dispute created",
        )
        self.db.add(transition)
        await self.db.flush()

        # Emit event
        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=EVENT_DISPUTE_CREATED,
            aggregate_type="dispute",
            aggregate_id=str(dispute.id),
            payload={
                "dispute_id": str(dispute.id),
                "dispute_number": dispute_number,
                "order_id": str(data["order_id"]),
                "delivery_id": str(data["delivery_id"]) if data.get("delivery_id") else None,
                "type": data["dispute_type"].value if isinstance(data["dispute_type"], DisputeType) else data["dispute_type"],
                "raised_by": str(user.id),
            },
        )

        logger.info("Created dispute %s (%s)", dispute.id, dispute_number)
        return dispute

    async def list_disputes(
        self,
        organization_id: uuid.UUID,
        status: DisputeStatus | None = None,
        dispute_type: DisputeType | None = None,
        order_id: uuid.UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Dispute], int]:
        """List disputes visible to the calling organization (paginated)."""
        query = select(Dispute).where(
            (Dispute.organization_id == organization_id)
            | (Dispute.supplier_org_id == organization_id)
        )
        count_query = select(func.count()).select_from(Dispute).where(
            (Dispute.organization_id == organization_id)
            | (Dispute.supplier_org_id == organization_id)
        )

        if status is not None:
            query = query.where(Dispute.status == status)
            count_query = count_query.where(Dispute.status == status)

        if dispute_type is not None:
            query = query.where(Dispute.dispute_type == dispute_type)
            count_query = count_query.where(Dispute.dispute_type == dispute_type)

        if order_id is not None:
            query = query.where(Dispute.order_id == order_id)
            count_query = count_query.where(Dispute.order_id == order_id)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Dispute.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_dispute(self, dispute_id: uuid.UUID) -> Dispute:
        """Get a dispute by ID with comments and transitions loaded."""
        result = await self.db.execute(
            select(Dispute)
            .options(
                joinedload(Dispute.comments),
                joinedload(Dispute.transitions),
            )
            .where(Dispute.id == dispute_id)
        )
        dispute = result.unique().scalar_one_or_none()
        if dispute is None:
            raise NotFoundException(f"Dispute {dispute_id} not found")
        return dispute

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    async def add_comment(
        self,
        dispute_id: uuid.UUID,
        content: str,
        is_internal: bool,
        user: AuthenticatedUser,
        attachment_s3_key: str | None = None,
        attachment_filename: str | None = None,
        attachment_content_type: str | None = None,
    ) -> DisputeComment:
        """Add a comment to a dispute."""
        # Verify dispute exists
        dispute = await self.get_dispute(dispute_id)

        if dispute.status in (DisputeStatus.CLOSED,):
            raise BusinessRuleException("Cannot add comments to a closed dispute")

        comment = DisputeComment(
            dispute_id=dispute_id,
            author_id=user.id,
            author_org_id=user.organization_id,
            content=content,
            is_internal=is_internal,
            attachment_s3_key=attachment_s3_key,
            attachment_filename=attachment_filename,
            attachment_content_type=attachment_content_type,
        )
        self.db.add(comment)
        await self.db.flush()

        # Emit event
        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=EVENT_DISPUTE_COMMENTED,
            aggregate_type="dispute",
            aggregate_id=str(dispute_id),
            payload={
                "dispute_id": str(dispute_id),
                "comment_id": str(comment.id),
                "author_id": str(user.id),
                "is_internal": is_internal,
            },
        )

        logger.info("Added comment to dispute %s by user %s", dispute_id, user.id)
        return comment

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def _validate_transition(
        self, current_status: DisputeStatus, target_status: DisputeStatus
    ) -> None:
        """Validate that the transition is allowed by the state machine."""
        allowed = VALID_DISPUTE_TRANSITIONS.get(current_status, [])
        if target_status not in allowed:
            raise BusinessRuleException(
                f"Cannot transition from '{current_status.value}' to '{target_status.value}'. "
                f"Allowed transitions: {[s.value for s in allowed]}"
            )

    async def _record_transition(
        self,
        dispute_id: uuid.UUID,
        from_status: DisputeStatus,
        to_status: DisputeStatus,
        transitioned_by: uuid.UUID,
        reason: str | None = None,
    ) -> DisputeTransition:
        """Record a state transition for audit."""
        transition = DisputeTransition(
            dispute_id=dispute_id,
            from_status=from_status,
            to_status=to_status,
            transitioned_by=transitioned_by,
            reason=reason,
        )
        self.db.add(transition)
        await self.db.flush()
        return transition

    async def assign_reviewer(
        self,
        dispute_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        user: AuthenticatedUser,
    ) -> Dispute:
        """Assign a reviewer and transition to UNDER_REVIEW."""
        dispute = await self.get_dispute(dispute_id)
        old_status = dispute.status

        self._validate_transition(old_status, DisputeStatus.UNDER_REVIEW)

        dispute.assigned_reviewer_id = reviewer_id
        dispute.status = DisputeStatus.UNDER_REVIEW

        await self._record_transition(
            dispute_id=dispute.id,
            from_status=old_status,
            to_status=DisputeStatus.UNDER_REVIEW,
            transitioned_by=user.id,
            reason=f"Reviewer assigned: {reviewer_id}",
        )
        await self.db.flush()

        # Emit event
        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=EVENT_DISPUTE_ASSIGNED,
            aggregate_type="dispute",
            aggregate_id=str(dispute_id),
            payload={
                "dispute_id": str(dispute_id),
                "reviewer_id": str(reviewer_id),
            },
        )

        logger.info("Dispute %s assigned to reviewer %s", dispute_id, reviewer_id)
        return dispute

    async def resolve_dispute(
        self,
        dispute_id: uuid.UUID,
        resolution_type: DisputeResolutionType,
        resolution_amount: float | None,
        notes: str | None,
        user: AuthenticatedUser,
    ) -> Dispute:
        """Resolve a dispute with a financial outcome."""
        dispute = await self.get_dispute(dispute_id)
        old_status = dispute.status

        self._validate_transition(old_status, DisputeStatus.RESOLVED)

        now = datetime.now(UTC)
        dispute.status = DisputeStatus.RESOLVED
        dispute.resolution_type = resolution_type
        dispute.resolution_amount = resolution_amount
        dispute.resolution_notes = notes
        dispute.resolved_at = now
        dispute.resolved_by = user.id

        await self._record_transition(
            dispute_id=dispute.id,
            from_status=old_status,
            to_status=DisputeStatus.RESOLVED,
            transitioned_by=user.id,
            reason=f"Resolved: {resolution_type.value}",
        )
        await self.db.flush()

        # Emit event
        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=EVENT_DISPUTE_RESOLVED,
            aggregate_type="dispute",
            aggregate_id=str(dispute_id),
            payload={
                "dispute_id": str(dispute_id),
                "resolution_type": resolution_type.value,
                "resolution_amount": str(resolution_amount) if resolution_amount else None,
            },
        )

        logger.info("Dispute %s resolved with %s", dispute_id, resolution_type.value)
        return dispute

    async def escalate_dispute(
        self,
        dispute_id: uuid.UUID,
        reason: str,
        user: AuthenticatedUser,
    ) -> Dispute:
        """Escalate a dispute to platform operations."""
        dispute = await self.get_dispute(dispute_id)
        old_status = dispute.status

        self._validate_transition(old_status, DisputeStatus.ESCALATED)

        now = datetime.now(UTC)
        dispute.status = DisputeStatus.ESCALATED
        dispute.escalated_at = now
        dispute.escalated_by = user.id

        await self._record_transition(
            dispute_id=dispute.id,
            from_status=old_status,
            to_status=DisputeStatus.ESCALATED,
            transitioned_by=user.id,
            reason=reason,
        )
        await self.db.flush()

        # Emit event
        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=EVENT_DISPUTE_ESCALATED,
            aggregate_type="dispute",
            aggregate_id=str(dispute_id),
            payload={
                "dispute_id": str(dispute_id),
                "escalated_by": str(user.id),
                "reason": reason,
            },
        )

        logger.info("Dispute %s escalated by user %s", dispute_id, user.id)
        return dispute
