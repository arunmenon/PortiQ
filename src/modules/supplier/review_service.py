"""Supplier review and approval service."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import BusinessRuleException
from src.models.enums import OnboardingStatus, ReviewAction
from src.models.supplier_profile import SupplierProfile
from src.models.supplier_review_log import SupplierReviewLog
from src.modules.supplier.onboarding_service import SupplierOnboardingService

logger = logging.getLogger(__name__)

# Map review actions to target onboarding statuses
_ACTION_STATUS_MAP = {
    ReviewAction.APPROVED: OnboardingStatus.APPROVED,
    ReviewAction.REJECTED: OnboardingStatus.REJECTED,
    ReviewAction.SUSPENDED: OnboardingStatus.SUSPENDED,
    ReviewAction.REACTIVATED: OnboardingStatus.APPROVED,
    ReviewAction.REVIEW_STARTED: OnboardingStatus.MANUAL_REVIEW_IN_PROGRESS,
}

# Statuses that are eligible for pending review listing
_PENDING_REVIEW_STATUSES = {
    OnboardingStatus.MANUAL_REVIEW_PENDING,
    OnboardingStatus.DOCUMENTS_SUBMITTED,
}


class SupplierReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._onboarding = SupplierOnboardingService(db)

    async def submit_review(
        self,
        supplier_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        action: ReviewAction,
        notes: str | None = None,
    ) -> SupplierProfile:
        """Submit a review decision for a supplier.

        Maps review actions to onboarding status transitions and delegates to
        the onboarding service for state machine enforcement.
        """
        target_status = _ACTION_STATUS_MAP.get(action)
        if target_status is None:
            raise BusinessRuleException(
                f"Review action '{action.value}' is not a valid review decision. "
                f"Valid actions: {[a.value for a in _ACTION_STATUS_MAP]}"
            )

        return await self._onboarding.transition_status(
            supplier_id=supplier_id,
            new_status=target_status,
            reviewer_id=reviewer_id,
            notes=notes,
        )

    async def get_pending_reviews(
        self, limit: int = 20, offset: int = 0
    ) -> tuple[list[SupplierProfile], int]:
        """Get supplier profiles that are awaiting review."""
        base_filter = SupplierProfile.onboarding_status.in_(_PENDING_REVIEW_STATUSES)

        count_result = await self.db.execute(
            select(func.count()).select_from(SupplierProfile).where(base_filter)
        )
        total = count_result.scalar() or 0

        query = (
            select(SupplierProfile)
            .where(base_filter)
            .order_by(SupplierProfile.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_review_history(
        self, supplier_id: uuid.UUID
    ) -> list[SupplierReviewLog]:
        """Get the full review history for a supplier, newest first."""
        # Verify supplier exists
        await self._onboarding.get_profile(supplier_id)

        result = await self.db.execute(
            select(SupplierReviewLog)
            .where(SupplierReviewLog.supplier_id == supplier_id)
            .order_by(SupplierReviewLog.created_at.desc())
        )
        return list(result.scalars().all())
