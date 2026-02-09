"""DedupService — detect duplicate line items across document extractions."""

from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.document_extraction import DocumentExtraction, ExtractedLineItem
from src.modules.document_ai.schemas import DuplicateGroup, DuplicateGroupItem


class DedupService:
    """Detect potential duplicate line items across extractions for the same RFQ."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def find_duplicates(
        self,
        extraction_id: uuid.UUID,
        rfq_id: uuid.UUID,
    ) -> list[DuplicateGroup]:
        """Find potential duplicates across all extractions for the same RFQ.

        Groups items by matched_impa_code. If the same IMPA code appears in
        multiple documents with similar quantities (within 50%), it is flagged
        as a potential duplicate.

        Returns a list of DuplicateGroup objects with items and suggested
        merge quantity.
        """
        # Get all extractions for the RFQ
        extractions_result = await self.db.execute(
            select(DocumentExtraction).where(
                DocumentExtraction.rfq_id == rfq_id
            )
        )
        extractions = list(extractions_result.scalars().all())
        extraction_ids = [e.id for e in extractions]

        if not extraction_ids:
            return []

        # Build a filename map for display
        filename_map = {e.id: e.filename for e in extractions}

        # Get all matched line items across these extractions
        items_result = await self.db.execute(
            select(ExtractedLineItem)
            .where(
                ExtractedLineItem.extraction_id.in_(extraction_ids),
                ExtractedLineItem.matched_impa_code.isnot(None),
            )
            .order_by(ExtractedLineItem.extraction_id, ExtractedLineItem.line_number)
        )
        all_items = list(items_result.scalars().all())

        # Group by matched IMPA code
        impa_groups: dict[str, list[ExtractedLineItem]] = defaultdict(list)
        for item in all_items:
            if item.matched_impa_code:
                impa_groups[item.matched_impa_code].append(item)

        duplicate_groups: list[DuplicateGroup] = []

        for impa_code, items in impa_groups.items():
            # Only flag as duplicate if the same IMPA appears in multiple extractions
            extraction_set = {item.extraction_id for item in items}
            if len(extraction_set) < 2:
                continue

            # Check if quantities are similar (within 50%)
            quantities = [
                float(item.detected_quantity)
                for item in items
                if item.detected_quantity is not None
            ]

            if quantities and len(quantities) >= 2:
                max_qty = max(quantities)
                min_qty = min(quantities)
                # Only flag if quantities are within 50% of each other
                if max_qty > 0 and (max_qty - min_qty) / max_qty > 0.50:
                    continue

            # Build duplicate group
            group_items = [
                DuplicateGroupItem(
                    extraction_id=item.extraction_id,
                    item_id=item.id,
                    quantity=Decimal(str(item.detected_quantity))
                    if item.detected_quantity is not None
                    else None,
                    source_filename=filename_map.get(item.extraction_id, "unknown"),
                )
                for item in items
            ]

            # Suggested merge quantity: max of all quantities
            suggested_quantity = (
                Decimal(str(max(quantities))) if quantities else Decimal("0")
            )

            duplicate_groups.append(
                DuplicateGroup(
                    impa_code=impa_code,
                    items=group_items,
                    suggested_merge_quantity=suggested_quantity,
                )
            )

        return duplicate_groups
