"""Unit tests for RfqService — CRUD, line items, invitations, state machine."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions import BusinessRuleException, NotFoundException
from src.models.enums import (
    InvitationStatus,
    QuoteStatus,
    RfqStatus,
    RfqTransitionType,
)
from src.modules.rfq.rfq_service import RfqService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    """Create a mock AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def rfq_service(mock_db):
    return RfqService(mock_db)


def _make_rfq(
    rfq_id=None,
    status=RfqStatus.DRAFT,
    buyer_org_id=None,
    bidding_deadline=None,
    require_all_line_items=True,
    allow_quote_revision=True,
):
    """Create a mock RFQ object."""
    rfq = MagicMock()
    rfq.id = rfq_id or uuid.uuid4()
    rfq.status = status
    rfq.buyer_organization_id = buyer_org_id or uuid.uuid4()
    rfq.reference_number = "RFQ-2026-00001"
    rfq.title = "Test RFQ"
    rfq.bidding_deadline = bidding_deadline
    rfq.bidding_start = None
    rfq.require_all_line_items = require_all_line_items
    rfq.allow_quote_revision = allow_quote_revision
    rfq.line_items = []
    rfq.invitations = []
    rfq.created_at = datetime.now(UTC)
    rfq.cancelled_at = None
    rfq.cancellation_reason = None
    rfq.awarded_quote_id = None
    rfq.awarded_supplier_id = None
    rfq.awarded_at = None
    return rfq


def _make_count_result(count_value):
    """Create a mock result for SELECT COUNT queries."""
    result = MagicMock()
    result.scalar.return_value = count_value
    return result


