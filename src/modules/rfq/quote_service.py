"""Quote lifecycle service — submit, withdraw, rank, visibility rules."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.exceptions import (
    BusinessRuleException,
    ForbiddenException,
    NotFoundException,
)
from src.models.enums import (
    InvitationStatus,
    QuoteStatus,
    RfqStatus,
)
from src.models.quote import Quote
from src.models.quote_line_item import QuoteLineItem
from src.models.rfq import Rfq
from src.models.rfq_invitation import RfqInvitation
from src.models.rfq_line_item import RfqLineItem
from src.models.supplier_profile import SupplierProfile
from src.modules.events.outbox_service import OutboxService
from src.modules.supplier.constants import TIER_CAPABILITIES

logger = logging.getLogger(__name__)


class QuoteService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Submit
    # ------------------------------------------------------------------

    async def submit_quote(
        self,
        rfq_id: uuid.UUID,
        supplier_organization_id: uuid.UUID,
        submitted_by: uuid.UUID,
        line_items: list[dict],
        currency: str = "USD",
        valid_until: datetime | None = None,
        delivery_port: str | None = None,
        estimated_delivery_days: int | None = None,
        payment_terms: str | None = None,
        shipping_terms: str | None = None,
        warranty_terms: str | None = None,
        notes: str | None = None,
    ) -> Quote:
        """Submit a quote for an RFQ.

        Validates:
        - RFQ is in BIDDING_OPEN status
        - Supplier has an ACCEPTED invitation
        - Supplier tier permits bidding (can_bid_rfq)
        - Supplier has not exceeded max_quotes
        """
        # Load RFQ
        rfq = await self._get_rfq(rfq_id)
        if rfq.status != RfqStatus.BIDDING_OPEN:
            raise BusinessRuleException(
                f"Cannot submit quote for RFQ in status '{rfq.status.value}'. "
                "RFQ must be in BIDDING_OPEN status."
            )

        # Validate invitation
        invitation = await self._get_accepted_invitation(rfq_id, supplier_organization_id)
        if invitation is None:
            raise BusinessRuleException(
                "Supplier must have an ACCEPTED invitation to submit a quote"
            )

        # Validate tier capabilities
        await self._validate_tier(supplier_organization_id, rfq_id)

        # Check for existing quote by this supplier on this RFQ
        existing_quote_result = await self.db.execute(
            select(Quote)
            .where(
                Quote.rfq_id == rfq_id,
                Quote.supplier_organization_id == supplier_organization_id,
                Quote.status.in_([QuoteStatus.SUBMITTED, QuoteStatus.DRAFT]),
            )
            .order_by(Quote.version.desc())
        )
        existing_quote = existing_quote_result.scalars().first()

        new_version = 1
        if existing_quote is not None:
            if not rfq.allow_quote_revision:
                raise BusinessRuleException(
                    "Quote revision is not allowed for this RFQ"
                )
            # Mark old quote as REVISED and bump version
            existing_quote.status = QuoteStatus.REVISED
            new_version = existing_quote.version + 1
            await self.db.flush()

        # Calculate total amount from line items
        total_amount = Decimal("0")
        for item in line_items:
            unit_price = Decimal(str(item.get("unit_price", 0)))
            quantity = Decimal(str(item.get("quantity", 1)))
            total_amount += unit_price * quantity

        # Check completeness (all RFQ line items quoted?)
        rfq_item_count_result = await self.db.execute(
            select(func.count()).select_from(RfqLineItem).where(RfqLineItem.rfq_id == rfq_id)
        )
        rfq_item_count = rfq_item_count_result.scalar() or 0
        is_complete = len(line_items) >= rfq_item_count if rfq.require_all_line_items else True

        # Create quote
        quote = Quote(
            rfq_id=rfq_id,
            supplier_organization_id=supplier_organization_id,
            submitted_by=submitted_by,
            status=QuoteStatus.SUBMITTED,
            version=new_version,
            total_amount=total_amount,
            currency=currency,
            valid_until=valid_until,
            delivery_port=delivery_port,
            estimated_delivery_days=estimated_delivery_days,
            payment_terms=payment_terms,
            shipping_terms=shipping_terms,
            warranty_terms=warranty_terms,
            notes=notes,
            is_complete=is_complete,
            submitted_at=datetime.now(UTC),
        )
        self.db.add(quote)
        await self.db.flush()

        # Create quote line items
        for item_data in line_items:
            unit_price = Decimal(str(item_data.get("unit_price", 0)))
            quantity = Decimal(str(item_data.get("quantity", 1)))
            quote_item = QuoteLineItem(
                quote_id=quote.id,
                rfq_line_item_id=item_data["rfq_line_item_id"],
                unit_price=unit_price,
                quantity=quantity,
                total_price=unit_price * quantity,
                lead_time_days=item_data.get("lead_time_days"),
                notes=item_data.get("notes"),
            )
            self.db.add(quote_item)

        await self.db.flush()

        # Emit event
        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type="quote.submitted",
            aggregate_type="quote",
            aggregate_id=str(quote.id),
            payload={
                "quote_id": str(quote.id),
                "rfq_id": str(rfq_id),
                "supplier_organization_id": str(supplier_organization_id),
                "total_amount": str(total_amount),
                "is_complete": is_complete,
            },
        )

        logger.info(
            "Quote %s submitted for RFQ %s by org %s (total: %s)",
            quote.id, rfq_id, supplier_organization_id, total_amount,
        )
        return quote

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_quote(self, quote_id: uuid.UUID) -> Quote:
        """Get a quote by ID."""
        result = await self.db.execute(
            select(Quote)
            .options(joinedload(Quote.line_items))
            .where(Quote.id == quote_id)
        )
        quote = result.unique().scalar_one_or_none()
        if quote is None:
            raise NotFoundException(f"Quote {quote_id} not found")
        return quote

    async def get_quote_detail(
        self,
        rfq_id: uuid.UUID,
        quote_id: uuid.UUID,
        requesting_org_id: uuid.UUID | None = None,
        requesting_org_type: str | None = None,
    ) -> Quote:
        """Get full quote detail including line items for a specific RFQ.

        Enforces sealed-bid visibility:
        - SUPPLIER: can only see their own quotes
        - BUYER: can only see quotes after BIDDING_CLOSED
        - PLATFORM: can see all quotes
        """
        result = await self.db.execute(
            select(Quote)
            .options(joinedload(Quote.line_items))
            .where(Quote.id == quote_id, Quote.rfq_id == rfq_id)
        )
        quote = result.unique().scalar_one_or_none()
        if quote is None:
            raise NotFoundException(
                f"Quote {quote_id} not found on RFQ {rfq_id}"
            )

        # Enforce sealed-bid visibility when org info is provided
        if requesting_org_id is not None and requesting_org_type is not None:
            if requesting_org_type == "SUPPLIER":
                if quote.supplier_organization_id != requesting_org_id:
                    raise ForbiddenException(
                        "Suppliers can only view their own quotes"
                    )
            elif requesting_org_type != "PLATFORM":
                # Buyer: sealed-bid — only visible after BIDDING_CLOSED
                rfq = await self._get_rfq(rfq_id)
                sealed_bid_visible_statuses = {
                    RfqStatus.BIDDING_CLOSED,
                    RfqStatus.EVALUATION,
                    RfqStatus.AWARDED,
                    RfqStatus.COMPLETED,
                }
                if rfq.status not in sealed_bid_visible_statuses:
                    raise ForbiddenException(
                        "Quotes are not visible until bidding closes (sealed bid)"
                    )

        return quote

    async def list_quotes_for_rfq(
        self,
        rfq_id: uuid.UUID,
        viewer_organization_id: uuid.UUID,
        viewer_organization_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Quote], int]:
        """List quotes for an RFQ with visibility rules.

        Buyers see all quotes only after BIDDING_CLOSED (sealed-bid).
        Suppliers see only their own quotes at any time.
        Platform admins see all.

        Returns (items, total_count).
        """
        rfq = await self._get_rfq(rfq_id)
        query = select(Quote).where(Quote.rfq_id == rfq_id)
        count_query = select(func.count()).select_from(Quote).where(Quote.rfq_id == rfq_id)

        if viewer_organization_type == "SUPPLIER":
            # Supplier always sees only their own quotes
            query = query.where(Quote.supplier_organization_id == viewer_organization_id)
            count_query = count_query.where(
                Quote.supplier_organization_id == viewer_organization_id
            )
        elif viewer_organization_type != "PLATFORM":
            # Buyer: can only see quotes after bidding closes (sealed bid)
            sealed_bid_visible_statuses = {
                RfqStatus.BIDDING_CLOSED,
                RfqStatus.EVALUATION,
                RfqStatus.AWARDED,
                RfqStatus.COMPLETED,
            }
            if rfq.status not in sealed_bid_visible_statuses:
                # Before bidding closes, buyer sees no individual quotes
                return [], 0

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Quote.total_amount.asc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    # ------------------------------------------------------------------
    # Withdraw
    # ------------------------------------------------------------------

    async def withdraw_quote(
        self,
        quote_id: uuid.UUID,
        supplier_organization_id: uuid.UUID,
    ) -> Quote:
        """Withdraw a submitted quote. Only the submitting org can withdraw."""
        quote = await self.get_quote(quote_id)

        if quote.supplier_organization_id != supplier_organization_id:
            raise ForbiddenException("You can only withdraw your own quotes")

        if quote.status != QuoteStatus.SUBMITTED:
            raise BusinessRuleException(
                f"Cannot withdraw quote in status '{quote.status.value}'. "
                "Only SUBMITTED quotes can be withdrawn."
            )

        # Check RFQ is still open for bidding
        rfq = await self._get_rfq(quote.rfq_id)
        if rfq.status != RfqStatus.BIDDING_OPEN:
            raise BusinessRuleException(
                "Quotes can only be withdrawn while bidding is open"
            )

        quote.status = QuoteStatus.WITHDRAWN
        quote.withdrawn_at = datetime.now(UTC)
        await self.db.flush()

        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type="quote.withdrawn",
            aggregate_type="quote",
            aggregate_id=str(quote_id),
            payload={
                "quote_id": str(quote_id),
                "rfq_id": str(quote.rfq_id),
                "supplier_organization_id": str(supplier_organization_id),
            },
        )

        logger.info("Quote %s withdrawn by org %s", quote_id, supplier_organization_id)
        return quote

    # ------------------------------------------------------------------
    # Ranking
    # ------------------------------------------------------------------

    async def rank_quotes(self, rfq_id: uuid.UUID) -> list[Quote]:
        """Rank SUBMITTED quotes by total_amount ascending. Updates price_rank."""
        result = await self.db.execute(
            select(Quote)
            .where(
                Quote.rfq_id == rfq_id,
                Quote.status == QuoteStatus.SUBMITTED,
            )
            .order_by(Quote.total_amount.asc())
        )
        quotes = list(result.scalars().all())

        for rank, quote in enumerate(quotes, start=1):
            quote.price_rank = rank

        await self.db.flush()
        logger.info("Ranked %d quotes for RFQ %s", len(quotes), rfq_id)
        return quotes

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_rfq(self, rfq_id: uuid.UUID) -> Rfq:
        """Load an RFQ without eager-loading relationships."""
        result = await self.db.execute(select(Rfq).where(Rfq.id == rfq_id))
        rfq = result.scalar_one_or_none()
        if rfq is None:
            raise NotFoundException(f"RFQ {rfq_id} not found")
        return rfq

    async def _get_accepted_invitation(
        self, rfq_id: uuid.UUID, supplier_organization_id: uuid.UUID
    ) -> RfqInvitation | None:
        """Return the ACCEPTED invitation for a supplier on an RFQ, or None."""
        result = await self.db.execute(
            select(RfqInvitation).where(
                RfqInvitation.rfq_id == rfq_id,
                RfqInvitation.supplier_organization_id == supplier_organization_id,
                RfqInvitation.status == InvitationStatus.ACCEPTED,
            )
        )
        return result.scalar_one_or_none()

    async def _validate_tier(
        self, supplier_organization_id: uuid.UUID, rfq_id: uuid.UUID
    ) -> None:
        """Validate the supplier's tier allows bidding and max_quotes not exceeded.

        Note: max_quotes is intentionally a global (platform-wide) limit across
        all RFQs, not a per-RFQ limit. It represents the tier-level cap on
        total active quotes a supplier can have at any point in time.
        """
        # Get supplier profile
        result = await self.db.execute(
            select(SupplierProfile).where(
                SupplierProfile.organization_id == supplier_organization_id
            )
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            raise BusinessRuleException(
                "Supplier profile not found. Complete onboarding to bid on RFQs."
            )

        capabilities = TIER_CAPABILITIES.get(profile.tier, {})
        if not capabilities.get("can_bid_rfq", False):
            raise BusinessRuleException(
                f"Supplier tier '{profile.tier.value}' does not allow bidding on RFQs. "
                "Please upgrade your tier."
            )

        # Check max_quotes
        max_quotes = capabilities.get("max_quotes")
        if max_quotes is not None:
            active_quote_count_result = await self.db.execute(
                select(func.count())
                .select_from(Quote)
                .where(
                    Quote.supplier_organization_id == supplier_organization_id,
                    Quote.status.in_([QuoteStatus.SUBMITTED, QuoteStatus.REVISED]),
                )
            )
            active_quote_count = active_quote_count_result.scalar() or 0
            if active_quote_count >= max_quotes:
                raise BusinessRuleException(
                    f"Supplier tier '{profile.tier.value}' allows a maximum of "
                    f"{max_quotes} active quotes. You currently have {active_quote_count}."
                )
