"""Supplier onboarding lifecycle service."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.exceptions import BusinessRuleException, ConflictException, NotFoundException
from src.models.enums import (
    KycDocumentStatus,
    KycDocumentType,
    OnboardingStatus,
    ReviewAction,
    SupplierTier,
)
from src.models.supplier_kyc_document import SupplierKycDocument
from src.models.supplier_profile import SupplierProfile
from src.models.supplier_review_log import SupplierReviewLog
from src.modules.supplier.constants import (
    TIER_DOCUMENT_REQUIREMENTS,
    VALID_STATUS_TRANSITIONS,
)

logger = logging.getLogger(__name__)

# Statuses where profile fields can still be edited
_EDITABLE_STATUSES = {
    OnboardingStatus.STARTED,
    OnboardingStatus.DOCUMENTS_PENDING,
    OnboardingStatus.REJECTED,
}

# Minimum docs needed to submit for verification (BASIC tier requirements)
_SUBMIT_REQUIRED_DOCS = TIER_DOCUMENT_REQUIREMENTS[SupplierTier.BASIC]

# Ordered list of tiers for upgrade path
_TIER_ORDER = [
    SupplierTier.PENDING,
    SupplierTier.BASIC,
    SupplierTier.VERIFIED,
    SupplierTier.PREFERRED,
    SupplierTier.PREMIUM,
]


class SupplierOnboardingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_profile(
        self,
        organization_id: uuid.UUID,
        company_name: str,
        contact_name: str,
        contact_email: str,
        contact_phone: str | None = None,
        gst_number: str | None = None,
        pan_number: str | None = None,
        cin_number: str | None = None,
        address_line1: str | None = None,
        address_line2: str | None = None,
        city: str | None = None,
        state: str | None = None,
        pincode: str | None = None,
        country: str = "India",
        categories: list | None = None,
        port_coverage: list | None = None,
    ) -> SupplierProfile:
        """Create a new supplier profile. One profile per organization."""
        existing = await self.get_profile_by_org(organization_id)
        if existing is not None:
            raise ConflictException(
                f"Supplier profile already exists for organization {organization_id}"
            )

        profile = SupplierProfile(
            organization_id=organization_id,
            company_name=company_name,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            gst_number=gst_number,
            pan_number=pan_number,
            cin_number=cin_number,
            address_line1=address_line1,
            address_line2=address_line2,
            city=city,
            state=state,
            pincode=pincode,
            country=country,
            categories=categories or [],
            port_coverage=port_coverage or [],
        )
        self.db.add(profile)
        await self.db.flush()
        logger.info("Created supplier profile %s for org %s", profile.id, organization_id)
        return profile

    async def get_profile(self, supplier_id: uuid.UUID) -> SupplierProfile:
        """Get a supplier profile by ID. Raises NotFoundException if not found."""
        result = await self.db.execute(
            select(SupplierProfile).where(SupplierProfile.id == supplier_id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            raise NotFoundException(f"Supplier profile {supplier_id} not found")
        return profile

    async def get_profile_by_org(self, organization_id: uuid.UUID) -> SupplierProfile | None:
        """Get a supplier profile by organization ID. Returns None if not found."""
        result = await self.db.execute(
            select(SupplierProfile).where(
                SupplierProfile.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()

    async def update_profile(
        self, supplier_id: uuid.UUID, **kwargs
    ) -> SupplierProfile:
        """Update supplier profile fields. Only allowed in editable statuses."""
        profile = await self.get_profile(supplier_id)

        if profile.onboarding_status not in _EDITABLE_STATUSES:
            raise BusinessRuleException(
                f"Cannot update profile in status '{profile.onboarding_status.value}'. "
                f"Profile can only be edited in statuses: {[s.value for s in _EDITABLE_STATUSES]}"
            )

        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        await self.db.flush()
        return profile

    async def list_profiles(
        self,
        tier: SupplierTier | None = None,
        status: OnboardingStatus | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[SupplierProfile], int]:
        """List supplier profiles with optional filters. Returns (items, total)."""
        query = select(SupplierProfile)
        count_query = select(func.count()).select_from(SupplierProfile)

        if tier is not None:
            query = query.where(SupplierProfile.tier == tier)
            count_query = count_query.where(SupplierProfile.tier == tier)
        if status is not None:
            query = query.where(SupplierProfile.onboarding_status == status)
            count_query = count_query.where(SupplierProfile.onboarding_status == status)
        if search:
            pattern = f"%{search}%"
            search_filter = SupplierProfile.company_name.ilike(pattern)
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(SupplierProfile.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def add_document(
        self,
        supplier_id: uuid.UUID,
        document_type: KycDocumentType,
        file_key: str,
        file_name: str,
        expiry_date: datetime | None = None,
    ) -> SupplierKycDocument:
        """Add a KYC document to a supplier profile."""
        # Verify supplier exists
        profile = await self.get_profile(supplier_id)

        # Auto-transition from STARTED to DOCUMENTS_PENDING on first document upload
        if profile.onboarding_status == OnboardingStatus.STARTED:
            profile.onboarding_status = OnboardingStatus.DOCUMENTS_PENDING
            await self.db.flush()

        document = SupplierKycDocument(
            supplier_id=supplier_id,
            document_type=document_type,
            file_key=file_key,
            file_name=file_name,
            expiry_date=expiry_date,
        )
        self.db.add(document)
        await self.db.flush()
        return document

    async def list_documents(self, supplier_id: uuid.UUID) -> list[SupplierKycDocument]:
        """List all KYC documents for a supplier."""
        # Verify supplier exists
        await self.get_profile(supplier_id)

        result = await self.db.execute(
            select(SupplierKycDocument)
            .where(SupplierKycDocument.supplier_id == supplier_id)
            .order_by(SupplierKycDocument.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_document_status(
        self,
        supplier_id: uuid.UUID,
        document_id: uuid.UUID,
        status: KycDocumentStatus,
        rejection_reason: str | None = None,
        verified_by: uuid.UUID | None = None,
    ) -> SupplierKycDocument:
        """Update the status of a KYC document."""
        result = await self.db.execute(
            select(SupplierKycDocument).where(
                SupplierKycDocument.id == document_id,
                SupplierKycDocument.supplier_id == supplier_id,
            )
        )
        document = result.scalar_one_or_none()
        if document is None:
            raise NotFoundException(
                f"Document {document_id} not found for supplier {supplier_id}"
            )

        document.status = status
        if status == KycDocumentStatus.REJECTED and rejection_reason:
            document.rejection_reason = rejection_reason
        if status == KycDocumentStatus.VERIFIED and verified_by:
            document.verified_by = verified_by
            document.verified_at = func.now()
        await self.db.flush()
        return document

    async def submit_for_verification(self, supplier_id: uuid.UUID) -> SupplierProfile:
        """Submit a supplier profile for verification.

        Validates that required BASIC-tier documents are present and transitions
        from DOCUMENTS_PENDING to DOCUMENTS_SUBMITTED.
        """
        profile = await self.get_profile(supplier_id)

        if profile.onboarding_status != OnboardingStatus.DOCUMENTS_PENDING:
            raise BusinessRuleException(
                f"Cannot submit for verification from status '{profile.onboarding_status.value}'. "
                "Profile must be in DOCUMENTS_PENDING status."
            )

        # Check required documents are uploaded (any status — they will be verified later)
        documents = await self.list_documents(supplier_id)
        uploaded_types = {doc.document_type for doc in documents}
        missing = _SUBMIT_REQUIRED_DOCS - uploaded_types
        if missing:
            missing_names = [dt.value for dt in missing]
            raise BusinessRuleException(
                f"Missing required documents for submission: {missing_names}"
            )

        profile.onboarding_status = OnboardingStatus.DOCUMENTS_SUBMITTED
        await self.db.flush()

        # Create review log entry
        log_entry = SupplierReviewLog(
            supplier_id=supplier_id,
            action=ReviewAction.SUBMITTED_FOR_REVIEW,
            from_status=OnboardingStatus.DOCUMENTS_PENDING,
            to_status=OnboardingStatus.DOCUMENTS_SUBMITTED,
        )
        self.db.add(log_entry)
        await self.db.flush()

        return profile

    async def transition_status(
        self,
        supplier_id: uuid.UUID,
        new_status: OnboardingStatus,
        reviewer_id: uuid.UUID | None = None,
        notes: str | None = None,
    ) -> SupplierProfile:
        """Transition a supplier's onboarding status. Validates the transition is allowed."""
        profile = await self.get_profile(supplier_id)
        current = profile.onboarding_status

        allowed = VALID_STATUS_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise BusinessRuleException(
                f"Cannot transition from '{current.value}' to '{new_status.value}'. "
                f"Allowed transitions: {[s.value for s in allowed]}"
            )

        old_status = current
        profile.onboarding_status = new_status

        # If approved, set tier to BASIC
        if new_status == OnboardingStatus.APPROVED and profile.tier == SupplierTier.PENDING:
            profile.tier = SupplierTier.BASIC

        await self.db.flush()

        # Determine the review action based on the new status
        action_map = {
            OnboardingStatus.MANUAL_REVIEW_IN_PROGRESS: ReviewAction.REVIEW_STARTED,
            OnboardingStatus.APPROVED: ReviewAction.APPROVED,
            OnboardingStatus.REJECTED: ReviewAction.REJECTED,
            OnboardingStatus.SUSPENDED: ReviewAction.SUSPENDED,
        }
        action = action_map.get(new_status)

        # For reactivation (SUSPENDED -> APPROVED)
        if old_status == OnboardingStatus.SUSPENDED and new_status == OnboardingStatus.APPROVED:
            action = ReviewAction.REACTIVATED

        if action:
            log_entry = SupplierReviewLog(
                supplier_id=supplier_id,
                reviewer_id=reviewer_id,
                action=action,
                from_status=old_status,
                to_status=new_status,
                notes=notes,
            )
            self.db.add(log_entry)
            await self.db.flush()

        return profile

    async def check_tier_upgrade_eligibility(self, supplier_id: uuid.UUID) -> dict:
        """Check if a supplier has met the document requirements for the next tier."""
        profile = await self.get_profile(supplier_id)
        current_tier = profile.tier

        # Find next tier
        current_index = _TIER_ORDER.index(current_tier)
        if current_index >= len(_TIER_ORDER) - 1:
            return {
                "current_tier": current_tier.value,
                "next_tier": None,
                "eligible": False,
                "missing_documents": [],
                "message": "Already at maximum tier",
            }

        next_tier = _TIER_ORDER[current_index + 1]
        required_docs = TIER_DOCUMENT_REQUIREMENTS.get(next_tier, set())

        # Get verified documents
        documents = await self.list_documents(supplier_id)
        verified_types = {
            doc.document_type
            for doc in documents
            if doc.status == KycDocumentStatus.VERIFIED
        }

        missing = required_docs - verified_types
        eligible = len(missing) == 0

        return {
            "current_tier": current_tier.value,
            "next_tier": next_tier.value,
            "eligible": eligible,
            "missing_documents": [dt.value for dt in missing],
        }

    async def request_tier_upgrade(self, supplier_id: uuid.UUID) -> SupplierProfile:
        """Request a tier upgrade for the supplier. Logs the request."""
        profile = await self.get_profile(supplier_id)

        if profile.onboarding_status != OnboardingStatus.APPROVED:
            raise BusinessRuleException(
                "Tier upgrade can only be requested when onboarding status is APPROVED"
            )

        eligibility = await self.check_tier_upgrade_eligibility(supplier_id)
        if not eligibility["eligible"]:
            raise BusinessRuleException(
                f"Not eligible for tier upgrade. Missing documents: {eligibility['missing_documents']}"
            )

        current_index = _TIER_ORDER.index(profile.tier)
        next_tier = _TIER_ORDER[current_index + 1]

        log_entry = SupplierReviewLog(
            supplier_id=supplier_id,
            action=ReviewAction.TIER_UPGRADE_REQUESTED,
            from_status=profile.onboarding_status,
            to_status=profile.onboarding_status,
            notes=f"Requested upgrade from {profile.tier.value} to {next_tier.value}",
        )
        self.db.add(log_entry)
        await self.db.flush()

        return profile