def _make_scalar_result(value):
    """Create a mock result that returns a scalar value."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalar.return_value = value
    unique_mock = MagicMock()
    unique_mock.scalar_one_or_none.return_value = value
    result.unique.return_value = unique_mock
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [value] if value else []
    result.scalars.return_value = scalars_mock
    return result


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


class TestCreateRfq:
    @pytest.mark.asyncio
    async def test_create_rfq_generates_reference_number(self, rfq_service, mock_db):
        """create_rfq should generate a reference number via SQL sequence."""
        seq_result = MagicMock()
        seq_result.scalar.return_value = 42
        mock_db.execute.return_value = seq_result

        await rfq_service.create_rfq(
            buyer_organization_id=uuid.uuid4(),
            created_by=uuid.uuid4(),
            title="Deck Supplies",
        )

        # Verify the RFQ was added to session
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited()


# ---------------------------------------------------------------------------
# Get / List
# ---------------------------------------------------------------------------


class TestGetRfq:
    @pytest.mark.asyncio
    async def test_get_rfq_not_found(self, rfq_service, mock_db):
        """get_rfq should raise NotFoundException when RFQ doesn't exist."""
        mock_db.execute.return_value = _make_scalar_result(None)

        with pytest.raises(NotFoundException, match="not found"):
            await rfq_service.get_rfq(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_get_rfq_found(self, rfq_service, mock_db):
        """get_rfq should return the RFQ when found."""
        rfq = _make_rfq()
        mock_db.execute.return_value = _make_scalar_result(rfq)

        result = await rfq_service.get_rfq(rfq.id)
        assert result == rfq

    @pytest.mark.asyncio
    async def test_list_rfqs_buyer_view(self, rfq_service, mock_db):
        """list_rfqs should filter by buyer_organization_id for BUYER callers."""
        buyer_org_id = uuid.uuid4()
        rfq1 = _make_rfq(buyer_org_id=buyer_org_id)
        rfq2 = _make_rfq(buyer_org_id=buyer_org_id)

        # First execute: count query, second execute: select query
        count_result = _make_count_result(2)
        list_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [rfq1, rfq2]
        list_result.scalars.return_value = scalars_mock

        mock_db.execute.side_effect = [count_result, list_result]

        items, total = await rfq_service.list_rfqs(
            organization_id=buyer_org_id,
            organization_type="BUYER",
        )
        assert total == 2
        assert len(items) == 2
        # Verify execute was called (contains the buyer filter)
        assert mock_db.execute.call_count == 2


# ---------------------------------------------------------------------------
# Update / Delete
# ---------------------------------------------------------------------------


class TestUpdateRfq:
    @pytest.mark.asyncio
    async def test_update_rfq_non_draft_raises(self, rfq_service, mock_db):
        """update_rfq should raise BusinessRuleException for non-DRAFT RFQs."""
        rfq = _make_rfq(status=RfqStatus.PUBLISHED)
        mock_db.execute.return_value = _make_scalar_result(rfq)

        with pytest.raises(BusinessRuleException, match="Only DRAFT"):
            await rfq_service.update_rfq(rfq.id, title="New Title")

    @pytest.mark.asyncio
    async def test_update_rfq_draft_succeeds(self, rfq_service, mock_db):
        """update_rfq should update fields on a DRAFT RFQ."""
        rfq = _make_rfq(status=RfqStatus.DRAFT)
        mock_db.execute.return_value = _make_scalar_result(rfq)

        result = await rfq_service.update_rfq(rfq.id, title="Updated")
        assert result.title == "Updated"


class TestDeleteRfq:
    @pytest.mark.asyncio
    async def test_delete_non_draft_raises(self, rfq_service, mock_db):
        """delete_rfq should raise for non-DRAFT RFQs."""
        rfq = _make_rfq(status=RfqStatus.BIDDING_OPEN)
        mock_db.execute.return_value = _make_scalar_result(rfq)

        with pytest.raises(BusinessRuleException, match="Only DRAFT"):
            await rfq_service.delete_rfq(rfq.id)

    @pytest.mark.asyncio
    async def test_delete_draft_succeeds(self, rfq_service, mock_db):
        """delete_rfq should hard-delete a DRAFT RFQ."""
        rfq = _make_rfq(status=RfqStatus.DRAFT)
        mock_db.execute.return_value = _make_scalar_result(rfq)

        await rfq_service.delete_rfq(rfq.id)
        mock_db.delete.assert_awaited_once_with(rfq)


# ---------------------------------------------------------------------------
# Line Items
# ---------------------------------------------------------------------------


class TestLineItems:
    @pytest.mark.asyncio
    async def test_add_line_item_non_draft_raises(self, rfq_service, mock_db):
        """add_line_item should raise for non-DRAFT RFQs."""
        rfq = _make_rfq(status=RfqStatus.PUBLISHED)
        mock_db.execute.return_value = _make_scalar_result(rfq)

        with pytest.raises(BusinessRuleException, match="DRAFT"):
            await rfq_service.add_line_item(
                rfq.id, line_number=1, description="Rope",
                quantity=10.0, unit_of_measure="EA",
            )

    @pytest.mark.asyncio
    async def test_add_line_item_draft(self, rfq_service, mock_db):
        """add_line_item should succeed on a DRAFT RFQ."""
        rfq = _make_rfq(status=RfqStatus.DRAFT)
        # First call returns RFQ, second returns count
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        mock_db.execute.side_effect = [_make_scalar_result(rfq), count_result]

        await rfq_service.add_line_item(
            rfq.id, line_number=1, description="Rope",
            quantity=10.0, unit_of_measure="EA",
        )
        mock_db.add.assert_called()
        mock_db.flush.assert_awaited()


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


class TestInvitations:
    @pytest.mark.asyncio
    async def test_invite_suppliers_non_draft_raises(self, rfq_service, mock_db):
        """invite_suppliers should raise for RFQs not in DRAFT or PUBLISHED."""
        rfq = _make_rfq(status=RfqStatus.BIDDING_OPEN)
        mock_db.execute.return_value = _make_scalar_result(rfq)

        with pytest.raises(BusinessRuleException, match="DRAFT or PUBLISHED"):
            await rfq_service.invite_suppliers(
                rfq.id, [uuid.uuid4()], uuid.uuid4()
            )

    @pytest.mark.asyncio
    async def test_invite_suppliers_happy_path(self, rfq_service, mock_db):
        """invite_suppliers should create invitations for new supplier orgs."""
        rfq = _make_rfq(status=RfqStatus.DRAFT)
        org_id_1 = uuid.uuid4()
        org_id_2 = uuid.uuid4()
        inviter_id = uuid.uuid4()

        # First call: get_rfq, second call: existing invitations (empty)
        existing_scalars = MagicMock()
        existing_scalars.all.return_value = []
        existing_result = MagicMock()
        existing_result.scalars.return_value = existing_scalars

        mock_db.execute.side_effect = [
            _make_scalar_result(rfq),  # get_rfq
            existing_result,           # existing invitation query
        ]

        invitations = await rfq_service.invite_suppliers(
            rfq.id, [org_id_1, org_id_2], inviter_id
        )

        assert len(invitations) == 2
        assert mock_db.add.call_count == 2
        mock_db.flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_invite_suppliers_skips_duplicates(self, rfq_service, mock_db):
        """invite_suppliers should skip supplier orgs that already have invitations."""
        rfq = _make_rfq(status=RfqStatus.DRAFT)
        existing_org_id = uuid.uuid4()
        new_org_id = uuid.uuid4()
        inviter_id = uuid.uuid4()

        # Existing invitations include existing_org_id
        existing_scalars = MagicMock()
        existing_scalars.all.return_value = [existing_org_id]
        existing_result = MagicMock()
        existing_result.scalars.return_value = existing_scalars

        mock_db.execute.side_effect = [
            _make_scalar_result(rfq),  # get_rfq
            existing_result,           # existing invitation query
        ]

        invitations = await rfq_service.invite_suppliers(
            rfq.id, [existing_org_id, new_org_id], inviter_id
        )

        # Only the new org should get an invitation
        assert len(invitations) == 1
        assert mock_db.add.call_count == 1

    @pytest.mark.asyncio
    async def test_respond_to_invitation_not_found(self, rfq_service, mock_db):
        """respond_to_invitation should raise for unknown invitation."""
        mock_db.execute.return_value = _make_scalar_result(None)

        with pytest.raises(NotFoundException, match="No invitation found"):
            await rfq_service.respond_to_invitation(
                uuid.uuid4(), uuid.uuid4(), accept=True
            )

    @pytest.mark.asyncio
    async def test_respond_to_invitation_non_pending(self, rfq_service, mock_db):
        """respond_to_invitation should raise for non-PENDING invitations."""
        invitation = MagicMock()
        invitation.status = InvitationStatus.ACCEPTED
        mock_db.execute.return_value = _make_scalar_result(invitation)

        with pytest.raises(BusinessRuleException, match="Cannot respond"):
            await rfq_service.respond_to_invitation(
                uuid.uuid4(), uuid.uuid4(), accept=True
            )

    @pytest.mark.asyncio
    async def test_respond_accept(self, rfq_service, mock_db):
        """respond_to_invitation should set ACCEPTED status."""
        invitation = MagicMock()
        invitation.status = InvitationStatus.PENDING
        mock_db.execute.return_value = _make_scalar_result(invitation)

        result = await rfq_service.respond_to_invitation(
            uuid.uuid4(), uuid.uuid4(), accept=True
        )
        assert result.status == InvitationStatus.ACCEPTED

    @pytest.mark.asyncio
    async def test_respond_decline(self, rfq_service, mock_db):
        """respond_to_invitation should set DECLINED status."""
        invitation = MagicMock()
        invitation.status = InvitationStatus.PENDING
        mock_db.execute.return_value = _make_scalar_result(invitation)

        result = await rfq_service.respond_to_invitation(
            uuid.uuid4(), uuid.uuid4(), accept=False
        )
        assert result.status == InvitationStatus.DECLINED


# ---------------------------------------------------------------------------
# State Machine Transitions
# ---------------------------------------------------------------------------


class TestTransitions:
    @pytest.mark.asyncio
    async def test_invalid_transition_raises(self, rfq_service, mock_db):
        """transition should raise for invalid state machine transitions."""
        rfq = _make_rfq(status=RfqStatus.DRAFT)
        mock_db.execute.return_value = _make_scalar_result(rfq)

        with pytest.raises(BusinessRuleException, match="Cannot perform"):
            await rfq_service.transition(
                rfq.id, RfqTransitionType.CLOSE_BIDDING, uuid.uuid4()
            )

    @pytest.mark.asyncio
    async def test_publish_guard_no_line_items(self, rfq_service, mock_db):
        """PUBLISH guard should reject when no line items exist."""
        rfq = _make_rfq(
            status=RfqStatus.DRAFT,
            bidding_deadline=datetime.now(UTC) + timedelta(days=7),
        )
        # get_rfq returns rfq, then item count=0
        count_zero = MagicMock()
        count_zero.scalar.return_value = 0
        mock_db.execute.side_effect = [
            _make_scalar_result(rfq),  # get_rfq
            count_zero,  # line item count
        ]

        with pytest.raises(BusinessRuleException, match="at least one line item"):
            await rfq_service.transition(
                rfq.id, RfqTransitionType.PUBLISH, uuid.uuid4()
            )

    @pytest.mark.asyncio
    async def test_publish_guard_no_deadline(self, rfq_service, mock_db):
        """PUBLISH guard should reject when no bidding deadline set."""
        rfq = _make_rfq(status=RfqStatus.DRAFT, bidding_deadline=None)
        count_result = MagicMock()
        count_result.scalar.return_value = 1
        mock_db.execute.side_effect = [
            _make_scalar_result(rfq),  # get_rfq
            count_result,  # line item count
        ]

        with pytest.raises(BusinessRuleException, match="bidding deadline"):
            await rfq_service.transition(
                rfq.id, RfqTransitionType.PUBLISH, uuid.uuid4()
            )

    @pytest.mark.asyncio
    async def test_publish_guard_past_deadline(self, rfq_service, mock_db):
        """PUBLISH guard should reject when deadline is in the past."""
        rfq = _make_rfq(
            status=RfqStatus.DRAFT,
            bidding_deadline=datetime.now(UTC) - timedelta(days=1),
        )
        count_result = MagicMock()
        count_result.scalar.return_value = 1
        mock_db.execute.side_effect = [
            _make_scalar_result(rfq),  # get_rfq
            count_result,  # line item count
        ]

        with pytest.raises(BusinessRuleException, match="future"):
            await rfq_service.transition(
                rfq.id, RfqTransitionType.PUBLISH, uuid.uuid4()
            )

    @pytest.mark.asyncio
    async def test_award_guard_no_quote_id(self, rfq_service, mock_db):
        """AWARD guard should reject when no quote_id in metadata."""
        rfq = _make_rfq(status=RfqStatus.EVALUATION)
        mock_db.execute.return_value = _make_scalar_result(rfq)

        with pytest.raises(BusinessRuleException, match="quote_id"):
            await rfq_service.transition(
                rfq.id, RfqTransitionType.AWARD, uuid.uuid4(), metadata={}
            )

    @pytest.mark.asyncio
    async def test_cancel_from_awarded_requires_reason(self, rfq_service, mock_db):
        """CANCEL from AWARDED should require a reason in metadata."""
        rfq = _make_rfq(status=RfqStatus.AWARDED)
        mock_db.execute.return_value = _make_scalar_result(rfq)

        with pytest.raises(BusinessRuleException, match="reason"):
            await rfq_service.transition(
                rfq.id, RfqTransitionType.CANCEL, uuid.uuid4()
            )

    # --- Happy-path transition tests ---

    @pytest.mark.asyncio
    @patch("src.modules.rfq.rfq_service.OutboxService")
    async def test_publish_happy_path(self, mock_outbox_cls, rfq_service, mock_db):
        """PUBLISH should transition DRAFT -> PUBLISHED when all guards pass."""
        rfq = _make_rfq(
            status=RfqStatus.DRAFT,
            bidding_deadline=datetime.now(UTC) + timedelta(days=7),
        )
        mock_outbox_instance = AsyncMock()
        mock_outbox_cls.return_value = mock_outbox_instance

        # Sequence: get_rfq, line_item_count, invitation_count
        mock_db.execute.side_effect = [
            _make_scalar_result(rfq),  # get_rfq
            _make_count_result(1),     # line item count >= 1
            _make_count_result(1),     # invitation count >= 1
        ]

        result = await rfq_service.transition(
            rfq.id, RfqTransitionType.PUBLISH, uuid.uuid4()
        )

        assert result.status == RfqStatus.PUBLISHED
        mock_db.add.assert_called()  # RfqTransition record
        mock_db.flush.assert_awaited()
        mock_outbox_instance.publish_event.assert_awaited_once()
        call_kwargs = mock_outbox_instance.publish_event.call_args
        assert call_kwargs[1]["event_type"] == "rfq.published"

    @pytest.mark.asyncio
    @patch("src.modules.rfq.rfq_service.OutboxService")
    async def test_open_bidding_happy_path(self, mock_outbox_cls, rfq_service, mock_db):
        """OPEN_BIDDING should transition PUBLISHED -> BIDDING_OPEN."""
        rfq = _make_rfq(status=RfqStatus.PUBLISHED)
        mock_outbox_instance = AsyncMock()
        mock_outbox_cls.return_value = mock_outbox_instance

        mock_db.execute.return_value = _make_scalar_result(rfq)

        result = await rfq_service.transition(
            rfq.id, RfqTransitionType.OPEN_BIDDING, uuid.uuid4()
        )

        assert result.status == RfqStatus.BIDDING_OPEN
        mock_db.add.assert_called()
        mock_outbox_instance.publish_event.assert_awaited_once()
        call_kwargs = mock_outbox_instance.publish_event.call_args
        assert call_kwargs[1]["event_type"] == "rfq.bidding_opened"

    @pytest.mark.asyncio
    @patch("src.modules.rfq.rfq_service.OutboxService")
    async def test_close_bidding_happy_path(self, mock_outbox_cls, rfq_service, mock_db):
        """CLOSE_BIDDING should transition BIDDING_OPEN -> BIDDING_CLOSED."""
        rfq = _make_rfq(status=RfqStatus.BIDDING_OPEN)
        mock_outbox_instance = AsyncMock()
        mock_outbox_cls.return_value = mock_outbox_instance

        mock_db.execute.return_value = _make_scalar_result(rfq)

        result = await rfq_service.transition(
            rfq.id, RfqTransitionType.CLOSE_BIDDING, uuid.uuid4()
        )

        assert result.status == RfqStatus.BIDDING_CLOSED
        mock_db.add.assert_called()
        mock_outbox_instance.publish_event.assert_awaited_once()
        call_kwargs = mock_outbox_instance.publish_event.call_args
        assert call_kwargs[1]["event_type"] == "rfq.bidding_closed"

    @pytest.mark.asyncio
    @patch("src.modules.rfq.rfq_service.OutboxService")
    async def test_start_evaluation_happy_path(self, mock_outbox_cls, rfq_service, mock_db):
        """START_EVALUATION should transition BIDDING_CLOSED -> EVALUATION."""
        rfq = _make_rfq(status=RfqStatus.BIDDING_CLOSED)
        mock_outbox_instance = AsyncMock()
        mock_outbox_cls.return_value = mock_outbox_instance

        mock_db.execute.return_value = _make_scalar_result(rfq)

        result = await rfq_service.transition(
            rfq.id, RfqTransitionType.START_EVALUATION, uuid.uuid4()
        )

        assert result.status == RfqStatus.EVALUATION
        mock_outbox_instance.publish_event.assert_awaited_once()
        call_kwargs = mock_outbox_instance.publish_event.call_args
        assert call_kwargs[1]["event_type"] == "rfq.evaluation_started"

    @pytest.mark.asyncio
    @patch("src.modules.rfq.rfq_service.OutboxService")
    async def test_award_happy_path(self, mock_outbox_cls, rfq_service, mock_db):
        """AWARD should transition EVALUATION -> AWARDED, set awarded_quote_id."""
        rfq = _make_rfq(status=RfqStatus.EVALUATION)
        quote_id = uuid.uuid4()
        supplier_org_id = uuid.uuid4()
        quote = MagicMock()
        quote.id = quote_id
        quote.rfq_id = rfq.id
        quote.status = QuoteStatus.SUBMITTED
        quote.supplier_organization_id = supplier_org_id

        mock_outbox_instance = AsyncMock()
        mock_outbox_cls.return_value = mock_outbox_instance

        # Sequence: get_rfq, then guard_award queries quote
        mock_db.execute.side_effect = [
            _make_scalar_result(rfq),    # get_rfq
            _make_scalar_result(quote),  # guard_award: select Quote
        ]

        result = await rfq_service.transition(
            rfq.id, RfqTransitionType.AWARD, uuid.uuid4(),
            metadata={"quote_id": str(quote_id)},
        )

        assert result.status == RfqStatus.AWARDED
        assert rfq.awarded_quote_id == quote_id
        assert quote.status == QuoteStatus.AWARDED
        mock_outbox_instance.publish_event.assert_awaited_once()
        call_kwargs = mock_outbox_instance.publish_event.call_args
        assert call_kwargs[1]["event_type"] == "rfq.awarded"

    @pytest.mark.asyncio
    @patch("src.modules.rfq.rfq_service.OutboxService")
    async def test_complete_happy_path(self, mock_outbox_cls, rfq_service, mock_db):
        """COMPLETE should transition AWARDED -> COMPLETED."""
        rfq = _make_rfq(status=RfqStatus.AWARDED)
        mock_outbox_instance = AsyncMock()
        mock_outbox_cls.return_value = mock_outbox_instance

        mock_db.execute.return_value = _make_scalar_result(rfq)

        result = await rfq_service.transition(
            rfq.id, RfqTransitionType.COMPLETE, uuid.uuid4()
        )

        assert result.status == RfqStatus.COMPLETED
        mock_outbox_instance.publish_event.assert_awaited_once()
        call_kwargs = mock_outbox_instance.publish_event.call_args
        assert call_kwargs[1]["event_type"] == "rfq.completed"

    @pytest.mark.asyncio
    @patch("src.modules.rfq.rfq_service.OutboxService")
    async def test_cancel_from_awarded_happy_path(self, mock_outbox_cls, rfq_service, mock_db):
        """CANCEL from AWARDED with reason should succeed and set cancelled fields."""
        rfq = _make_rfq(status=RfqStatus.AWARDED)
        mock_outbox_instance = AsyncMock()
        mock_outbox_cls.return_value = mock_outbox_instance

        mock_db.execute.return_value = _make_scalar_result(rfq)

        result = await rfq_service.transition(
            rfq.id, RfqTransitionType.CANCEL, uuid.uuid4(),
            reason="Supplier unable to fulfill",
            metadata={"reason": "Supplier unable to fulfill"},
        )

        assert result.status == RfqStatus.CANCELLED
        mock_outbox_instance.publish_event.assert_awaited_once()
        call_kwargs = mock_outbox_instance.publish_event.call_args
        assert call_kwargs[1]["event_type"] == "rfq.cancelled"

    @pytest.mark.asyncio
    @patch("src.modules.rfq.rfq_service.OutboxService")
    async def test_cancel_from_draft_no_reason_required(self, mock_outbox_cls, rfq_service, mock_db):
        """CANCEL from DRAFT should not require a reason."""
        rfq = _make_rfq(status=RfqStatus.DRAFT)
        mock_outbox_instance = AsyncMock()
        mock_outbox_cls.return_value = mock_outbox_instance

        mock_db.execute.return_value = _make_scalar_result(rfq)

        result = await rfq_service.transition(
            rfq.id, RfqTransitionType.CANCEL, uuid.uuid4()
        )

        assert result.status == RfqStatus.CANCELLED

    @pytest.mark.asyncio
    @patch("src.modules.rfq.rfq_service.OutboxService")
    async def test_transition_emits_outbox_event_with_correct_payload(
        self, mock_outbox_cls, rfq_service, mock_db
    ):
        """transition should emit an OutboxService event with correct payload fields."""
        rfq = _make_rfq(status=RfqStatus.PUBLISHED)
        triggered_by = uuid.uuid4()
        mock_outbox_instance = AsyncMock()
        mock_outbox_cls.return_value = mock_outbox_instance

        mock_db.execute.return_value = _make_scalar_result(rfq)

        await rfq_service.transition(
            rfq.id, RfqTransitionType.OPEN_BIDDING, triggered_by
        )

        mock_outbox_instance.publish_event.assert_awaited_once()
        call_kwargs = mock_outbox_instance.publish_event.call_args[1]
        assert call_kwargs["event_type"] == "rfq.bidding_opened"
        assert call_kwargs["aggregate_type"] == "rfq"
        assert call_kwargs["aggregate_id"] == str(rfq.id)
        payload = call_kwargs["payload"]
        assert payload["rfq_id"] == str(rfq.id)
        assert payload["from_status"] == "PUBLISHED"
        assert payload["to_status"] == "BIDDING_OPEN"
        assert payload["triggered_by"] == str(triggered_by)


# ---------------------------------------------------------------------------
# Audit Trail
# ---------------------------------------------------------------------------


class TestAuditTrail:
    @pytest.mark.asyncio
    async def test_get_transitions(self, rfq_service, mock_db):
        """get_transitions should return transition records."""
        transitions = [MagicMock(), MagicMock()]
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = transitions
        result = MagicMock()
        result.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result

        result_list = await rfq_service.get_transitions(uuid.uuid4())
        assert len(result_list) == 2
