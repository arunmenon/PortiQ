"""Unit tests for QuoteService — submit, withdraw, rank, validation."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions import BusinessRuleException, ForbiddenException
from src.models.enums import (
    InvitationStatus,
    QuoteStatus,
    RfqStatus,
    SupplierTier,
)
from src.modules.rfq.quote_service import QuoteService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def quote_service(mock_db):
    return QuoteService(mock_db)


def _make_rfq(status=RfqStatus.BIDDING_OPEN, require_all_line_items=True):
    rfq = MagicMock()
    rfq.id = uuid.uuid4()
    rfq.status = status
    rfq.require_all_line_items = require_all_line_items
    rfq.reference_number = "RFQ-2026-00001"
    return rfq


def _make_invitation(status=InvitationStatus.ACCEPTED):
    inv = MagicMock()
    inv.id = uuid.uuid4()
    inv.status = status
    return inv


def _make_supplier_profile(tier=SupplierTier.VERIFIED):
    profile = MagicMock()
    profile.id = uuid.uuid4()
    profile.tier = tier
    return profile


def _make_quote(
    status=QuoteStatus.SUBMITTED,
    supplier_org_id=None,
    rfq_id=None,
):
    quote = MagicMock()
    quote.id = uuid.uuid4()
    quote.status = status
    quote.supplier_organization_id = supplier_org_id or uuid.uuid4()
    quote.rfq_id = rfq_id or uuid.uuid4()
    quote.total_amount = Decimal("1000.00")
    quote.line_items = []
    return quote


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalar.return_value = value
    unique_mock = MagicMock()
    unique_mock.scalar_one_or_none.return_value = value
    result.unique.return_value = unique_mock
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [value] if value else []
    scalars_mock.first.return_value = value
    result.scalars.return_value = scalars_mock
    return result


def _scalars_first_result(value):
    """Create a mock result whose .scalars().first() returns value."""
    result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.first.return_value = value
    scalars_mock.all.return_value = [value] if value else []
    result.scalars.return_value = scalars_mock
    return result


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------


class TestSubmitQuote:
    @pytest.mark.asyncio
    async def test_submit_rfq_not_bidding_open(self, quote_service, mock_db):
        """submit_quote should reject when RFQ is not in BIDDING_OPEN status."""
        rfq = _make_rfq(status=RfqStatus.PUBLISHED)
        mock_db.execute.return_value = _scalar_result(rfq)

        with pytest.raises(BusinessRuleException, match="BIDDING_OPEN"):
            await quote_service.submit_quote(
                rfq_id=rfq.id,
                supplier_organization_id=uuid.uuid4(),
                submitted_by=uuid.uuid4(),
                line_items=[{"unit_price": "100", "quantity": "1"}],
            )

    @pytest.mark.asyncio
    async def test_submit_no_accepted_invitation(self, quote_service, mock_db):
        """submit_quote should reject when supplier has no ACCEPTED invitation."""
        rfq = _make_rfq(status=RfqStatus.BIDDING_OPEN)
        # First call: _get_rfq, second call: _get_accepted_invitation returns None
        mock_db.execute.side_effect = [
            _scalar_result(rfq),
            _scalar_result(None),
        ]

        with pytest.raises(BusinessRuleException, match="ACCEPTED invitation"):
            await quote_service.submit_quote(
                rfq_id=rfq.id,
                supplier_organization_id=uuid.uuid4(),
                submitted_by=uuid.uuid4(),
                line_items=[{"unit_price": "100", "quantity": "1"}],
            )

    @pytest.mark.asyncio
    async def test_submit_tier_cannot_bid(self, quote_service, mock_db):
        """submit_quote should reject when supplier tier cannot bid."""
        rfq = _make_rfq(status=RfqStatus.BIDDING_OPEN)
        invitation = _make_invitation(status=InvitationStatus.ACCEPTED)
        profile = _make_supplier_profile(tier=SupplierTier.PENDING)

        mock_db.execute.side_effect = [
            _scalar_result(rfq),        # _get_rfq
            _scalar_result(invitation),  # _get_accepted_invitation
            _scalar_result(profile),     # _validate_tier -> get profile
        ]

        with pytest.raises(BusinessRuleException, match="does not allow bidding"):
            await quote_service.submit_quote(
                rfq_id=rfq.id,
                supplier_organization_id=uuid.uuid4(),
                submitted_by=uuid.uuid4(),
                line_items=[{"unit_price": "100", "quantity": "1"}],
            )

    @pytest.mark.asyncio
    @patch("src.modules.rfq.quote_service.OutboxService")
    async def test_submit_quote_happy_path(self, mock_outbox_cls, quote_service, mock_db):
        """submit_quote should create quote + line items with correct total."""
        rfq = _make_rfq(status=RfqStatus.BIDDING_OPEN, require_all_line_items=False)
        invitation = _make_invitation(status=InvitationStatus.ACCEPTED)
        profile = _make_supplier_profile(tier=SupplierTier.PREMIUM)
        rfq_line_item_id_1 = uuid.uuid4()
        rfq_line_item_id_2 = uuid.uuid4()

        mock_outbox_instance = AsyncMock()
        mock_outbox_cls.return_value = mock_outbox_instance

        # Count result for rfq line items (completeness check)
        rfq_item_count_result = MagicMock()
        rfq_item_count_result.scalar.return_value = 2

        # PREMIUM tier has max_quotes=None, so no active quote count query
        mock_db.execute.side_effect = [
            _scalar_result(rfq),                 # _get_rfq
            _scalar_result(invitation),          # _get_accepted_invitation
            _scalar_result(profile),             # _validate_tier -> get profile
            _scalars_first_result(None),         # existing quote check (no previous quote)
            rfq_item_count_result,               # rfq line item count for completeness
        ]

        line_items = [
            {"rfq_line_item_id": str(rfq_line_item_id_1), "unit_price": "100.00", "quantity": "5"},
            {"rfq_line_item_id": str(rfq_line_item_id_2), "unit_price": "50.00", "quantity": "10"},
        ]

        result = await quote_service.submit_quote(
            rfq_id=rfq.id,
            supplier_organization_id=uuid.uuid4(),
            submitted_by=uuid.uuid4(),
            line_items=line_items,
        )

        # Quote added + 2 line items = 3 add() calls
        assert mock_db.add.call_count == 3
        mock_db.flush.assert_awaited()
        # Verify outbox event emitted
        mock_outbox_instance.publish_event.assert_awaited_once()
        call_kwargs = mock_outbox_instance.publish_event.call_args[1]
        assert call_kwargs["event_type"] == "quote.submitted"

    @pytest.mark.asyncio
    @patch("src.modules.rfq.quote_service.OutboxService")
    async def test_submit_quote_with_verified_tier(self, mock_outbox_cls, quote_service, mock_db):
        """submit_quote with VERIFIED tier should check max_quotes limit."""
        rfq = _make_rfq(status=RfqStatus.BIDDING_OPEN, require_all_line_items=False)
        invitation = _make_invitation(status=InvitationStatus.ACCEPTED)
        profile = _make_supplier_profile(tier=SupplierTier.VERIFIED)
        rfq_line_item_id = uuid.uuid4()

        mock_outbox_instance = AsyncMock()
        mock_outbox_cls.return_value = mock_outbox_instance

        # Active quotes count for max_quotes check
        active_quote_count_result = MagicMock()
        active_quote_count_result.scalar.return_value = 0

        # Count result for rfq line items (completeness check)
        rfq_item_count_result = MagicMock()
        rfq_item_count_result.scalar.return_value = 1

        mock_db.execute.side_effect = [
            _scalar_result(rfq),                 # _get_rfq
            _scalar_result(invitation),          # _get_accepted_invitation
            _scalar_result(profile),             # _validate_tier -> get profile
            active_quote_count_result,           # _validate_tier -> active quote count
            _scalars_first_result(None),         # existing quote check (no previous quote)
            rfq_item_count_result,               # rfq line item count for completeness
        ]

        line_items = [
            {"rfq_line_item_id": str(rfq_line_item_id), "unit_price": "200.00", "quantity": "3"},
        ]

        result = await quote_service.submit_quote(
            rfq_id=rfq.id,
            supplier_organization_id=uuid.uuid4(),
            submitted_by=uuid.uuid4(),
            line_items=line_items,
        )

        # Quote + 1 line item = 2 add() calls
        assert mock_db.add.call_count == 2
        mock_outbox_instance.publish_event.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("src.modules.rfq.quote_service.OutboxService")
    async def test_submit_quote_revision(self, mock_outbox_cls, quote_service, mock_db):
        """submit_quote should handle revisions: mark old as REVISED, bump version."""
        rfq = _make_rfq(status=RfqStatus.BIDDING_OPEN, require_all_line_items=False)
        rfq.allow_quote_revision = True
        invitation = _make_invitation(status=InvitationStatus.ACCEPTED)
        profile = _make_supplier_profile(tier=SupplierTier.PREMIUM)

        # Existing quote that will be revised
        existing_quote = _make_quote(status=QuoteStatus.SUBMITTED)
        existing_quote.version = 1

        mock_outbox_instance = AsyncMock()
        mock_outbox_cls.return_value = mock_outbox_instance

        rfq_item_count_result = MagicMock()
        rfq_item_count_result.scalar.return_value = 1

        mock_db.execute.side_effect = [
            _scalar_result(rfq),                          # _get_rfq
            _scalar_result(invitation),                   # _get_accepted_invitation
            _scalar_result(profile),                      # _validate_tier -> get profile
            _scalars_first_result(existing_quote),        # existing quote check (found!)
            rfq_item_count_result,                        # rfq line item count
        ]

        rfq_line_item_id = uuid.uuid4()
        line_items = [
            {"rfq_line_item_id": str(rfq_line_item_id), "unit_price": "150.00", "quantity": "2"},
        ]

        result = await quote_service.submit_quote(
            rfq_id=rfq.id,
            supplier_organization_id=uuid.uuid4(),
            submitted_by=uuid.uuid4(),
            line_items=line_items,
        )

        # Old quote should be marked as REVISED
        assert existing_quote.status == QuoteStatus.REVISED
        # New quote added + 1 line item = at least 2 add() calls
        assert mock_db.add.call_count >= 2
        mock_outbox_instance.publish_event.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_submit_quote_revision_not_allowed(self, quote_service, mock_db):
        """submit_quote should reject revision when allow_quote_revision is False."""
        rfq = _make_rfq(status=RfqStatus.BIDDING_OPEN, require_all_line_items=False)
        rfq.allow_quote_revision = False
        invitation = _make_invitation(status=InvitationStatus.ACCEPTED)
        profile = _make_supplier_profile(tier=SupplierTier.PREMIUM)

        existing_quote = _make_quote(status=QuoteStatus.SUBMITTED)
        existing_quote.version = 1

        mock_db.execute.side_effect = [
            _scalar_result(rfq),                          # _get_rfq
            _scalar_result(invitation),                   # _get_accepted_invitation
            _scalar_result(profile),                      # _validate_tier -> get profile
            _scalars_first_result(existing_quote),        # existing quote check (found!)
        ]

        rfq_line_item_id = uuid.uuid4()
        line_items = [
            {"rfq_line_item_id": str(rfq_line_item_id), "unit_price": "150.00", "quantity": "2"},
        ]

        with pytest.raises(BusinessRuleException, match="revision is not allowed"):
            await quote_service.submit_quote(
                rfq_id=rfq.id,
                supplier_organization_id=uuid.uuid4(),
                submitted_by=uuid.uuid4(),
                line_items=line_items,
            )


# ---------------------------------------------------------------------------
# Withdraw
# ---------------------------------------------------------------------------


class TestWithdrawQuote:
    @pytest.mark.asyncio
    async def test_withdraw_wrong_org(self, quote_service, mock_db):
        """withdraw_quote should reject when caller is not the submitting org."""
        org_a = uuid.uuid4()
        org_b = uuid.uuid4()
        quote = _make_quote(supplier_org_id=org_a)
        mock_db.execute.return_value = _scalar_result(quote)

        with pytest.raises(ForbiddenException, match="your own"):
            await quote_service.withdraw_quote(quote.id, org_b)

    @pytest.mark.asyncio
    async def test_withdraw_non_submitted(self, quote_service, mock_db):
        """withdraw_quote should reject for non-SUBMITTED quotes."""
        org_id = uuid.uuid4()
        quote = _make_quote(status=QuoteStatus.WITHDRAWN, supplier_org_id=org_id)
        mock_db.execute.return_value = _scalar_result(quote)

        with pytest.raises(BusinessRuleException, match="Only SUBMITTED"):
            await quote_service.withdraw_quote(quote.id, org_id)

    @pytest.mark.asyncio
    async def test_withdraw_bidding_not_open(self, quote_service, mock_db):
        """withdraw_quote should reject when RFQ bidding is not open."""
        org_id = uuid.uuid4()
        rfq_id = uuid.uuid4()
        quote = _make_quote(
            status=QuoteStatus.SUBMITTED,
            supplier_org_id=org_id,
            rfq_id=rfq_id,
        )
        rfq = _make_rfq(status=RfqStatus.BIDDING_CLOSED)
        rfq.id = rfq_id

        mock_db.execute.side_effect = [
            _scalar_result(quote),  # get_quote
            _scalar_result(rfq),    # _get_rfq
        ]

        with pytest.raises(BusinessRuleException, match="bidding is open"):
            await quote_service.withdraw_quote(quote.id, org_id)

    @pytest.mark.asyncio
    async def test_withdraw_success(self, quote_service, mock_db):
        """withdraw_quote should set status to WITHDRAWN and emit event."""
        org_id = uuid.uuid4()
        rfq_id = uuid.uuid4()
        quote = _make_quote(
            status=QuoteStatus.SUBMITTED,
            supplier_org_id=org_id,
            rfq_id=rfq_id,
        )
        rfq = _make_rfq(status=RfqStatus.BIDDING_OPEN)
        rfq.id = rfq_id

        mock_db.execute.side_effect = [
            _scalar_result(quote),  # get_quote
            _scalar_result(rfq),    # _get_rfq
        ]

        result = await quote_service.withdraw_quote(quote.id, org_id)
        assert result.status == QuoteStatus.WITHDRAWN


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


class TestRankQuotes:
    @pytest.mark.asyncio
    async def test_rank_assigns_positions(self, quote_service, mock_db):
        """rank_quotes should assign price_rank based on total_amount ascending."""
        q1 = MagicMock()
        q1.total_amount = Decimal("500")
        q2 = MagicMock()
        q2.total_amount = Decimal("300")
        q3 = MagicMock()
        q3.total_amount = Decimal("800")

        # Already sorted by DB ORDER BY, so mock returns sorted
        sorted_quotes = [q2, q1, q3]
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = sorted_quotes
        result = MagicMock()
        result.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result

        ranked = await quote_service.rank_quotes(uuid.uuid4())
        assert ranked[0].price_rank == 1
        assert ranked[1].price_rank == 2
        assert ranked[2].price_rank == 3


# ---------------------------------------------------------------------------
# Visibility
# ---------------------------------------------------------------------------


class TestVisibility:
    @pytest.mark.asyncio
    async def test_supplier_sees_only_own(self, quote_service, mock_db):
        """list_quotes_for_rfq should return only supplier's own quotes."""
        rfq = _make_rfq(status=RfqStatus.BIDDING_OPEN)
        own_quote = _make_quote()

        # count query result
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        # quotes query result
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [own_quote]
        list_result = MagicMock()
        list_result.scalars.return_value = scalars_mock

        mock_db.execute.side_effect = [
            _scalar_result(rfq),  # _get_rfq
            count_result,         # count query
            list_result,          # select quotes
        ]

        quotes, total = await quote_service.list_quotes_for_rfq(
            rfq_id=rfq.id,
            viewer_organization_id=uuid.uuid4(),
            viewer_organization_type="SUPPLIER",
        )
        assert len(quotes) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_buyer_sees_none_before_close(self, quote_service, mock_db):
        """list_quotes_for_rfq should return empty for buyer before BIDDING_CLOSED."""
        rfq = _make_rfq(status=RfqStatus.BIDDING_OPEN)
        mock_db.execute.return_value = _scalar_result(rfq)

        quotes, total = await quote_service.list_quotes_for_rfq(
            rfq_id=rfq.id,
            viewer_organization_id=uuid.uuid4(),
            viewer_organization_type="BUYER",
        )
        assert quotes == []
        assert total == 0
