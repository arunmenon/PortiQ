"""RFQ lifecycle service — CRUD, line items, invitations, state machine."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.exceptions import (
    BusinessRuleException,
    NotFoundException,
)
from src.models.enums import (
    InvitationStatus,
    QuoteStatus,
    RfqStatus,
    RfqTransitionType,
)
from src.models.rfq import Rfq
from src.models.rfq_invitation import RfqInvitation
from src.models.rfq_line_item import RfqLineItem
from src.models.rfq_transition import RfqTransition
from src.modules.events.outbox_service import OutboxService
from src.modules.rfq.constants import VALID_TRANSITIONS

logger = logging.getLogger(__name__)

# Event type constants
EVENT_RFQ_PUBLISHED = "rfq.published"
EVENT_RFQ_BIDDING_OPENED = "rfq.bidding_opened"
EVENT_RFQ_BIDDING_CLOSED = "rfq.bidding_closed"
EVENT_RFQ_AWARDED = "rfq.awarded"
EVENT_RFQ_CANCELLED = "rfq.cancelled"
EVENT_RFQ_COMPLETED = "rfq.completed"
EVENT_RFQ_EVALUATION = "rfq.evaluation_started"

_TRANSITION_EVENT_MAP: dict[RfqTransitionType, str] = {
    RfqTransitionType.PUBLISH: EVENT_RFQ_PUBLISHED,
    RfqTransitionType.OPEN_BIDDING: EVENT_RFQ_BIDDING_OPENED,
    RfqTransitionType.CLOSE_BIDDING: EVENT_RFQ_BIDDING_CLOSED,
    RfqTransitionType.START_EVALUATION: EVENT_RFQ_EVALUATION,
    RfqTransitionType.AWARD: EVENT_RFQ_AWARDED,
    RfqTransitionType.COMPLETE: EVENT_RFQ_COMPLETED,
    RfqTransitionType.CANCEL: EVENT_RFQ_CANCELLED,
}


class RfqService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Reference number generation
    # ------------------------------------------------------------------

    async def _generate_reference_number(self) -> str:
        """Generate RFQ-YYYY-NNNNN reference using a DB sequence."""
        result = await self.db.execute(text("SELECT nextval('rfq_reference_seq')"))
        seq_val = result.scalar()
        year = datetime.now(UTC).year
        return f"RFQ-{year}-{seq_val:05d}"

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_rfq(
        self,
        buyer_organization_id: uuid.UUID,
        created_by: uuid.UUID,
        title: str,
        description: str | None = None,
        vessel_id: uuid.UUID | None = None,
        delivery_port: str | None = None,
        delivery_date: datetime | None = None,
        bidding_deadline: datetime | None = None,
        require_all_line_items: bool = False,
        allow_partial_quotes: bool = False,
        allow_quote_revision: bool = True,
        auction_type: str = "SEALED_BID",
        currency: str = "USD",
        notes: str | None = None,
    ) -> Rfq:
        """Create a new RFQ in DRAFT status."""
        reference_number = await self._generate_reference_number()

        rfq = Rfq(
            reference_number=reference_number,
            buyer_organization_id=buyer_organization_id,
            created_by=created_by,
            title=title,
            description=description,
            vessel_id=vessel_id,
            delivery_port=delivery_port,
            delivery_date=delivery_date,
            bidding_deadline=bidding_deadline,
            require_all_line_items=require_all_line_items,
            allow_partial_quotes=allow_partial_quotes,
            allow_quote_revision=allow_quote_revision,
            auction_type=auction_type,
            currency=currency,
            notes=notes,
            status=RfqStatus.DRAFT,
        )
        self.db.add(rfq)
        await self.db.flush()
        logger.info("Created RFQ %s (%s)", rfq.id, reference_number)
        return rfq

    async def get_rfq(self, rfq_id: uuid.UUID) -> Rfq:
        """Get an RFQ by ID. Raises NotFoundException if not found."""
        result = await self.db.execute(
            select(Rfq)
            .options(
                joinedload(Rfq.line_items),
                joinedload(Rfq.invitations),
            )
            .where(Rfq.id == rfq_id)
        )
        rfq = result.unique().scalar_one_or_none()
        if rfq is None:
            raise NotFoundException(f"RFQ {rfq_id} not found")
        return rfq

    async def list_rfqs(
        self,
        organization_id: uuid.UUID,
        organization_type: str,
        status: RfqStatus | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Rfq], int]:
        """List RFQs visible to the caller's organization.

        Buyers see RFQs they created. Suppliers see RFQs they are invited to.
        Platform admins should pass organization_type='PLATFORM' to see all.
        """
        query = select(Rfq)
        count_query = select(func.count()).select_from(Rfq)

        if organization_type == "SUPPLIER":
            # Supplier sees RFQs where they have an invitation
            invited_rfq_ids = (
                select(RfqInvitation.rfq_id)
                .where(RfqInvitation.supplier_organization_id == organization_id)
                .scalar_subquery()
            )
            query = query.where(Rfq.id.in_(invited_rfq_ids))
            count_query = count_query.where(Rfq.id.in_(invited_rfq_ids))
        elif organization_type != "PLATFORM":
            # Buyer sees own RFQs
            query = query.where(Rfq.buyer_organization_id == organization_id)
            count_query = count_query.where(Rfq.buyer_organization_id == organization_id)

        if status is not None:
            query = query.where(Rfq.status == status)
            count_query = count_query.where(Rfq.status == status)

        if search:
            pattern = f"%{search}%"
            search_filter = Rfq.title.ilike(pattern)
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Rfq.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def update_rfq(self, rfq_id: uuid.UUID, **kwargs) -> Rfq:
        """Update an RFQ. Only allowed in DRAFT status."""
        rfq = await self.get_rfq(rfq_id)
        if rfq.status != RfqStatus.DRAFT:
            raise BusinessRuleException(
                f"Cannot update RFQ in status '{rfq.status.value}'. "
                "Only DRAFT RFQs can be edited."
            )
        for key, value in kwargs.items():
            if hasattr(rfq, key):
                setattr(rfq, key, value)
        await self.db.flush()
        return rfq

    async def delete_rfq(self, rfq_id: uuid.UUID) -> None:
        """Hard-delete a DRAFT RFQ."""
        rfq = await self.get_rfq(rfq_id)
        if rfq.status != RfqStatus.DRAFT:
            raise BusinessRuleException(
                f"Cannot delete RFQ in status '{rfq.status.value}'. "
                "Only DRAFT RFQs can be deleted."
            )
        await self.db.delete(rfq)
        await self.db.flush()
        logger.info("Deleted DRAFT RFQ %s", rfq_id)

    # ------------------------------------------------------------------
    # Line Items
    # ------------------------------------------------------------------

    async def add_line_item(
        self,
        rfq_id: uuid.UUID,
        line_number: int,
        description: str,
        quantity: float,
        unit_of_measure: str,
        product_id: uuid.UUID | None = None,
        impa_code: str | None = None,
        specifications: dict | None = None,
        notes: str | None = None,
    ) -> RfqLineItem:
        """Add a line item to a DRAFT RFQ."""
        rfq = await self.get_rfq(rfq_id)
        if rfq.status != RfqStatus.DRAFT:
            raise BusinessRuleException("Line items can only be added to DRAFT RFQs")

        item = RfqLineItem(
            rfq_id=rfq_id,
            line_number=line_number,
            product_id=product_id,
            impa_code=impa_code,
            description=description,
            quantity=quantity,
            unit_of_measure=unit_of_measure,
            specifications=specifications,
            notes=notes,
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def update_line_item(
        self, rfq_id: uuid.UUID, item_id: uuid.UUID, **kwargs
    ) -> RfqLineItem:
        """Update a line item on a DRAFT RFQ."""
        rfq = await self.get_rfq(rfq_id)
        if rfq.status != RfqStatus.DRAFT:
            raise BusinessRuleException("Line items can only be updated on DRAFT RFQs")

        result = await self.db.execute(
            select(RfqLineItem).where(
                RfqLineItem.id == item_id, RfqLineItem.rfq_id == rfq_id
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise NotFoundException(f"Line item {item_id} not found on RFQ {rfq_id}")

        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)
        await self.db.flush()
        return item

    async def delete_line_item(self, rfq_id: uuid.UUID, item_id: uuid.UUID) -> None:
        """Remove a line item from a DRAFT RFQ."""
        rfq = await self.get_rfq(rfq_id)
        if rfq.status != RfqStatus.DRAFT:
            raise BusinessRuleException("Line items can only be removed from DRAFT RFQs")

        result = await self.db.execute(
            select(RfqLineItem).where(
                RfqLineItem.id == item_id, RfqLineItem.rfq_id == rfq_id
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise NotFoundException(f"Line item {item_id} not found on RFQ {rfq_id}")

        await self.db.delete(item)
        await self.db.flush()

    async def get_line_items(self, rfq_id: uuid.UUID) -> list[RfqLineItem]:
        """Get all line items for an RFQ."""
        result = await self.db.execute(
            select(RfqLineItem)
            .where(RfqLineItem.rfq_id == rfq_id)
            .order_by(RfqLineItem.line_number)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Invitations
    # ------------------------------------------------------------------

    async def invite_suppliers(
        self,
        rfq_id: uuid.UUID,
        supplier_organization_ids: list[uuid.UUID],
        invited_by: uuid.UUID,
    ) -> list[RfqInvitation]:
        """Batch-invite suppliers to an RFQ. Idempotent — skips duplicates."""
        rfq = await self.get_rfq(rfq_id)
        if rfq.status not in {RfqStatus.DRAFT, RfqStatus.PUBLISHED}:
            raise BusinessRuleException(
                "Suppliers can only be invited to DRAFT or PUBLISHED RFQs"
            )

        # Find existing invitations to skip
        existing_result = await self.db.execute(
            select(RfqInvitation.supplier_organization_id).where(
                RfqInvitation.rfq_id == rfq_id
            )
        )
        existing_org_ids = set(existing_result.scalars().all())

        now = datetime.now(UTC)
        invitations = []
        for org_id in supplier_organization_ids:
            if org_id in existing_org_ids:
                continue
            invitation = RfqInvitation(
                rfq_id=rfq_id,
                supplier_organization_id=org_id,
                invited_by=invited_by,
                invited_at=now,
                status=InvitationStatus.PENDING,
            )
            self.db.add(invitation)
            invitations.append(invitation)

        await self.db.flush()
        logger.info("Invited %d suppliers to RFQ %s", len(invitations), rfq_id)
        return invitations

    async def list_invitations(self, rfq_id: uuid.UUID) -> list[RfqInvitation]:
        """List all invitations for an RFQ."""
        result = await self.db.execute(
            select(RfqInvitation)
            .where(RfqInvitation.rfq_id == rfq_id)
            .order_by(RfqInvitation.created_at.desc())
        )
        return list(result.scalars().all())

    async def remove_invitation(
        self, rfq_id: uuid.UUID, invitation_id: uuid.UUID
    ) -> None:
        """Remove a PENDING invitation from a DRAFT RFQ."""
        rfq = await self.get_rfq(rfq_id)
        if rfq.status != RfqStatus.DRAFT:
            raise BusinessRuleException(
                "Invitations can only be removed from DRAFT RFQs"
            )

        result = await self.db.execute(
            select(RfqInvitation).where(
                RfqInvitation.id == invitation_id,
                RfqInvitation.rfq_id == rfq_id,
            )
        )
        invitation = result.scalar_one_or_none()
        if invitation is None:
            raise NotFoundException(
                f"Invitation {invitation_id} not found on RFQ {rfq_id}"
            )
        if invitation.status != InvitationStatus.PENDING:
            raise BusinessRuleException(
                f"Cannot remove invitation in status '{invitation.status.value}'"
            )

        await self.db.delete(invitation)
        await self.db.flush()

    async def respond_to_invitation(
        self,
        rfq_id: uuid.UUID,
        supplier_organization_id: uuid.UUID,
        accept: bool,
    ) -> RfqInvitation:
        """Accept or decline an invitation."""
        result = await self.db.execute(
            select(RfqInvitation).where(
                RfqInvitation.rfq_id == rfq_id,
                RfqInvitation.supplier_organization_id == supplier_organization_id,
            )
        )
        invitation = result.scalar_one_or_none()
        if invitation is None:
            raise NotFoundException(
                f"No invitation found for organization {supplier_organization_id} on RFQ {rfq_id}"
            )
        if invitation.status != InvitationStatus.PENDING:
            raise BusinessRuleException(
                f"Cannot respond to invitation in status '{invitation.status.value}'"
            )

        invitation.status = InvitationStatus.ACCEPTED if accept else InvitationStatus.DECLINED
        invitation.responded_at = datetime.now(UTC)
        await self.db.flush()
        return invitation

    # ------------------------------------------------------------------
    # State Machine
    # ------------------------------------------------------------------

    async def transition(
        self,
        rfq_id: uuid.UUID,
        transition_type: RfqTransitionType,
        triggered_by: uuid.UUID,
        trigger_source: str = "USER",
        reason: str | None = None,
        metadata: dict | None = None,
    ) -> Rfq:
        """Execute a state machine transition on an RFQ.

        Validates via VALID_TRANSITIONS, runs guard conditions, records the
        transition, and emits an event via OutboxService.
        """
        rfq = await self.get_rfq(rfq_id)
        current_status = rfq.status

        # Validate transition is allowed
        allowed_transitions = VALID_TRANSITIONS.get(current_status, {})
        if transition_type not in allowed_transitions:
            raise BusinessRuleException(
                f"Cannot perform '{transition_type.value}' from status '{current_status.value}'. "
                f"Allowed transitions: {[t.value for t in allowed_transitions.keys()]}"
            )

        new_status = allowed_transitions[transition_type]

        # Run guard conditions
        await self._run_guards(rfq, transition_type, metadata)

        # Record transition
        old_status = current_status
        rfq.status = new_status

        # Populate cancellation fields when cancelling
        if transition_type == RfqTransitionType.CANCEL:
            rfq.cancelled_at = datetime.now(UTC)
            rfq.cancellation_reason = reason

        transition_record = RfqTransition(
            rfq_id=rfq_id,
            from_status=old_status,
            to_status=new_status,
            transition_type=transition_type,
            triggered_by=triggered_by,
            trigger_source=trigger_source,
            reason=reason,
            metadata_extra=metadata or {},
        )
        self.db.add(transition_record)
        await self.db.flush()

        # Emit event
        event_type = _TRANSITION_EVENT_MAP.get(transition_type)
        if event_type:
            outbox = OutboxService(self.db)
            await outbox.publish_event(
                event_type=event_type,
                aggregate_type="rfq",
                aggregate_id=str(rfq_id),
                payload={
                    "rfq_id": str(rfq_id),
                    "reference_number": rfq.reference_number,
                    "from_status": old_status.value,
                    "to_status": new_status.value,
                    "triggered_by": str(triggered_by),
                    "reason": reason,
                    "metadata": metadata,
                },
            )

        logger.info(
            "RFQ %s transitioned %s -> %s via %s",
            rfq_id, old_status.value, new_status.value, transition_type.value,
        )
        return rfq

    async def _run_guards(
        self,
        rfq: Rfq,
        transition_type: RfqTransitionType,
        metadata: dict | None,
    ) -> None:
        """Run guard conditions for the given transition."""
        if transition_type == RfqTransitionType.PUBLISH:
            await self._guard_publish(rfq)
        elif transition_type == RfqTransitionType.AWARD:
            await self._guard_award(rfq, metadata)
        elif transition_type == RfqTransitionType.CANCEL:
            self._guard_cancel(rfq, metadata)

    async def _guard_publish(self, rfq: Rfq) -> None:
        """PUBLISH requires >= 1 line item, deadline in future, >= 1 invitation."""
        # Check line items
        item_count_result = await self.db.execute(
            select(func.count()).select_from(RfqLineItem).where(RfqLineItem.rfq_id == rfq.id)
        )
        item_count = item_count_result.scalar() or 0
        if item_count == 0:
            raise BusinessRuleException("Cannot publish RFQ without at least one line item")

        # Check bidding deadline
        if rfq.bidding_deadline is None:
            raise BusinessRuleException("Cannot publish RFQ without a bidding deadline")
        if rfq.bidding_deadline <= datetime.now(UTC):
            raise BusinessRuleException("Bidding deadline must be in the future")

        # Check invitations
        invitation_count_result = await self.db.execute(
            select(func.count()).select_from(RfqInvitation).where(
                RfqInvitation.rfq_id == rfq.id
            )
        )
        invitation_count = invitation_count_result.scalar() or 0
        if invitation_count == 0:
            raise BusinessRuleException(
                "Cannot publish RFQ without at least one supplier invitation"
            )

    async def _guard_award(self, rfq: Rfq, metadata: dict | None) -> None:
        """AWARD requires quote_id in metadata, and quote must be SUBMITTED."""
        if not metadata or "quote_id" not in metadata:
            raise BusinessRuleException("AWARD transition requires 'quote_id' in metadata")

        from src.models.quote import Quote

        quote_id = uuid.UUID(metadata["quote_id"])
        result = await self.db.execute(
            select(Quote).where(Quote.id == quote_id, Quote.rfq_id == rfq.id)
        )
        quote = result.scalar_one_or_none()
        if quote is None:
            raise NotFoundException(f"Quote {quote_id} not found on RFQ {rfq.id}")
        if quote.status != QuoteStatus.SUBMITTED:
            raise BusinessRuleException(
                f"Cannot award a quote in status '{quote.status.value}'. "
                "Only SUBMITTED quotes can be awarded."
            )

        # Mark the winning quote as AWARDED and update RFQ fields
        quote.status = QuoteStatus.AWARDED
        rfq.awarded_quote_id = quote.id
        rfq.awarded_supplier_id = quote.supplier_organization_id
        rfq.awarded_at = datetime.now(UTC)
        await self.db.flush()

    @staticmethod
    def _guard_cancel(rfq: Rfq, metadata: dict | None) -> None:
        """CANCEL from AWARDED requires a reason."""
        if rfq.status == RfqStatus.AWARDED:
            reason = (metadata or {}).get("reason")
            if not reason:
                raise BusinessRuleException(
                    "Cancelling an AWARDED RFQ requires a reason in metadata"
                )

    # ------------------------------------------------------------------
    # Audit trail
    # ------------------------------------------------------------------

    async def get_transitions(self, rfq_id: uuid.UUID) -> list[RfqTransition]:
        """Get the full transition history for an RFQ."""
        result = await self.db.execute(
            select(RfqTransition)
            .where(RfqTransition.rfq_id == rfq_id)
            .order_by(RfqTransition.created_at.asc())
        )
        return list(result.scalars().all())
