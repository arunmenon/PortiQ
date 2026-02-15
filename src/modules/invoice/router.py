"""Invoice & Settlement API router — 8 endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.exceptions import ForbiddenException
from src.models.enums import InvoiceStatus, SettlementPeriodStatus
from src.modules.invoice.schemas import (
    InvoiceListResponse,
    InvoiceMarkPaidRequest,
    InvoiceResponse,
    ReconciliationResponse,
    SettlementListResponse,
    SettlementPeriodResponse,
)
from src.modules.invoice.service import InvoiceService
from src.modules.tenancy.auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/invoices", tags=["invoices"])
settlement_router = APIRouter(prefix="/settlements", tags=["settlements"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_supplier(user: AuthenticatedUser) -> None:
    """Raise ForbiddenException unless the user is from a supplier org."""
    if user.organization_type not in ("SUPPLIER", "BOTH", "PLATFORM"):
        raise ForbiddenException("This action requires a supplier organization")


def _require_buyer(user: AuthenticatedUser) -> None:
    """Raise ForbiddenException unless the user is from a buyer org or platform."""
    if user.organization_type not in ("BUYER", "BOTH", "PLATFORM"):
        raise ForbiddenException("This action requires a buyer organization")


# ---------------------------------------------------------------------------
# Invoice endpoints
# ---------------------------------------------------------------------------


@router.post("/generate/{delivery_id}", response_model=InvoiceResponse, status_code=201)
async def generate_invoice(
    delivery_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Auto-generate an invoice from an accepted delivery."""
    _require_supplier(user)
    svc = InvoiceService(db)
    invoice = await svc.generate_invoice(
        delivery_id=delivery_id,
        user_org_id=user.organization_id,
    )
    return InvoiceResponse.model_validate(invoice)


@router.get("/", response_model=InvoiceListResponse)
async def list_invoices(
    status: InvoiceStatus | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List invoices for the calling organization."""
    svc = InvoiceService(db)
    items, total = await svc.list_invoices(
        organization_id=user.organization_id,
        organization_type=user.organization_type,
        status=status,
        limit=limit,
        offset=offset,
    )
    return InvoiceListResponse(
        items=[InvoiceResponse.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single invoice with line items."""
    svc = InvoiceService(db)
    invoice = await svc.get_invoice(invoice_id)
    return InvoiceResponse.model_validate(invoice)


@router.put("/{invoice_id}/ready", response_model=InvoiceResponse)
async def mark_invoice_ready(
    invoice_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark invoice as ready for payment (supplier action)."""
    _require_supplier(user)
    svc = InvoiceService(db)
    invoice = await svc.mark_ready(
        invoice_id=invoice_id,
        user_id=user.id,
    )
    return InvoiceResponse.model_validate(invoice)


@router.put("/{invoice_id}/acknowledge", response_model=InvoiceResponse)
async def acknowledge_invoice(
    invoice_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Buyer acknowledges the invoice."""
    _require_buyer(user)
    svc = InvoiceService(db)
    invoice = await svc.acknowledge(
        invoice_id=invoice_id,
        user_id=user.id,
    )
    return InvoiceResponse.model_validate(invoice)


@router.put("/{invoice_id}/mark-paid", response_model=InvoiceResponse)
async def mark_invoice_paid(
    invoice_id: uuid.UUID,
    body: InvoiceMarkPaidRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record payment against an invoice."""
    svc = InvoiceService(db)
    invoice = await svc.mark_paid(
        invoice_id=invoice_id,
        user_id=user.id,
        paid_reference=body.paid_reference,
        notes=body.notes,
    )
    return InvoiceResponse.model_validate(invoice)


@router.get("/{invoice_id}/reconciliation", response_model=ReconciliationResponse)
async def get_reconciliation(
    invoice_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get reconciliation view: ordered vs delivered vs invoiced."""
    svc = InvoiceService(db)
    recon = await svc.get_reconciliation(invoice_id=invoice_id)
    return ReconciliationResponse(**recon)


# ---------------------------------------------------------------------------
# Settlement endpoints
# ---------------------------------------------------------------------------


@settlement_router.get("/", response_model=SettlementListResponse)
async def list_settlements(
    status: SettlementPeriodStatus | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List settlement periods for the calling organization."""
    svc = InvoiceService(db)
    items, total = await svc.list_settlement_periods(
        organization_id=user.organization_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return SettlementListResponse(
        items=[SettlementPeriodResponse.model_validate(sp) for sp in items],
        total=total,
        limit=limit,
        offset=offset,
    )
