"""Order Management API router — 10 endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.exceptions import ForbiddenException
from src.models.enums import OrderStatus, VendorOrderStatus
from src.modules.order.schemas import (
    FulfillmentCreate,
    FulfillmentResponse,
    FulfillmentStatusUpdate,
    OrderCancelRequest,
    OrderCreate,
    OrderListResponse,
    OrderResponse,
    VendorOrderListResponse,
    VendorOrderResponse,
    VendorOrderStatusUpdate,
)
from src.modules.order.service import OrderService
from src.modules.tenancy.auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/orders", tags=["orders"])


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
# Order CRUD
# ---------------------------------------------------------------------------


@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(
    body: OrderCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an order from an awarded RFQ."""
    _require_buyer(user)
    svc = OrderService(db)
    order = await svc.create_from_award(
        rfq_id=body.rfq_id,
        buyer_org_id=user.organization_id,
        delivery_port=body.delivery_port,
        vessel_imo=body.vessel_imo,
        vessel_name=body.vessel_name,
        requested_delivery_date=body.requested_delivery_date,
        notes=body.notes,
    )
    return OrderResponse.model_validate(order)


@router.get("/", response_model=OrderListResponse)
async def list_orders(
    status: OrderStatus | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List orders for the calling buyer organization."""
    _require_buyer(user)
    svc = OrderService(db)
    items, total = await svc.list_orders(
        buyer_org_id=user.organization_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return OrderListResponse(
        items=[OrderResponse.model_validate(o) for o in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/supplier", response_model=VendorOrderListResponse)
async def list_supplier_orders(
    status: VendorOrderStatus | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List vendor orders for the calling supplier organization."""
    _require_supplier(user)
    svc = OrderService(db)
    items, total = await svc.list_supplier_orders(
        supplier_org_id=user.organization_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return VendorOrderListResponse(
        items=[VendorOrderResponse.model_validate(vo) for vo in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single order with vendor orders, line items, and fulfillments."""
    svc = OrderService(db)
    order = await svc.get_order(order_id)
    return OrderResponse.model_validate(order)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: uuid.UUID,
    body: OrderCancelRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an order."""
    _require_buyer(user)
    svc = OrderService(db)
    order = await svc.cancel_order(
        order_id=order_id,
        reason=body.reason,
        cancelled_by=user.id,
    )
    return OrderResponse.model_validate(order)


# ---------------------------------------------------------------------------
# Vendor Orders
# ---------------------------------------------------------------------------


@router.get("/vendor-orders/{vendor_order_id}", response_model=VendorOrderResponse)
async def get_vendor_order(
    vendor_order_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a vendor order with line items and fulfillments."""
    svc = OrderService(db)
    vo = await svc.get_vendor_order(vendor_order_id)
    return VendorOrderResponse.model_validate(vo)


@router.put(
    "/vendor-orders/{vendor_order_id}/status",
    response_model=VendorOrderResponse,
)
async def update_vendor_order_status(
    vendor_order_id: uuid.UUID,
    body: VendorOrderStatusUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update vendor order status (supplier action)."""
    _require_supplier(user)
    svc = OrderService(db)
    vo = await svc.update_vendor_order_status(
        vendor_order_id=vendor_order_id,
        new_status=body.new_status,
        triggered_by=user.id,
        reason=body.reason,
    )
    return VendorOrderResponse.model_validate(vo)


# ---------------------------------------------------------------------------
# Fulfillments
# ---------------------------------------------------------------------------


@router.post(
    "/vendor-orders/{vendor_order_id}/fulfillments",
    response_model=FulfillmentResponse,
    status_code=201,
)
async def create_fulfillment(
    vendor_order_id: uuid.UUID,
    body: FulfillmentCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a fulfillment shipment for a vendor order (supplier action)."""
    _require_supplier(user)
    svc = OrderService(db)
    fulfillment = await svc.create_fulfillment(
        vendor_order_id=vendor_order_id,
        delivery_type=body.delivery_type,
        delivery_address=body.delivery_address,
        carrier=body.carrier,
        items=[item.model_dump() for item in body.items],
        created_by=user.id,
    )
    return FulfillmentResponse.model_validate(fulfillment)


@router.get("/fulfillments/{fulfillment_id}", response_model=FulfillmentResponse)
async def get_fulfillment(
    fulfillment_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a fulfillment with its items."""
    svc = OrderService(db)
    fulfillment = await svc.get_fulfillment(fulfillment_id)
    return FulfillmentResponse.model_validate(fulfillment)


@router.put(
    "/fulfillments/{fulfillment_id}/status",
    response_model=FulfillmentResponse,
)
async def update_fulfillment_status(
    fulfillment_id: uuid.UUID,
    body: FulfillmentStatusUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update fulfillment status."""
    svc = OrderService(db)
    fulfillment = await svc.update_fulfillment_status(
        fulfillment_id=fulfillment_id,
        new_status=body.new_status,
        triggered_by=user.id,
        reason=body.reason,
    )
    return FulfillmentResponse.model_validate(fulfillment)
