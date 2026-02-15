"""Delivery & POD service — CRUD, state transitions, photo uploads, SLA lookup."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.exceptions import BusinessRuleException, NotFoundException
from src.models.delivery import Delivery
from src.models.delivery_item import DeliveryItem
from src.models.delivery_photo import DeliveryPhoto
from src.models.delivery_sla_config import DeliverySlaConfig
from src.models.enums import (
    DeliveryItemStatus,
    DeliveryPhotoType,
    DeliveryStatus,
)
from src.models.fulfillment import Fulfillment
from src.models.fulfillment_item import FulfillmentItem
from src.modules.delivery.constants import (
    EVENT_DELIVERY_ACCEPTED,
    EVENT_DELIVERY_CREATED,
    EVENT_DELIVERY_DISPATCHED,
    EVENT_DELIVERY_DISPUTED,
    EVENT_DELIVERY_PHOTO_UPLOADED,
    EVENT_DELIVERY_RECORDED,
    S3_DELIVERY_BUCKET,
    S3_PHOTO_PREFIX,
    S3_PRESIGNED_URL_EXPIRY_SECONDS,
    VALID_TRANSITIONS,
)
from src.modules.events.outbox_service import OutboxService

logger = logging.getLogger(__name__)


class DeliveryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Reference number generation
    # ------------------------------------------------------------------

    async def _generate_delivery_number(self) -> str:
        """Generate DEL-YYYY-NNNNNN delivery number using a DB sequence."""
        result = await self.db.execute(text("SELECT nextval('delivery_number_seq')"))
        seq_val = result.scalar()
        year = datetime.now(UTC).year
        return f"DEL-{year}-{seq_val:06d}"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _validate_transition(
        self, current: DeliveryStatus, target: DeliveryStatus
    ) -> None:
        """Raise BusinessRuleException if the transition is not allowed."""
        allowed = VALID_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise BusinessRuleException(
                f"Cannot transition from '{current.value}' to '{target.value}'. "
                f"Allowed targets: {[s.value for s in allowed]}"
            )

    async def _get_delivery(self, delivery_id: uuid.UUID) -> Delivery:
        """Fetch a delivery by ID. Raises NotFoundException if missing."""
        result = await self.db.execute(
            select(Delivery).where(Delivery.id == delivery_id)
        )
        delivery = result.scalar_one_or_none()
        if delivery is None:
            raise NotFoundException(f"Delivery {delivery_id} not found")
        return delivery

    async def _get_delivery_with_relations(self, delivery_id: uuid.UUID) -> Delivery:
        """Fetch a delivery with items and photos eagerly loaded."""
        result = await self.db.execute(
            select(Delivery)
            .options(
                joinedload(Delivery.items),
                joinedload(Delivery.photos),
            )
            .where(Delivery.id == delivery_id)
        )
        delivery = result.unique().scalar_one_or_none()
        if delivery is None:
            raise NotFoundException(f"Delivery {delivery_id} not found")
        return delivery

    # ------------------------------------------------------------------
    # Create delivery from fulfillment
    # ------------------------------------------------------------------

    async def create_delivery(
        self,
        fulfillment_id: uuid.UUID,
        organization_id: uuid.UUID,
        created_by: uuid.UUID,
        delivery_type: str | None = None,
        estimated_arrival: datetime | None = None,
    ) -> Delivery:
        """Create a delivery record linked to a fulfillment.

        Auto-creates DeliveryItem rows from the fulfillment's items.
        """
        # Fetch the fulfillment with its items
        result = await self.db.execute(
            select(Fulfillment)
            .options(joinedload(Fulfillment.items))
            .where(Fulfillment.id == fulfillment_id)
        )
        fulfillment = result.unique().scalar_one_or_none()
        if fulfillment is None:
            raise NotFoundException(f"Fulfillment {fulfillment_id} not found")

        delivery_number = await self._generate_delivery_number()

        delivery = Delivery(
            delivery_number=delivery_number,
            fulfillment_id=fulfillment.id,
            vendor_order_id=fulfillment.vendor_order_id,
            order_id=fulfillment.vendor_order_id,  # Will be set correctly below
            organization_id=organization_id,
            status=DeliveryStatus.PENDING,
            delivery_type=delivery_type,
            estimated_arrival=estimated_arrival,
        )

        # Resolve order_id from the vendor_order
        from src.models.vendor_order import VendorOrder

        vo_result = await self.db.execute(
            select(VendorOrder.order_id).where(
                VendorOrder.id == fulfillment.vendor_order_id
            )
        )
        order_id = vo_result.scalar_one_or_none()
        if order_id is None:
            raise NotFoundException(
                f"VendorOrder {fulfillment.vendor_order_id} not found"
            )
        delivery.order_id = order_id

        self.db.add(delivery)
        await self.db.flush()

        # Auto-create delivery items from fulfillment items
        for fi in fulfillment.items:
            delivery_item = DeliveryItem(
                delivery_id=delivery.id,
                fulfillment_item_id=fi.id,
                order_line_item_id=fi.order_line_item_id,
                quantity_expected=fi.quantity_shipped,
                status=DeliveryItemStatus.PENDING,
            )
            self.db.add(delivery_item)

        await self.db.flush()

        # Emit event
        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=EVENT_DELIVERY_CREATED,
            aggregate_type="delivery",
            aggregate_id=str(delivery.id),
            payload={
                "delivery_id": str(delivery.id),
                "delivery_number": delivery_number,
                "fulfillment_id": str(fulfillment_id),
                "order_id": str(order_id),
                "organization_id": str(organization_id),
            },
        )

        logger.info(
            "Created delivery %s (%s) for fulfillment %s",
            delivery.id,
            delivery_number,
            fulfillment_id,
        )
        return delivery

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def dispatch_delivery(
        self,
        delivery_id: uuid.UUID,
        dispatched_by: uuid.UUID,
        estimated_arrival: datetime | None = None,
    ) -> Delivery:
        """Mark a delivery as dispatched."""
        delivery = await self._get_delivery(delivery_id)
        self._validate_transition(delivery.status, DeliveryStatus.DISPATCHED)

        now = datetime.now(UTC)
        delivery.status = DeliveryStatus.DISPATCHED
        delivery.dispatched_at = now
        delivery.dispatched_by = dispatched_by
        if estimated_arrival is not None:
            delivery.estimated_arrival = estimated_arrival

        await self.db.flush()

        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=EVENT_DELIVERY_DISPATCHED,
            aggregate_type="delivery",
            aggregate_id=str(delivery.id),
            payload={
                "delivery_id": str(delivery.id),
                "dispatched_by": str(dispatched_by),
                "dispatched_at": now.isoformat(),
                "estimated_arrival": estimated_arrival.isoformat() if estimated_arrival else None,
            },
        )

        logger.info("Delivery %s dispatched by %s", delivery_id, dispatched_by)
        return delivery

    # ------------------------------------------------------------------
    # Record delivery (POD)
    # ------------------------------------------------------------------

    async def record_delivery(
        self,
        delivery_id: uuid.UUID,
        delivered_by: uuid.UUID,
        receiver_name: str,
        receiver_designation: str | None = None,
        receiver_contact: str | None = None,
        delivery_latitude: float | None = None,
        delivery_longitude: float | None = None,
        gps_accuracy_meters: float | None = None,
        signature_s3_key: str | None = None,
        delivery_type: str | None = None,
        items: list[dict] | None = None,
    ) -> Delivery:
        """Record proof-of-delivery: GPS, receiver info, signature, item quantities."""
        delivery = await self._get_delivery(delivery_id)
        self._validate_transition(delivery.status, DeliveryStatus.DELIVERED)

        now = datetime.now(UTC)
        delivery.status = DeliveryStatus.DELIVERED
        delivery.delivered_at = now
        delivery.delivered_by = delivered_by
        delivery.receiver_name = receiver_name
        delivery.receiver_designation = receiver_designation
        delivery.receiver_contact = receiver_contact

        if delivery_latitude is not None:
            delivery.delivery_latitude = delivery_latitude
        if delivery_longitude is not None:
            delivery.delivery_longitude = delivery_longitude
        if gps_accuracy_meters is not None:
            delivery.gps_accuracy_meters = gps_accuracy_meters
        if signature_s3_key is not None:
            delivery.signature_s3_key = signature_s3_key
            delivery.signature_captured_at = now
        if delivery_type is not None:
            delivery.delivery_type = delivery_type

        # Check SLA
        if delivery.sla_target_time is not None:
            delivery.sla_met = now <= delivery.sla_target_time

        await self.db.flush()

        # Update delivery item quantities
        if items:
            for item_data in items:
                item_id = item_data.get("delivery_item_id")
                if item_id is None:
                    continue
                result = await self.db.execute(
                    select(DeliveryItem).where(
                        DeliveryItem.id == item_id,
                        DeliveryItem.delivery_id == delivery_id,
                    )
                )
                di = result.scalar_one_or_none()
                if di is None:
                    raise NotFoundException(
                        f"Delivery item {item_id} not found on delivery {delivery_id}"
                    )
                di.quantity_delivered = item_data.get("quantity_delivered")
                di.quantity_accepted = item_data.get("quantity_accepted")
                di.quantity_rejected = item_data.get("quantity_rejected", 0)
                di.rejection_reason = item_data.get("rejection_reason")
                di.notes = item_data.get("notes")
                di.status = DeliveryItemStatus.DELIVERED

            await self.db.flush()

        # Emit event
        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=EVENT_DELIVERY_RECORDED,
            aggregate_type="delivery",
            aggregate_id=str(delivery.id),
            payload={
                "delivery_id": str(delivery.id),
                "delivered_by": str(delivered_by),
                "delivered_at": now.isoformat(),
                "receiver_name": receiver_name,
                "gps": {
                    "latitude": str(delivery_latitude) if delivery_latitude else None,
                    "longitude": str(delivery_longitude) if delivery_longitude else None,
                    "accuracy_meters": str(gps_accuracy_meters) if gps_accuracy_meters else None,
                },
                "items_count": len(items) if items else 0,
            },
        )

        logger.info("Delivery %s recorded by %s", delivery_id, delivered_by)
        return delivery

    # ------------------------------------------------------------------
    # Photo upload (presigned URL)
    # ------------------------------------------------------------------

    async def generate_photo_upload_url(
        self,
        delivery_id: uuid.UUID,
        photo_type: DeliveryPhotoType,
        file_name: str,
        content_type: str = "image/jpeg",
        delivery_item_id: uuid.UUID | None = None,
        caption: str | None = None,
        uploaded_by: uuid.UUID | None = None,
    ) -> dict:
        """Create a DeliveryPhoto record and return a presigned upload URL placeholder.

        Actual S3 presigned URL generation is a TODO — returns a placeholder structure.
        """
        # Verify delivery exists
        await self._get_delivery(delivery_id)

        # Generate S3 key
        photo_id = uuid.uuid4()
        s3_key = f"{S3_PHOTO_PREFIX}/{delivery_id}/{photo_id}/{file_name}"

        photo = DeliveryPhoto(
            id=photo_id,
            delivery_id=delivery_id,
            delivery_item_id=delivery_item_id,
            s3_key=s3_key,
            s3_bucket=S3_DELIVERY_BUCKET,
            file_name=file_name,
            content_type=content_type,
            photo_type=photo_type,
            caption=caption,
            uploaded_by=uploaded_by,
        )
        self.db.add(photo)
        await self.db.flush()

        # TODO: Generate actual S3 presigned URL using boto3
        # presigned_url = s3_client.generate_presigned_url(
        #     "put_object",
        #     Params={"Bucket": S3_DELIVERY_BUCKET, "Key": s3_key, "ContentType": content_type},
        #     ExpiresIn=S3_PRESIGNED_URL_EXPIRY_SECONDS,
        # )
        presigned_url = (
            f"https://{S3_DELIVERY_BUCKET}.s3.ap-south-1.amazonaws.com/{s3_key}"
            f"?X-Amz-Expires={S3_PRESIGNED_URL_EXPIRY_SECONDS}"
        )

        # Emit event
        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=EVENT_DELIVERY_PHOTO_UPLOADED,
            aggregate_type="delivery",
            aggregate_id=str(delivery_id),
            payload={
                "delivery_id": str(delivery_id),
                "photo_id": str(photo_id),
                "photo_type": photo_type.value,
                "s3_key": s3_key,
            },
        )

        logger.info("Photo upload URL generated for delivery %s", delivery_id)
        return {
            "photo_id": photo_id,
            "upload_url": presigned_url,
            "s3_key": s3_key,
            "s3_bucket": S3_DELIVERY_BUCKET,
        }

    # ------------------------------------------------------------------
    # Accept delivery
    # ------------------------------------------------------------------

    async def accept_delivery(
        self,
        delivery_id: uuid.UUID,
        accepted_by: uuid.UUID,
        notes: str | None = None,
    ) -> Delivery:
        """Buyer accepts a delivered shipment."""
        delivery = await self._get_delivery(delivery_id)
        self._validate_transition(delivery.status, DeliveryStatus.ACCEPTED)

        now = datetime.now(UTC)
        delivery.status = DeliveryStatus.ACCEPTED
        delivery.accepted_at = now
        delivery.accepted_by = accepted_by
        delivery.acceptance_notes = notes

        # Mark all pending/delivered items as accepted
        items_result = await self.db.execute(
            select(DeliveryItem).where(DeliveryItem.delivery_id == delivery_id)
        )
        for item in items_result.scalars().all():
            if item.status in (DeliveryItemStatus.PENDING, DeliveryItemStatus.DELIVERED):
                item.status = DeliveryItemStatus.ACCEPTED
                if item.quantity_delivered is not None and item.quantity_accepted is None:
                    item.quantity_accepted = item.quantity_delivered

        await self.db.flush()

        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=EVENT_DELIVERY_ACCEPTED,
            aggregate_type="delivery",
            aggregate_id=str(delivery.id),
            payload={
                "delivery_id": str(delivery.id),
                "accepted_by": str(accepted_by),
                "accepted_at": now.isoformat(),
            },
        )

        logger.info("Delivery %s accepted by %s", delivery_id, accepted_by)
        return delivery

    # ------------------------------------------------------------------
    # Dispute delivery
    # ------------------------------------------------------------------

    async def flag_dispute(
        self,
        delivery_id: uuid.UUID,
        reason: str,
        disputed_by: uuid.UUID,
        items: list[dict] | None = None,
    ) -> Delivery:
        """Flag a delivery as disputed."""
        delivery = await self._get_delivery(delivery_id)
        self._validate_transition(delivery.status, DeliveryStatus.DISPUTED)

        now = datetime.now(UTC)
        delivery.status = DeliveryStatus.DISPUTED
        delivery.disputed_at = now
        delivery.dispute_reason = reason

        # Mark specified items as disputed
        if items:
            for item_data in items:
                item_id = item_data.get("delivery_item_id")
                if item_id is None:
                    continue
                result = await self.db.execute(
                    select(DeliveryItem).where(
                        DeliveryItem.id == item_id,
                        DeliveryItem.delivery_id == delivery_id,
                    )
                )
                di = result.scalar_one_or_none()
                if di is None:
                    raise NotFoundException(
                        f"Delivery item {item_id} not found on delivery {delivery_id}"
                    )
                di.status = DeliveryItemStatus.DISPUTED
                di.rejection_reason = item_data.get("reason")

        await self.db.flush()

        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=EVENT_DELIVERY_DISPUTED,
            aggregate_type="delivery",
            aggregate_id=str(delivery.id),
            payload={
                "delivery_id": str(delivery.id),
                "reason": reason,
                "disputed_by": str(disputed_by),
                "disputed_at": now.isoformat(),
                "disputed_items": [
                    str(i.get("delivery_item_id")) for i in (items or [])
                ],
            },
        )

        logger.info("Delivery %s disputed: %s", delivery_id, reason)
        return delivery

    # ------------------------------------------------------------------
    # List / Get
    # ------------------------------------------------------------------

    async def list_deliveries(
        self,
        organization_id: uuid.UUID,
        organization_type: str,
        status: DeliveryStatus | None = None,
        order_id: uuid.UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Delivery], int]:
        """List deliveries visible to the caller's organization."""
        query = select(Delivery)
        count_query = select(func.count()).select_from(Delivery)

        # Platform admins see all; others see their own org's deliveries
        if organization_type != "PLATFORM":
            query = query.where(Delivery.organization_id == organization_id)
            count_query = count_query.where(
                Delivery.organization_id == organization_id
            )

        if status is not None:
            query = query.where(Delivery.status == status)
            count_query = count_query.where(Delivery.status == status)

        if order_id is not None:
            query = query.where(Delivery.order_id == order_id)
            count_query = count_query.where(Delivery.order_id == order_id)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Delivery.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_delivery(self, delivery_id: uuid.UUID) -> Delivery:
        """Get delivery detail with items and photos."""
        return await self._get_delivery_with_relations(delivery_id)

    # ------------------------------------------------------------------
    # SLA Config
    # ------------------------------------------------------------------

    async def get_sla_config(
        self,
        buyer_org_id: uuid.UUID,
        supplier_org_id: uuid.UUID,
    ) -> DeliverySlaConfig | None:
        """Get the SLA configuration for a buyer-supplier pair."""
        result = await self.db.execute(
            select(DeliverySlaConfig).where(
                DeliverySlaConfig.buyer_org_id == buyer_org_id,
                DeliverySlaConfig.supplier_org_id == supplier_org_id,
                DeliverySlaConfig.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()
