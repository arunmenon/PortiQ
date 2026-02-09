"""Reorder service — copy/adapt line items from previous RFQs.

Allows buyers to quickly create new requisitions based on their past orders,
with optional quantity adjustments for different voyage durations or crew sizes.
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.exceptions import NotFoundException
from src.models.enums import RfqStatus
from src.models.rfq import Rfq
from src.models.rfq_line_item import RfqLineItem
from src.modules.prediction.schemas import PredictedItem, ReorderSuggestion

logger = logging.getLogger(__name__)


class ReorderService:
    """Find and copy line items from previous RFQs for reorder workflows."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_last_order(
        self,
        vessel_id: uuid.UUID,
        port: str | None = None,
    ) -> ReorderSuggestion | None:
        """Find the most recent COMPLETED or AWARDED RFQ for this vessel.

        Optionally filters by delivery port (UN/LOCODE).  Returns a
        ReorderSuggestion with the RFQ's line items converted to
        PredictedItem format.
        """
        query = (
            select(Rfq)
            .options(joinedload(Rfq.line_items))
            .where(
                Rfq.vessel_id == vessel_id,
                Rfq.status.in_([RfqStatus.COMPLETED, RfqStatus.AWARDED]),
            )
        )

        if port:
            query = query.where(Rfq.delivery_port == port)

        query = query.order_by(Rfq.created_at.desc()).limit(1)

        result = await self.db.execute(query)
        rfq = result.unique().scalar_one_or_none()

        if rfq is None:
            return None

        line_items = self._rfq_line_items_to_predicted(rfq.line_items)

        return ReorderSuggestion(
            source_rfq_id=rfq.id,
            source_rfq_reference=rfq.reference_number,
            created_at=rfq.created_at,
            delivery_port=rfq.delivery_port,
            line_items=line_items,
            quantity_adjustments={},
        )

    async def copy_from_rfq(
        self,
        source_rfq_id: uuid.UUID,
        voyage_days: int | None = None,
        crew_size: int | None = None,
    ) -> list[PredictedItem]:
        """Copy line items from a specific RFQ, optionally adjusting quantities.

        If ``voyage_days`` or ``crew_size`` are provided, quantities are scaled
        relative to the original RFQ's duration/crew.  Without adjustment
        parameters, quantities are copied as-is.
        """
        result = await self.db.execute(
            select(Rfq)
            .options(joinedload(Rfq.line_items))
            .where(Rfq.id == source_rfq_id)
        )
        rfq = result.unique().scalar_one_or_none()
        if rfq is None:
            raise NotFoundException(f"RFQ {source_rfq_id} not found")

        line_items = self._rfq_line_items_to_predicted(rfq.line_items)

        # Scale quantities if adjustment parameters are provided
        if voyage_days is not None or crew_size is not None:
            line_items = self._adjust_quantities(
                line_items, voyage_days=voyage_days, crew_size=crew_size
            )

        logger.info(
            "Copied %d line items from RFQ %s (adjustments: days=%s, crew=%s)",
            len(line_items),
            source_rfq_id,
            voyage_days,
            crew_size,
        )
        return line_items

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rfq_line_items_to_predicted(
        line_items: list[RfqLineItem],
    ) -> list[PredictedItem]:
        """Convert RFQ line items to PredictedItem format."""
        predicted: list[PredictedItem] = []
        for item in line_items:
            impa_code = item.impa_code or "000000"
            category_prefix = impa_code[:2] if len(impa_code) >= 2 else "00"

            predicted.append(
                PredictedItem(
                    impa_code=impa_code,
                    product_id=item.product_id,
                    description=item.description,
                    quantity=item.quantity,
                    unit=item.unit_of_measure,
                    confidence=0.9,  # high confidence — based on actual past order
                    category_prefix=category_prefix,
                )
            )
        return predicted

    @staticmethod
    def _adjust_quantities(
        items: list[PredictedItem],
        voyage_days: int | None = None,
        crew_size: int | None = None,
    ) -> list[PredictedItem]:
        """Adjust quantities using absolute scaling factors.

        NOTE: This uses fixed reference baselines (14 days, 20 crew) rather than
        the source RFQ's actual voyage/crew parameters, which are not stored on
        the Rfq model. This means adjustments are "absolute" — a request for
        7 voyage_days always produces 0.5x factor regardless of source RFQ duration.

        Future improvement: Store voyage_days and crew_size on Rfq model,
        then use source RFQ values as the reference for relative scaling.
        """
        logger.warning(
            "Reorder adjustment uses fixed reference baselines (14d/20crew), not source RFQ values"
        )

        reference_voyage_days = 14
        reference_crew_size = 20

        voyage_factor = (
            Decimal(str(voyage_days)) / Decimal(str(reference_voyage_days))
            if voyage_days is not None
            else Decimal("1")
        )
        crew_factor = (
            Decimal(str(crew_size)) / Decimal(str(reference_crew_size))
            if crew_size is not None
            else Decimal("1")
        )

        adjustment_factor = voyage_factor * crew_factor

        adjusted: list[PredictedItem] = []
        for item in items:
            new_quantity = (item.quantity * adjustment_factor).quantize(Decimal("0.01"))
            adjusted.append(
                item.model_copy(
                    update={
                        "quantity": new_quantity,
                        "confidence": 0.75,  # slightly lower confidence after adjustment
                    }
                )
            )
        return adjusted
