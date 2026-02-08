"""RFQ & Bidding API router — 24 endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.exceptions import ForbiddenException
from src.models.enums import RfqStatus, RfqTransitionType
from src.modules.rfq.quote_service import QuoteService
from src.modules.rfq.rfq_service import RfqService
from src.modules.rfq.schemas import (
    AwardRequest,
    CancelRequest,
    InvitationCreate,
    InvitationRespondRequest,
    InvitationResponse,
    QuoteCreate,
    QuoteListResponse,
    QuoteResponse,
    RfqCreate,
    RfqLineItemCreate,
    RfqLineItemResponse,
    RfqLineItemUpdate,
    RfqListResponse,
    RfqResponse,
    RfqUpdate,
    TransitionResponse,
)
from src.modules.tenancy.auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/rfqs", tags=["rfqs"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_buyer(user: AuthenticatedUser) -> None:
    """Raise ForbiddenException unless the user is from a buyer org or platform."""
    if user.organization_type not in ("BUYER", "BOTH", "PLATFORM"):
        raise ForbiddenException("This action requires a buyer organization")


def _require_supplier(user: AuthenticatedUser) -> None:
    """Raise ForbiddenException unless the user is from a supplier org."""
    if user.organization_type not in ("SUPPLIER", "BOTH", "PLATFORM"):
        raise ForbiddenException("This action requires a supplier organization")


# ---------------------------------------------------------------------------
# RFQ CRUD
# ---------------------------------------------------------------------------


@router.post("/", response_model=RfqResponse, status_code=201)
async def create_rfq(
    body: RfqCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new RFQ in DRAFT status."""
    _require_buyer(user)
    svc = RfqService(db)
    rfq = await svc.create_rfq(
        buyer_organization_id=user.organization_id,
        created_by=user.id,
        title=body.title,
        description=body.description,
        vessel_id=body.vessel_id,
        delivery_port=body.delivery_port,
        delivery_date=body.delivery_date,
        bidding_deadline=body.bidding_deadline,
        require_all_line_items=body.require_all_line_items,
        allow_partial_quotes=body.allow_partial_quotes,
        allow_quote_revision=body.allow_quote_revision,
        auction_type=body.auction_type,
        currency=body.currency,
        notes=body.notes,
    )

    # Process inline line items if provided
    for item in body.line_items:
        await svc.add_line_item(
            rfq_id=rfq.id,
            line_number=item.line_number,
            description=item.description,
            quantity=item.quantity,
            unit_of_measure=item.unit_of_measure,
            product_id=item.product_id,
            impa_code=item.impa_code,
            specifications=item.specifications,
            notes=item.notes,
        )

    # Re-fetch to include the newly added line items in the response
    if body.line_items:
        rfq = await svc.get_rfq(rfq.id)

    return RfqResponse.model_validate(rfq)


