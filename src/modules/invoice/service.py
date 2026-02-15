"""Invoice lifecycle service — generation from deliveries, status transitions, reconciliation."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.exceptions import BusinessRuleException, NotFoundException
from src.models.delivery import Delivery
from src.models.delivery_item import DeliveryItem
from src.models.dispute import Dispute
from src.models.enums import (
    DeliveryStatus,
    DisputeResolutionType,
    DisputeStatus,
    InvoiceStatus,
    SettlementPeriodStatus,
    SettlementPeriodType,
)
from src.models.invoice import Invoice
from src.models.invoice_line_item import InvoiceLineItem
from src.models.order import Order
from src.models.order_line_item import OrderLineItem
from src.models.settlement_period import SettlementPeriod
from src.models.vendor_order import VendorOrder
from src.modules.events.outbox_service import OutboxService
from src.modules.invoice.constants import (
    EVENT_INVOICE_ACKNOWLEDGED,
    EVENT_INVOICE_GENERATED,
    EVENT_INVOICE_PAID,
    EVENT_INVOICE_READY,
    INVOICE_TERMINAL_STATUSES,
    INVOICE_TRANSITIONS,
)

logger = logging.getLogger(__name__)


class InvoiceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Reference number generation
    # ------------------------------------------------------------------

    async def _generate_invoice_number(self) -> str:
        """Generate INV-YYYY-NNNNNN reference using a DB sequence."""
        result = await self.db.execute(text("SELECT nextval('invoice_number_seq')"))
        seq_val = result.scalar()
        year = datetime.now(UTC).year
        return f"INV-{year}-{seq_val:06d}"

    # ------------------------------------------------------------------
    # Generate invoice from accepted delivery
    # ------------------------------------------------------------------

    async def generate_invoice(
        self,
        delivery_id: uuid.UUID,
        user_org_id: uuid.UUID,
    ) -> Invoice:
        """Auto-generate an invoice from an accepted delivery.

        Pulls delivery + order data, creates Invoice + InvoiceLineItems from
        accepted delivery items at agreed prices. Applies credit adjustments
        from any resolved disputes.
        """
        # Fetch delivery with items
        delivery_result = await self.db.execute(
            select(Delivery)
            .options(joinedload(Delivery.items))
            .where(Delivery.id == delivery_id)
        )
        delivery = delivery_result.unique().scalar_one_or_none()
        if delivery is None:
            raise NotFoundException(f"Delivery {delivery_id} not found")

        if delivery.status != DeliveryStatus.ACCEPTED:
            raise BusinessRuleException(
                f"Cannot generate invoice for delivery in status '{delivery.status.value}'. "
                "Delivery must be in ACCEPTED status."
            )

        # Check no invoice already exists for this delivery
        existing_result = await self.db.execute(
            select(func.count())
            .select_from(Invoice)
            .where(Invoice.delivery_id == delivery_id)
        )
        if (existing_result.scalar() or 0) > 0:
            raise BusinessRuleException(
                f"An invoice already exists for delivery {delivery_id}"
            )

        # Fetch order for buyer info
        order_result = await self.db.execute(
            select(Order).where(Order.id == delivery.order_id)
        )
        order = order_result.scalar_one_or_none()
        if order is None:
            raise NotFoundException(f"Order {delivery.order_id} not found")

        # Fetch vendor order for supplier info
        vo_result = await self.db.execute(
            select(VendorOrder).where(VendorOrder.id == delivery.vendor_order_id)
        )
        vendor_order = vo_result.scalar_one_or_none()
        if vendor_order is None:
            raise NotFoundException(
                f"Vendor order {delivery.vendor_order_id} not found"
            )

        # Fetch order line items for pricing
        oli_result = await self.db.execute(
            select(OrderLineItem).where(
                OrderLineItem.vendor_order_id == vendor_order.id
            )
        )
        order_line_items_map: dict[uuid.UUID, OrderLineItem] = {
            oli.id: oli for oli in oli_result.scalars().all()
        }

        # Fetch resolved disputes for this delivery to apply credit adjustments
        disputes_result = await self.db.execute(
            select(Dispute).where(
                Dispute.delivery_id == delivery_id,
                Dispute.status.in_([DisputeStatus.RESOLVED, DisputeStatus.CLOSED]),
                Dispute.resolution_amount.isnot(None),
            )
        )
        # Build map: delivery_item_id -> total credit from disputes
        disputes = disputes_result.scalars().all()
        credit_by_delivery_item: dict[uuid.UUID, Decimal] = {}
        for dispute in disputes:
            if dispute.delivery_item_id and dispute.resolution_amount:
                if dispute.resolution_type in (
                    DisputeResolutionType.CREDIT_NOTE,
                    DisputeResolutionType.REFUND,
                    DisputeResolutionType.PRICE_ADJUSTMENT,
                ):
                    credit_by_delivery_item[dispute.delivery_item_id] = (
                        credit_by_delivery_item.get(
                            dispute.delivery_item_id, Decimal("0")
                        )
                        + dispute.resolution_amount
                    )

        # Generate invoice number
        invoice_number = await self._generate_invoice_number()

        # Build line items and calculate totals
        subtotal = Decimal("0")
        total_credits = Decimal("0")
        line_items_to_add: list[InvoiceLineItem] = []

        for di in delivery.items:
            oli = order_line_items_map.get(di.order_line_item_id)
            if oli is None:
                continue

            qty_accepted = di.quantity_accepted or 0
            qty_delivered = di.quantity_delivered or 0
            qty_rejected = di.quantity_rejected or 0

            line_sub = oli.unit_price * qty_accepted
            credit = credit_by_delivery_item.get(di.id, Decimal("0"))
            line_total = line_sub - credit

            subtotal += line_sub
            total_credits += credit

            line_item = InvoiceLineItem(
                order_line_item_id=oli.id,
                delivery_item_id=di.id,
                impa_code=oli.impa_code,
                product_name=oli.product_name,
                quantity_ordered=oli.quantity_ordered,
                quantity_delivered=qty_delivered,
                quantity_accepted=qty_accepted,
                quantity_rejected=qty_rejected,
                unit_price=oli.unit_price,
                line_subtotal=line_sub,
                credit_amount=credit,
                line_total=line_total,
            )
            line_items_to_add.append(line_item)

        total_amount = subtotal - total_credits

        # Create the Invoice
        invoice = Invoice(
            invoice_number=invoice_number,
            organization_id=vendor_order.supplier_id,
            order_id=order.id,
            vendor_order_id=vendor_order.id,
            delivery_id=delivery_id,
            buyer_org_id=order.buyer_org_id,
            supplier_org_id=vendor_order.supplier_id,
            status=InvoiceStatus.DRAFT,
            subtotal=subtotal,
            tax_rate=Decimal("0"),
            tax_amount=Decimal("0"),
            discount_amount=Decimal("0"),
            credit_adjustment=total_credits,
            total_amount=total_amount,
            currency=order.currency,
            buyer_po_number=order.order_number,
            invoice_date=date.today(),
        )
        self.db.add(invoice)
        await self.db.flush()

        # Attach line items
        for li in line_items_to_add:
            li.invoice_id = invoice.id
            self.db.add(li)
        await self.db.flush()

        # Emit event
        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=EVENT_INVOICE_GENERATED,
            aggregate_type="invoice",
            aggregate_id=str(invoice.id),
            payload={
                "invoice_id": str(invoice.id),
                "invoice_number": invoice_number,
                "order_id": str(order.id),
                "delivery_id": str(delivery_id),
                "total_amount": str(total_amount),
                "currency": order.currency,
            },
        )

        logger.info(
            "Generated invoice %s from delivery %s (total: %s)",
            invoice.id,
            delivery_id,
            total_amount,
        )

        return await self.get_invoice(invoice.id)

    # ------------------------------------------------------------------
    # Get / List invoices
    # ------------------------------------------------------------------

    async def get_invoice(self, invoice_id: uuid.UUID) -> Invoice:
        """Get an invoice with line items."""
        result = await self.db.execute(
            select(Invoice)
            .options(joinedload(Invoice.line_items))
            .where(Invoice.id == invoice_id)
        )
        invoice = result.unique().scalar_one_or_none()
        if invoice is None:
            raise NotFoundException(f"Invoice {invoice_id} not found")
        return invoice

    async def list_invoices(
        self,
        organization_id: uuid.UUID,
        organization_type: str,
        status: InvoiceStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Invoice], int]:
        """List invoices for an organization, paginated."""
        # Suppliers see invoices where they are the supplier;
        # buyers see invoices where they are the buyer.
        if organization_type in ("SUPPLIER",):
            org_filter = Invoice.supplier_org_id == organization_id
        else:
            org_filter = Invoice.buyer_org_id == organization_id

        query = select(Invoice).where(org_filter)
        count_query = select(func.count()).select_from(Invoice).where(org_filter)

        if status is not None:
            query = query.where(Invoice.status == status)
            count_query = count_query.where(Invoice.status == status)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Invoice.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    async def mark_ready(
        self,
        invoice_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Invoice:
        """Transition invoice from DRAFT to READY."""
        return await self._transition_status(
            invoice_id=invoice_id,
            new_status=InvoiceStatus.READY,
            user_id=user_id,
            event_type=EVENT_INVOICE_READY,
        )

    async def acknowledge(
        self,
        invoice_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Invoice:
        """Buyer acknowledges the invoice (SENT -> ACKNOWLEDGED)."""
        invoice = await self.get_invoice(invoice_id)
        self._validate_transition(invoice, InvoiceStatus.ACKNOWLEDGED)

        invoice.status = InvoiceStatus.ACKNOWLEDGED
        invoice.acknowledged_at = datetime.now(UTC)
        await self.db.flush()

        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=EVENT_INVOICE_ACKNOWLEDGED,
            aggregate_type="invoice",
            aggregate_id=str(invoice_id),
            payload={
                "invoice_id": str(invoice_id),
                "invoice_number": invoice.invoice_number,
                "buyer_org_id": str(invoice.buyer_org_id),
                "acknowledged_at": invoice.acknowledged_at.isoformat(),
            },
        )

        logger.info("Invoice %s acknowledged", invoice_id)
        return invoice

    async def mark_paid(
        self,
        invoice_id: uuid.UUID,
        user_id: uuid.UUID,
        paid_reference: str | None = None,
        notes: str | None = None,
    ) -> Invoice:
        """Record payment against invoice (ACKNOWLEDGED -> PAID)."""
        invoice = await self.get_invoice(invoice_id)
        self._validate_transition(invoice, InvoiceStatus.PAID)

        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = datetime.now(UTC)
        if paid_reference:
            invoice.paid_reference = paid_reference
        if notes:
            invoice.notes = notes
        await self.db.flush()

        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=EVENT_INVOICE_PAID,
            aggregate_type="invoice",
            aggregate_id=str(invoice_id),
            payload={
                "invoice_id": str(invoice_id),
                "invoice_number": invoice.invoice_number,
                "payment_reference": paid_reference,
                "paid_at": invoice.paid_at.isoformat(),
                "total_amount": str(invoice.total_amount),
            },
        )

        logger.info("Invoice %s marked as paid", invoice_id)
        return invoice

    # ------------------------------------------------------------------
    # Reconciliation
    # ------------------------------------------------------------------

    async def get_reconciliation(
        self,
        invoice_id: uuid.UUID,
    ) -> dict:
        """Build reconciliation view: ordered vs delivered vs invoiced."""
        invoice = await self.get_invoice(invoice_id)

        recon_items = []
        ordered_total = Decimal("0")
        delivered_total = Decimal("0")
        invoiced_total = Decimal("0")
        total_credits = Decimal("0")

        for li in invoice.line_items:
            ordered_line_total = li.unit_price * li.quantity_ordered
            delivered_line_total = li.unit_price * li.quantity_delivered
            variance = ordered_line_total - li.line_total

            ordered_total += ordered_line_total
            delivered_total += delivered_line_total
            invoiced_total += li.line_total
            total_credits += li.credit_amount

            recon_items.append(
                {
                    "order_line_item_id": li.order_line_item_id,
                    "impa_code": li.impa_code,
                    "product_name": li.product_name,
                    "quantity_ordered": li.quantity_ordered,
                    "quantity_delivered": li.quantity_delivered,
                    "quantity_accepted": li.quantity_accepted,
                    "quantity_rejected": li.quantity_rejected,
                    "unit_price": li.unit_price,
                    "ordered_total": ordered_line_total,
                    "delivered_total": delivered_line_total,
                    "invoiced_total": li.line_total,
                    "credit_amount": li.credit_amount,
                    "variance": variance,
                }
            )

        return {
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "order_id": invoice.order_id,
            "delivery_id": invoice.delivery_id,
            "line_items": recon_items,
            "ordered_total": ordered_total,
            "delivered_total": delivered_total,
            "invoiced_total": invoiced_total,
            "total_credits": total_credits,
            "net_variance": ordered_total - invoiced_total,
        }

    # ------------------------------------------------------------------
    # Settlement periods
    # ------------------------------------------------------------------

    async def list_settlement_periods(
        self,
        organization_id: uuid.UUID,
        status: SettlementPeriodStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[SettlementPeriod], int]:
        """List settlement periods for an organization."""
        org_filter = SettlementPeriod.organization_id == organization_id

        query = select(SettlementPeriod).where(org_filter)
        count_query = (
            select(func.count()).select_from(SettlementPeriod).where(org_filter)
        )

        if status is not None:
            query = query.where(SettlementPeriod.status == status)
            count_query = count_query.where(SettlementPeriod.status == status)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = (
            query.order_by(SettlementPeriod.period_start.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_transition(
        self, invoice: Invoice, new_status: InvoiceStatus
    ) -> None:
        """Validate that the transition is allowed."""
        if invoice.status in INVOICE_TERMINAL_STATUSES:
            raise BusinessRuleException(
                f"Cannot transition invoice in terminal status '{invoice.status.value}'"
            )

        allowed = INVOICE_TRANSITIONS.get(invoice.status, set())
        if new_status not in allowed:
            raise BusinessRuleException(
                f"Cannot transition invoice from '{invoice.status.value}' "
                f"to '{new_status.value}'. "
                f"Allowed: {[s.value for s in allowed]}"
            )

    async def _transition_status(
        self,
        invoice_id: uuid.UUID,
        new_status: InvoiceStatus,
        user_id: uuid.UUID,
        event_type: str,
    ) -> Invoice:
        """Generic status transition with event emission."""
        invoice = await self.get_invoice(invoice_id)
        self._validate_transition(invoice, new_status)

        old_status = invoice.status
        invoice.status = new_status

        if new_status == InvoiceStatus.SENT:
            invoice.sent_at = datetime.now(UTC)

        await self.db.flush()

        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=event_type,
            aggregate_type="invoice",
            aggregate_id=str(invoice_id),
            payload={
                "invoice_id": str(invoice_id),
                "invoice_number": invoice.invoice_number,
                "from_status": old_status.value,
                "to_status": new_status.value,
                "triggered_by": str(user_id),
            },
        )

        logger.info(
            "Invoice %s transitioned %s -> %s",
            invoice_id,
            old_status.value,
            new_status.value,
        )
        return invoice
