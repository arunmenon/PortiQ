"""Delivery & Proof-of-Delivery API router — 9 endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.exceptions import ForbiddenException, NotFoundException
from src.models.enums import DeliveryStatus
from src.modules.delivery.schemas import (
    DeliveryAcceptRequest,
    DeliveryCreate,
    DeliveryDetailResponse,
    DeliveryDispatchRequest,
    DeliveryDisputeRequest,
    DeliveryListResponse,
    DeliveryRecordRequest,
    DeliveryResponse,
    DeliverySlaConfigResponse,
    PhotoUploadRequest,
    PhotoUploadResponse,
)
from src.modules.delivery.service import DeliveryService
from src.modules.tenancy.auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/deliveries", tags=["deliveries"])

# Secondary router for SLA config (different prefix)
sla_router = APIRouter(prefix="/delivery-sla", tags=["deliveries"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_supplier(user: AuthenticatedUser) -> None:
    """Raise ForbiddenException unless the user is from a supplier org or platform."""
    if user.organization_type not in ("SUPPLIER", "BOTH", "PLATFORM"):
        raise ForbiddenException("This action requires a supplier organization")


def _require_buyer(user: AuthenticatedUser) -> None:
    """Raise ForbiddenException unless the user is from a buyer org or platform."""
    if user.organization_type not in ("BUYER", "BOTH", "PLATFORM"):
        raise ForbiddenException("This action requires a buyer organization")


# ---------------------------------------------------------------------------
# Create delivery
# ---------------------------------------------------------------------------


@router.post("/", response_model=DeliveryResponse, status_code=201)
async def create_delivery(
    body: DeliveryCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new delivery linked to a fulfillment."""
    _require_supplier(user)
    svc = DeliveryService(db)
    delivery = await svc.create_delivery(
        fulfillment_id=body.fulfillment_id,
        organization_id=user.organization_id,
        created_by=user.id,
        delivery_type=body.delivery_type,
        estimated_arrival=body.estimated_arrival,
    )
    return DeliveryResponse.model_validate(delivery)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


@router.post("/{delivery_id}/dispatch", response_model=DeliveryResponse)
async def dispatch_delivery(
    delivery_id: uuid.UUID,
    body: DeliveryDispatchRequest | None = None,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a delivery as dispatched."""
    _require_supplier(user)
    svc = DeliveryService(db)
    delivery = await svc.dispatch_delivery(
        delivery_id=delivery_id,
        dispatched_by=user.id,
        estimated_arrival=body.estimated_arrival if body else None,
    )
    return DeliveryResponse.model_validate(delivery)


# ---------------------------------------------------------------------------
# Record delivery (POD)
# ---------------------------------------------------------------------------


@router.post("/{delivery_id}/record", response_model=DeliveryResponse)
async def record_delivery(
    delivery_id: uuid.UUID,
    body: DeliveryRecordRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record proof-of-delivery: GPS, receiver info, signature, item quantities."""
    _require_supplier(user)
    svc = DeliveryService(db)
    delivery = await svc.record_delivery(
        delivery_id=delivery_id,
        delivered_by=user.id,
        receiver_name=body.receiver_name,
        receiver_designation=body.receiver_designation,
        receiver_contact=body.receiver_contact,
        delivery_latitude=body.delivery_latitude,
        delivery_longitude=body.delivery_longitude,
        gps_accuracy_meters=body.gps_accuracy_meters,
        signature_s3_key=body.signature_s3_key,
        delivery_type=body.delivery_type,
        items=[item.model_dump() for item in body.items],
    )
    return DeliveryResponse.model_validate(delivery)


# ---------------------------------------------------------------------------
# Photo upload
# ---------------------------------------------------------------------------


@router.post(
    "/{delivery_id}/photos",
    response_model=PhotoUploadResponse,
    status_code=201,
)
async def upload_photo(
    delivery_id: uuid.UUID,
    body: PhotoUploadRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a presigned S3 URL for uploading a delivery photo."""
    svc = DeliveryService(db)
    result = await svc.generate_photo_upload_url(
        delivery_id=delivery_id,
        photo_type=body.photo_type,
        file_name=body.file_name,
        content_type=body.content_type,
        delivery_item_id=body.delivery_item_id,
        caption=body.caption,
        uploaded_by=user.id,
    )
    return PhotoUploadResponse(**result)


# ---------------------------------------------------------------------------
# Accept delivery
# ---------------------------------------------------------------------------


@router.post("/{delivery_id}/accept", response_model=DeliveryResponse)
async def accept_delivery(
    delivery_id: uuid.UUID,
    body: DeliveryAcceptRequest | None = None,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Buyer accepts a delivered shipment."""
    _require_buyer(user)
    svc = DeliveryService(db)
    delivery = await svc.accept_delivery(
        delivery_id=delivery_id,
        accepted_by=user.id,
        notes=body.notes if body else None,
    )
    return DeliveryResponse.model_validate(delivery)


# ---------------------------------------------------------------------------
# Dispute
# ---------------------------------------------------------------------------


@router.post("/{delivery_id}/dispute", response_model=DeliveryResponse)
async def dispute_delivery(
    delivery_id: uuid.UUID,
    body: DeliveryDisputeRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Flag a delivery as disputed."""
    _require_buyer(user)
    svc = DeliveryService(db)
    delivery = await svc.flag_dispute(
        delivery_id=delivery_id,
        reason=body.reason,
        disputed_by=user.id,
        items=[item.model_dump() for item in body.items],
    )
    return DeliveryResponse.model_validate(delivery)


# ---------------------------------------------------------------------------
# List / Get
# ---------------------------------------------------------------------------


@router.get("/", response_model=DeliveryListResponse)
async def list_deliveries(
    status: DeliveryStatus | None = Query(None),
    order_id: uuid.UUID | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List deliveries visible to the calling organization."""
    svc = DeliveryService(db)
    items, total = await svc.list_deliveries(
        organization_id=user.organization_id,
        organization_type=user.organization_type,
        status=status,
        order_id=order_id,
        limit=limit,
        offset=offset,
    )
    return DeliveryListResponse(
        items=[DeliveryResponse.model_validate(d) for d in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{delivery_id}", response_model=DeliveryDetailResponse)
async def get_delivery(
    delivery_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get delivery detail with items and photos."""
    svc = DeliveryService(db)
    delivery = await svc.get_delivery(delivery_id)
    return DeliveryDetailResponse.model_validate(delivery)


# ---------------------------------------------------------------------------
# SLA Config
# ---------------------------------------------------------------------------


@sla_router.get(
    "/{buyer_org_id}/{supplier_org_id}",
    response_model=DeliverySlaConfigResponse,
)
async def get_sla_config(
    buyer_org_id: uuid.UUID,
    supplier_org_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get SLA configuration for a buyer-supplier pair."""
    svc = DeliveryService(db)
    config = await svc.get_sla_config(buyer_org_id, supplier_org_id)
    if config is None:
        raise NotFoundException(
            f"No SLA config found for buyer {buyer_org_id} / supplier {supplier_org_id}"
        )
    return DeliverySlaConfigResponse.model_validate(config)