@router.get("/", response_model=RfqListResponse)
async def list_rfqs(
    status: RfqStatus | None = Query(None),
    search: str | None = Query(None, max_length=255),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List RFQs visible to the calling organization."""
    svc = RfqService(db)
    items, total = await svc.list_rfqs(
        organization_id=user.organization_id,
        organization_type=user.organization_type,
        status=status,
        search=search,
        limit=limit,
        offset=offset,
    )
    return RfqListResponse(
        items=[RfqResponse.model_validate(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{rfq_id}", response_model=RfqResponse)
async def get_rfq(
    rfq_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single RFQ by ID."""
    svc = RfqService(db)
    rfq = await svc.get_rfq(rfq_id)
    return RfqResponse.model_validate(rfq)


@router.patch("/{rfq_id}", response_model=RfqResponse)
async def update_rfq(
    rfq_id: uuid.UUID,
    body: RfqUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a DRAFT RFQ."""
    _require_buyer(user)
    svc = RfqService(db)
    rfq = await svc.update_rfq(rfq_id, **body.model_dump(exclude_unset=True))
    return RfqResponse.model_validate(rfq)


@router.delete("/{rfq_id}", status_code=204)
async def delete_rfq(
    rfq_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a DRAFT RFQ."""
    _require_buyer(user)
    svc = RfqService(db)
    await svc.delete_rfq(rfq_id)


# ---------------------------------------------------------------------------
# Line Items
# ---------------------------------------------------------------------------


@router.post(
    "/{rfq_id}/line-items",
    response_model=RfqLineItemResponse,
    status_code=201,
)
async def add_line_item(
    rfq_id: uuid.UUID,
    body: RfqLineItemCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a line item to a DRAFT RFQ."""
    _require_buyer(user)
    svc = RfqService(db)
    item = await svc.add_line_item(
        rfq_id=rfq_id,
        line_number=body.line_number,
        description=body.description,
        quantity=body.quantity,
        unit_of_measure=body.unit_of_measure,
        product_id=body.product_id,
        impa_code=body.impa_code,
        specifications=body.specifications,
        notes=body.notes,
    )
    return RfqLineItemResponse.model_validate(item)


@router.patch(
    "/{rfq_id}/line-items/{item_id}",
    response_model=RfqLineItemResponse,
)
async def update_line_item(
    rfq_id: uuid.UUID,
    item_id: uuid.UUID,
    body: RfqLineItemUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a line item on a DRAFT RFQ."""
    _require_buyer(user)
    svc = RfqService(db)
    item = await svc.update_line_item(
        rfq_id, item_id, **body.model_dump(exclude_unset=True)
    )
    return RfqLineItemResponse.model_validate(item)


@router.delete("/{rfq_id}/line-items/{item_id}", status_code=204)
async def delete_line_item(
    rfq_id: uuid.UUID,
    item_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a line item from a DRAFT RFQ."""
    _require_buyer(user)
    svc = RfqService(db)
    await svc.delete_line_item(rfq_id, item_id)


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


@router.post(
    "/{rfq_id}/invitations",
    response_model=list[InvitationResponse],
    status_code=201,
)
async def invite_suppliers(
    rfq_id: uuid.UUID,
    body: InvitationCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Invite suppliers to bid on an RFQ."""
    _require_buyer(user)
    svc = RfqService(db)
    invitations = await svc.invite_suppliers(
        rfq_id=rfq_id,
        supplier_organization_ids=body.supplier_organization_ids,
        invited_by=user.id,
    )
    return [InvitationResponse.model_validate(inv) for inv in invitations]


@router.get("/{rfq_id}/invitations", response_model=list[InvitationResponse])
async def list_invitations(
    rfq_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all invitations for an RFQ."""
    svc = RfqService(db)
    invitations = await svc.list_invitations(rfq_id)
    return [InvitationResponse.model_validate(inv) for inv in invitations]


@router.delete("/{rfq_id}/invitations/{invitation_id}", status_code=204)
async def remove_invitation(
    rfq_id: uuid.UUID,
    invitation_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a pending invitation from a DRAFT RFQ."""
    _require_buyer(user)
    svc = RfqService(db)
    await svc.remove_invitation(rfq_id, invitation_id)


@router.post("/{rfq_id}/invitations/respond", response_model=InvitationResponse)
async def respond_to_invitation(
    rfq_id: uuid.UUID,
    body: InvitationRespondRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept or decline an RFQ invitation (supplier action)."""
    _require_supplier(user)
    svc = RfqService(db)
    invitation = await svc.respond_to_invitation(
        rfq_id=rfq_id,
        supplier_organization_id=user.organization_id,
        accept=body.accept,
    )
    return InvitationResponse.model_validate(invitation)


# ---------------------------------------------------------------------------
# Transitions
# ---------------------------------------------------------------------------


@router.post("/{rfq_id}/publish", response_model=RfqResponse)
async def publish_rfq(
    rfq_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Publish a DRAFT RFQ (makes it visible to invited suppliers)."""
    _require_buyer(user)
    svc = RfqService(db)
    rfq = await svc.transition(rfq_id, RfqTransitionType.PUBLISH, user.id)
    return RfqResponse.model_validate(rfq)


@router.post("/{rfq_id}/open-bidding", response_model=RfqResponse)
async def open_bidding(
    rfq_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Open bidding on a PUBLISHED RFQ."""
    _require_buyer(user)
    svc = RfqService(db)
    rfq = await svc.transition(rfq_id, RfqTransitionType.OPEN_BIDDING, user.id)
    return RfqResponse.model_validate(rfq)


@router.post("/{rfq_id}/close-bidding", response_model=RfqResponse)
async def close_bidding(
    rfq_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Close bidding on an RFQ."""
    _require_buyer(user)
    svc = RfqService(db)
    rfq = await svc.transition(rfq_id, RfqTransitionType.CLOSE_BIDDING, user.id)
    return RfqResponse.model_validate(rfq)


@router.post("/{rfq_id}/start-evaluation", response_model=RfqResponse)
async def start_evaluation(
    rfq_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start evaluation after bidding closes."""
    _require_buyer(user)
    svc = RfqService(db)
    rfq = await svc.transition(rfq_id, RfqTransitionType.START_EVALUATION, user.id)
    return RfqResponse.model_validate(rfq)


@router.post("/{rfq_id}/award", response_model=RfqResponse)
async def award_rfq(
    rfq_id: uuid.UUID,
    body: AwardRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Award an RFQ to a supplier's quote."""
    _require_buyer(user)
    svc = RfqService(db)
    rfq = await svc.transition(
        rfq_id,
        RfqTransitionType.AWARD,
        user.id,
        metadata={"quote_id": str(body.quote_id)},
    )
    return RfqResponse.model_validate(rfq)


@router.post("/{rfq_id}/complete", response_model=RfqResponse)
async def complete_rfq(
    rfq_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark an awarded RFQ as completed."""
    _require_buyer(user)
    svc = RfqService(db)
    rfq = await svc.transition(rfq_id, RfqTransitionType.COMPLETE, user.id)
    return RfqResponse.model_validate(rfq)


@router.post("/{rfq_id}/cancel", response_model=RfqResponse)
async def cancel_rfq(
    rfq_id: uuid.UUID,
    body: CancelRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an RFQ at any cancellable state."""
    _require_buyer(user)
    svc = RfqService(db)
    rfq = await svc.transition(
        rfq_id,
        RfqTransitionType.CANCEL,
        user.id,
        reason=body.reason,
        metadata={"reason": body.reason} if body.reason else None,
    )
    return RfqResponse.model_validate(rfq)


@router.get("/{rfq_id}/transitions", response_model=list[TransitionResponse])
async def get_transitions(
    rfq_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the full transition (audit) history for an RFQ."""
    svc = RfqService(db)
    transitions = await svc.get_transitions(rfq_id)
    return [TransitionResponse.model_validate(t) for t in transitions]


# ---------------------------------------------------------------------------
# Quotes
# ---------------------------------------------------------------------------


@router.post(
    "/{rfq_id}/quotes",
    response_model=QuoteResponse,
    status_code=201,
)
async def submit_quote(
    rfq_id: uuid.UUID,
    body: QuoteCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a quote for an RFQ (supplier action)."""
    _require_supplier(user)
    svc = QuoteService(db)
    quote = await svc.submit_quote(
        rfq_id=rfq_id,
        supplier_organization_id=user.organization_id,
        submitted_by=user.id,
        line_items=[item.model_dump() for item in body.line_items],
        currency=body.currency,
        valid_until=body.valid_until,
        delivery_port=body.delivery_port,
        estimated_delivery_days=body.estimated_delivery_days,
        payment_terms=body.payment_terms,
        shipping_terms=body.shipping_terms,
        warranty_terms=body.warranty_terms,
        notes=body.notes,
    )
    return QuoteResponse.model_validate(quote)


@router.get("/{rfq_id}/quotes", response_model=QuoteListResponse)
async def list_quotes(
    rfq_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List quotes for an RFQ (visibility rules apply)."""
    svc = QuoteService(db)
    quotes, total = await svc.list_quotes_for_rfq(
        rfq_id=rfq_id,
        viewer_organization_id=user.organization_id,
        viewer_organization_type=user.organization_type,
        limit=limit,
        offset=offset,
    )
    return QuoteListResponse(
        items=[QuoteResponse.model_validate(q) for q in quotes],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{rfq_id}/quotes/{quote_id}", response_model=QuoteResponse)
async def get_quote(
    rfq_id: uuid.UUID,
    quote_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific quote for an RFQ."""
    svc = QuoteService(db)
    quote = await svc.get_quote_detail(
        rfq_id,
        quote_id,
        requesting_org_id=user.organization_id,
        requesting_org_type=user.organization_type,
    )
    return QuoteResponse.model_validate(quote)


@router.post("/{rfq_id}/quotes/{quote_id}/withdraw", response_model=QuoteResponse)
async def withdraw_quote(
    rfq_id: uuid.UUID,
    quote_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Withdraw a submitted quote (supplier action)."""
    _require_supplier(user)
    svc = QuoteService(db)
    quote = await svc.withdraw_quote(
        quote_id=quote_id,
        supplier_organization_id=user.organization_id,
    )
    return QuoteResponse.model_validate(quote)
