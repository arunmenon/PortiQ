"""Order lifecycle service — creation from award, fulfillment, status transitions."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.exceptions import BusinessRuleException, NotFoundException
from src.models.enums import (
    FulfillmentLineItemStatus,
    FulfillmentStatus,
    OrderStatus,
    QuoteStatus,
    RfqStatus,
    VendorOrderStatus,
)
from src.models.fulfillment import Fulfillment
from src.models.fulfillment_item import FulfillmentItem
from src.models.order import Order
from src.models.order_line_item import OrderLineItem
from src.models.quote import Quote
from src.models.quote_line_item import QuoteLineItem
from src.models.rfq import Rfq
from src.models.rfq_line_item import RfqLineItem
from src.models.vendor_order import VendorOrder
from src.modules.events.outbox_service import OutboxService
from src.modules.order.constants import (
    EVENT_FULFILLMENT_CREATED,
    EVENT_FULFILLMENT_STATUS_UPDATED,
    EVENT_ORDER_CANCELLED,
    EVENT_ORDER_CREATED,
    EVENT_VENDOR_ORDER_STATUS_UPDATED,
    FULFILLMENT_TRANSITIONS,
    ORDER_TERMINAL_STATUSES,
    ORDER_TRANSITIONS,
    VENDOR_ORDER_TRANSITIONS,
)

logger = logging.getLogger(__name__)


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Reference number generation
    # ------------------------------------------------------------------

    async def _generate_order_number(self) -> str:
        """Generate ORD-YYYY-NNNNNN reference using a DB sequence."""
        result = await self.db.execute(text("SELECT nextval('order_number_seq')"))
        seq_val = result.scalar()
        year = datetime.now(UTC).year
        return f"ORD-{year}-{seq_val:06d}"

    async def _generate_fulfillment_number(self, vendor_order_number: str) -> str:
        """Generate fulfillment number: {vendor_order_number}-FUL-{seq}."""
        result = await self.db.execute(
            text("SELECT nextval('fulfillment_number_seq')")
        )
        seq_val = result.scalar()
        return f"{vendor_order_number}-FUL-{seq_val:04d}"

    # ------------------------------------------------------------------
    # Create order from RFQ award
    # ------------------------------------------------------------------

    async def create_from_award(
        self,
        rfq_id: uuid.UUID,
        buyer_org_id: uuid.UUID,
        delivery_port: str | None = None,
        vessel_imo: str | None = None,
        vessel_name: str | None = None,
        requested_delivery_date=None,
        notes: str | None = None,
    ) -> Order:
        """Create an Order with VendorOrder(s) and LineItems from an awarded RFQ."""
        # Fetch the RFQ
        rfq_result = await self.db.execute(
            select(Rfq).where(Rfq.id == rfq_id)
        )
        rfq = rfq_result.scalar_one_or_none()
        if rfq is None:
            raise NotFoundException(f"RFQ {rfq_id} not found")

        if rfq.status != RfqStatus.AWARDED:
            raise BusinessRuleException(
                f"Cannot create order from RFQ in status '{rfq.status.value}'. "
                "RFQ must be in AWARDED status."
            )

        if rfq.buyer_organization_id != buyer_org_id:
            raise BusinessRuleException(
                "Only the buyer organization that owns the RFQ can create an order"
            )

        if rfq.awarded_quote_id is None:
            raise BusinessRuleException("RFQ has no awarded quote")

        # Check no order already exists for this RFQ
        existing_result = await self.db.execute(
            select(func.count()).select_from(Order).where(Order.rfq_id == rfq_id)
        )
        if (existing_result.scalar() or 0) > 0:
            raise BusinessRuleException(
                f"An order already exists for RFQ {rfq_id}"
            )

        # Fetch the awarded quote with line items
        quote_result = await self.db.execute(
            select(Quote)
            .options(joinedload(Quote.line_items))
            .where(Quote.id == rfq.awarded_quote_id)
        )
        quote = quote_result.unique().scalar_one_or_none()
        if quote is None:
            raise NotFoundException(f"Awarded quote {rfq.awarded_quote_id} not found")

        if quote.status != QuoteStatus.AWARDED:
            raise BusinessRuleException(
                f"Quote is in status '{quote.status.value}', expected AWARDED"
            )

        # Fetch RFQ line items for product name / IMPA code lookup
        rfq_line_items_result = await self.db.execute(
            select(RfqLineItem).where(RfqLineItem.rfq_id == rfq_id)
        )
        rfq_line_items_map: dict[uuid.UUID, RfqLineItem] = {
            rli.id: rli for rli in rfq_line_items_result.scalars().all()
        }

        # Generate order number
        order_number = await self._generate_order_number()

        # Calculate total from quote line items
        total_amount = sum(
            (qli.total_price for qli in quote.line_items), Decimal("0")
        )

        # Create the Order — skip PENDING_PAYMENT for MVP, go straight to CONFIRMED
        order = Order(
            order_number=order_number,
            rfq_id=rfq_id,
            buyer_org_id=buyer_org_id,
            status=OrderStatus.CONFIRMED,
            total_amount=total_amount,
            currency=quote.currency,
            delivery_port=delivery_port or rfq.delivery_port,
            vessel_imo=vessel_imo,
            vessel_name=vessel_name,
            requested_delivery_date=requested_delivery_date,
            metadata_extra={"notes": notes} if notes else {},
        )
        self.db.add(order)
        await self.db.flush()

        # Create vendor order for the awarded supplier
        supplier_id = quote.supplier_organization_id
        supplier_id_suffix = str(supplier_id)[-4:]
        vendor_order_number = f"{order_number}-{supplier_id_suffix}"

        vendor_order = VendorOrder(
            vendor_order_number=vendor_order_number,
            order_id=order.id,
            supplier_id=supplier_id,
            status=VendorOrderStatus.PENDING_CONFIRMATION,
            amount=total_amount,
        )
        self.db.add(vendor_order)
        await self.db.flush()

        # Create order line items from quote line items
        for qli in quote.line_items:
            rfq_li = rfq_line_items_map.get(qli.rfq_line_item_id)
            impa_code = (rfq_li.impa_code if rfq_li and rfq_li.impa_code else "000000")
            product_name = rfq_li.description if rfq_li else "Unknown"
            product_id = rfq_li.product_id if rfq_li else None

            line_item = OrderLineItem(
                vendor_order_id=vendor_order.id,
                product_id=product_id,
                impa_code=impa_code,
                product_name=product_name,
                quantity_ordered=int(qli.quantity),
                unit_price=qli.unit_price,
                line_total=qli.total_price,
                status=FulfillmentLineItemStatus.PENDING,
            )
            self.db.add(line_item)

        await self.db.flush()

        # Emit event
        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=EVENT_ORDER_CREATED,
            aggregate_type="order",
            aggregate_id=str(order.id),
            payload={
                "order_id": str(order.id),
                "order_number": order_number,
                "rfq_id": str(rfq_id),
                "buyer_org_id": str(buyer_org_id),
                "supplier_id": str(supplier_id),
                "total_amount": str(total_amount),
                "currency": quote.currency,
            },
        )

        logger.info(
            "Created order %s from RFQ %s (quote %s)",
            order.id, rfq_id, quote.id,
        )

        # Re-fetch with relationships for response
        return await self.get_order(order.id)

    # ------------------------------------------------------------------
    # Get / List orders
    # ------------------------------------------------------------------

    async def get_order(self, order_id: uuid.UUID) -> Order:
        """Get an order with vendor orders, line items, and fulfillments."""
        result = await self.db.execute(
            select(Order)
            .options(
                joinedload(Order.vendor_orders)
                .joinedload(VendorOrder.line_items),
                joinedload(Order.vendor_orders)
                .joinedload(VendorOrder.fulfillments)
                .joinedload(Fulfillment.items),
            )
            .where(Order.id == order_id)
        )
        order = result.unique().scalar_one_or_none()
        if order is None:
            raise NotFoundException(f"Order {order_id} not found")
        return order

    async def list_orders(
        self,
        buyer_org_id: uuid.UUID,
        status: OrderStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Order], int]:
        """List orders for a buyer organization, paginated."""
        query = select(Order).where(Order.buyer_org_id == buyer_org_id)
        count_query = (
            select(func.count())
            .select_from(Order)
            .where(Order.buyer_org_id == buyer_org_id)
        )

        if status is not None:
            query = query.where(Order.status == status)
            count_query = count_query.where(Order.status == status)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Order.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    # ------------------------------------------------------------------
    # Supplier vendor orders
    # ------------------------------------------------------------------

    async def list_supplier_orders(
        self,
        supplier_org_id: uuid.UUID,
        status: VendorOrderStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[VendorOrder], int]:
        """List vendor orders for a supplier organization."""
        query = select(VendorOrder).where(VendorOrder.supplier_id == supplier_org_id)
        count_query = (
            select(func.count())
            .select_from(VendorOrder)
            .where(VendorOrder.supplier_id == supplier_org_id)
        )

        if status is not None:
            query = query.where(VendorOrder.status == status)
            count_query = count_query.where(VendorOrder.status == status)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(VendorOrder.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_vendor_order(self, vendor_order_id: uuid.UUID) -> VendorOrder:
        """Get a vendor order with line items and fulfillments."""
        result = await self.db.execute(
            select(VendorOrder)
            .options(
                joinedload(VendorOrder.line_items),
                joinedload(VendorOrder.fulfillments)
                .joinedload(Fulfillment.items),
            )
            .where(VendorOrder.id == vendor_order_id)
        )
        vo = result.unique().scalar_one_or_none()
        if vo is None:
            raise NotFoundException(f"Vendor order {vendor_order_id} not found")
        return vo

    # ------------------------------------------------------------------
    # Vendor order status transitions
    # ------------------------------------------------------------------

    async def update_vendor_order_status(
        self,
        vendor_order_id: uuid.UUID,
        new_status: VendorOrderStatus,
        triggered_by: uuid.UUID,
        reason: str | None = None,
    ) -> VendorOrder:
        """Update vendor order status with transition validation."""
        vo = await self.get_vendor_order(vendor_order_id)

        allowed = VENDOR_ORDER_TRANSITIONS.get(vo.status, set())
        if new_status not in allowed:
            raise BusinessRuleException(
                f"Cannot transition vendor order from '{vo.status.value}' "
                f"to '{new_status.value}'. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        old_status = vo.status
        vo.status = new_status

        if new_status == VendorOrderStatus.CONFIRMED:
            vo.confirmed_at = datetime.now(UTC)

        await self.db.flush()

        # Emit event
        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=EVENT_VENDOR_ORDER_STATUS_UPDATED,
            aggregate_type="vendor_order",
            aggregate_id=str(vendor_order_id),
            payload={
                "vendor_order_id": str(vendor_order_id),
                "vendor_order_number": vo.vendor_order_number,
                "order_id": str(vo.order_id),
                "from_status": old_status.value,
                "to_status": new_status.value,
                "triggered_by": str(triggered_by),
                "reason": reason,
            },
        )

        logger.info(
            "Vendor order %s transitioned %s -> %s",
            vendor_order_id, old_status.value, new_status.value,
        )
        return vo

    # ------------------------------------------------------------------
    # Cancel order
    # ------------------------------------------------------------------

    async def cancel_order(
        self,
        order_id: uuid.UUID,
        reason: str,
        cancelled_by: uuid.UUID,
    ) -> Order:
        """Cancel an order and all its vendor orders."""
        order = await self.get_order(order_id)

        if order.status in ORDER_TERMINAL_STATUSES:
            raise BusinessRuleException(
                f"Cannot cancel order in terminal status '{order.status.value}'"
            )

        allowed = ORDER_TRANSITIONS.get(order.status, set())
        if OrderStatus.CANCELLED not in allowed:
            raise BusinessRuleException(
                f"Cannot cancel order in status '{order.status.value}'"
            )

        order.status = OrderStatus.CANCELLED

        # Cancel all non-terminal vendor orders
        for vo in order.vendor_orders:
            if vo.status not in {VendorOrderStatus.FULFILLED, VendorOrderStatus.CANCELLED}:
                vo.status = VendorOrderStatus.CANCELLED

        await self.db.flush()

        # Emit event
        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=EVENT_ORDER_CANCELLED,
            aggregate_type="order",
            aggregate_id=str(order_id),
            payload={
                "order_id": str(order_id),
                "order_number": order.order_number,
                "cancelled_by": str(cancelled_by),
                "reason": reason,
            },
        )

        logger.info("Cancelled order %s: %s", order_id, reason)
        return order

    # ------------------------------------------------------------------
    # Fulfillment
    # ------------------------------------------------------------------

    async def create_fulfillment(
        self,
        vendor_order_id: uuid.UUID,
        delivery_type=None,
        delivery_address: str | None = None,
        carrier: str | None = None,
        items: list[dict] | None = None,
        created_by: uuid.UUID | None = None,
    ) -> Fulfillment:
        """Create a fulfillment shipment for a vendor order."""
        vo = await self.get_vendor_order(vendor_order_id)

        if vo.status in {VendorOrderStatus.CANCELLED, VendorOrderStatus.FULFILLED}:
            raise BusinessRuleException(
                f"Cannot create fulfillment for vendor order in status '{vo.status.value}'"
            )

        if not items:
            raise BusinessRuleException("Fulfillment must include at least one item")

        # Build a map of line items for this vendor order
        line_items_map: dict[uuid.UUID, OrderLineItem] = {
            li.id: li for li in vo.line_items
        }

        # Validate each fulfillment item
        for item_data in items:
            line_item_id = item_data["line_item_id"]
            quantity = item_data["quantity"]

            li = line_items_map.get(line_item_id)
            if li is None:
                raise NotFoundException(
                    f"Line item {line_item_id} not found on vendor order {vendor_order_id}"
                )

            remaining = li.quantity_ordered - li.quantity_fulfilled
            if quantity > remaining:
                raise BusinessRuleException(
                    f"Cannot ship {quantity} units of '{li.product_name}'. "
                    f"Only {remaining} remaining (ordered: {li.quantity_ordered}, "
                    f"already fulfilled: {li.quantity_fulfilled})."
                )

        # Generate fulfillment number
        fulfillment_number = await self._generate_fulfillment_number(
            vo.vendor_order_number
        )

        fulfillment = Fulfillment(
            fulfillment_number=fulfillment_number,
            vendor_order_id=vendor_order_id,
            status=FulfillmentStatus.PENDING,
            delivery_type=delivery_type,
            delivery_address=delivery_address,
            carrier=carrier,
        )
        self.db.add(fulfillment)
        await self.db.flush()

        # Create fulfillment items and update line item quantities
        for item_data in items:
            line_item_id = item_data["line_item_id"]
            quantity = item_data["quantity"]

            fi = FulfillmentItem(
                fulfillment_id=fulfillment.id,
                order_line_item_id=line_item_id,
                status=FulfillmentLineItemStatus.ALLOCATED,
                quantity_shipped=quantity,
            )
            self.db.add(fi)

            # Update the line item's fulfilled quantity
            li = line_items_map[line_item_id]
            li.quantity_fulfilled += quantity

        await self.db.flush()

        # Emit event
        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=EVENT_FULFILLMENT_CREATED,
            aggregate_type="fulfillment",
            aggregate_id=str(fulfillment.id),
            payload={
                "fulfillment_id": str(fulfillment.id),
                "fulfillment_number": fulfillment_number,
                "vendor_order_id": str(vendor_order_id),
                "items": [
                    {
                        "line_item_id": str(i["line_item_id"]),
                        "quantity": i["quantity"],
                    }
                    for i in items
                ],
            },
        )

        logger.info(
            "Created fulfillment %s for vendor order %s",
            fulfillment.id, vendor_order_id,
        )

        return await self.get_fulfillment(fulfillment.id)

    async def get_fulfillment(self, fulfillment_id: uuid.UUID) -> Fulfillment:
        """Get a fulfillment with its items."""
        result = await self.db.execute(
            select(Fulfillment)
            .options(joinedload(Fulfillment.items))
            .where(Fulfillment.id == fulfillment_id)
        )
        f = result.unique().scalar_one_or_none()
        if f is None:
            raise NotFoundException(f"Fulfillment {fulfillment_id} not found")
        return f

    async def update_fulfillment_status(
        self,
        fulfillment_id: uuid.UUID,
        new_status: FulfillmentStatus,
        triggered_by: uuid.UUID,
        reason: str | None = None,
    ) -> Fulfillment:
        """Update fulfillment status with transition validation."""
        fulfillment = await self.get_fulfillment(fulfillment_id)

        allowed = FULFILLMENT_TRANSITIONS.get(fulfillment.status, set())
        if new_status not in allowed:
            raise BusinessRuleException(
                f"Cannot transition fulfillment from '{fulfillment.status.value}' "
                f"to '{new_status.value}'. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        old_status = fulfillment.status
        fulfillment.status = new_status

        if new_status == FulfillmentStatus.SHIPPED:
            fulfillment.shipped_at = datetime.now(UTC)
        elif new_status == FulfillmentStatus.DELIVERED:
            fulfillment.delivered_at = datetime.now(UTC)
        elif new_status == FulfillmentStatus.ACCEPTED:
            fulfillment.accepted_at = datetime.now(UTC)

        await self.db.flush()

        # Emit event
        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=EVENT_FULFILLMENT_STATUS_UPDATED,
            aggregate_type="fulfillment",
            aggregate_id=str(fulfillment_id),
            payload={
                "fulfillment_id": str(fulfillment_id),
                "fulfillment_number": fulfillment.fulfillment_number,
                "vendor_order_id": str(fulfillment.vendor_order_id),
                "from_status": old_status.value,
                "to_status": new_status.value,
                "triggered_by": str(triggered_by),
                "reason": reason,
            },
        )

        logger.info(
            "Fulfillment %s transitioned %s -> %s",
            fulfillment_id, old_status.value, new_status.value,
        )
        return fulfillment
