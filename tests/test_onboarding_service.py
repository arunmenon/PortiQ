"""Unit tests for SupplierOnboardingService."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.exceptions import BusinessRuleException, ConflictException, NotFoundException
from src.models.enums import (
    KycDocumentStatus,
    KycDocumentType,
    OnboardingStatus,
    SupplierTier,
)
from src.modules.supplier.onboarding_service import SupplierOnboardingService


def _make_profile(
    org_id: uuid.UUID | None = None,
    tier: SupplierTier = SupplierTier.PENDING,
    status: OnboardingStatus = OnboardingStatus.STARTED,
):
    profile = MagicMock()
    profile.id = uuid.uuid4()
    profile.organization_id = org_id or uuid.uuid4()
    profile.tier = tier
    profile.onboarding_status = status
    profile.company_name = "Maritime Supplies Ltd"
    profile.contact_name = "John Doe"
    profile.contact_email = "john@maritime.com"
    profile.contact_phone = None
    profile.categories = []
    profile.port_coverage = []
    profile.verification_results = {}
    profile.country = "India"
    profile.created_at = "2026-01-01T00:00:00Z"
    profile.updated_at = "2026-01-01T00:00:00Z"
    return profile


def _make_document(
    supplier_id: uuid.UUID,
    doc_type: KycDocumentType = KycDocumentType.GST_CERTIFICATE,
    status: KycDocumentStatus = KycDocumentStatus.PENDING,
):
    doc = MagicMock()
    doc.id = uuid.uuid4()
    doc.supplier_id = supplier_id
    doc.document_type = doc_type
    doc.file_key = f"uploads/{doc_type.value.lower()}.pdf"
    doc.file_name = f"{doc_type.value.lower()}.pdf"
    doc.status = status
    doc.verified_at = None
    doc.verified_by = None
    doc.expiry_date = None
    doc.rejection_reason = None
    doc.created_at = "2026-01-01T00:00:00Z"
    doc.updated_at = "2026-01-01T00:00:00Z"
    return doc


@pytest.mark.asyncio
async def test_create_profile():
    """Creating a profile with valid data succeeds."""
    org_id = uuid.uuid4()

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    # get_profile_by_org returns None (no existing profile)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock

    svc = SupplierOnboardingService(db)
    profile = await svc.create_profile(
        organization_id=org_id,
        company_name="Maritime Supplies Ltd",
        contact_name="John Doe",
        contact_email="john@maritime.com",
    )

    assert db.add.call_count == 1
    assert db.flush.call_count == 1


@pytest.mark.asyncio
async def test_create_duplicate_profile():
    """Creating a second profile for the same org raises ConflictException."""
    org_id = uuid.uuid4()
    existing = _make_profile(org_id=org_id)

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = existing
    db.execute.return_value = result_mock

    svc = SupplierOnboardingService(db)
    with pytest.raises(ConflictException, match="already exists"):
        await svc.create_profile(
            organization_id=org_id,
            company_name="Another Name",
            contact_name="Jane Doe",
            contact_email="jane@test.com",
        )


@pytest.mark.asyncio
async def test_add_document():
    """Adding a document to an existing supplier succeeds."""
    profile = _make_profile(status=OnboardingStatus.STARTED)

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    # First execute: get_profile (for add_document -> get_profile)
    profile_result = MagicMock()
    profile_result.scalar_one_or_none.return_value = profile
    db.execute.return_value = profile_result

    svc = SupplierOnboardingService(db)
    document = await svc.add_document(
        supplier_id=profile.id,
        document_type=KycDocumentType.GST_CERTIFICATE,
        file_key="uploads/gst.pdf",
        file_name="gst.pdf",
    )

    # Profile status should be auto-transitioned + document added
    assert db.add.call_count == 1
    # Two flushes: one for status update, one for document insert
    assert db.flush.call_count == 2


@pytest.mark.asyncio
async def test_submit_for_verification_missing_docs():
    """Submitting for verification without required docs raises BusinessRuleException."""
    profile = _make_profile(status=OnboardingStatus.DOCUMENTS_PENDING)

    db = AsyncMock()
    db.flush = AsyncMock()

    # First execute: get_profile
    profile_result = MagicMock()
    profile_result.scalar_one_or_none.return_value = profile

    # Second execute: list_documents -> empty list (no docs uploaded)
    docs_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    docs_result.scalars.return_value = scalars_mock

    # Third execute: get_profile again (for list_documents -> get_profile check)
    profile_result2 = MagicMock()
    profile_result2.scalar_one_or_none.return_value = profile

    db.execute.side_effect = [profile_result, profile_result2, docs_result]

    svc = SupplierOnboardingService(db)
    with pytest.raises(BusinessRuleException, match="Missing required documents"):
        await svc.submit_for_verification(profile.id)


@pytest.mark.asyncio
async def test_status_transition_valid():
    """A valid status transition succeeds."""
    profile = _make_profile(
        status=OnboardingStatus.MANUAL_REVIEW_IN_PROGRESS,
        tier=SupplierTier.PENDING,
    )

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    profile_result = MagicMock()
    profile_result.scalar_one_or_none.return_value = profile
    db.execute.return_value = profile_result

    svc = SupplierOnboardingService(db)
    result = await svc.transition_status(
        supplier_id=profile.id,
        new_status=OnboardingStatus.APPROVED,
        reviewer_id=uuid.uuid4(),
        notes="All documents verified",
    )

    # Status should be updated
    assert profile.onboarding_status == OnboardingStatus.APPROVED
    # Tier should be upgraded from PENDING to BASIC on approval
    assert profile.tier == SupplierTier.BASIC
    # Review log should be added
    assert db.add.call_count == 1


@pytest.mark.asyncio
async def test_status_transition_invalid():
    """An invalid status transition raises BusinessRuleException."""
    profile = _make_profile(status=OnboardingStatus.STARTED)

    db = AsyncMock()
    profile_result = MagicMock()
    profile_result.scalar_one_or_none.return_value = profile
    db.execute.return_value = profile_result

    svc = SupplierOnboardingService(db)
    with pytest.raises(BusinessRuleException, match="Cannot transition"):
        await svc.transition_status(
            supplier_id=profile.id,
            new_status=OnboardingStatus.APPROVED,
        )


@pytest.mark.asyncio
async def test_list_profiles_with_filters():
    """Listing profiles with filters returns correct structure."""
    profile1 = _make_profile(tier=SupplierTier.BASIC, status=OnboardingStatus.APPROVED)
    profile2 = _make_profile(tier=SupplierTier.BASIC, status=OnboardingStatus.APPROVED)

    db = AsyncMock()

    # First execute: count query
    count_result = MagicMock()
    count_result.scalar.return_value = 2

    # Second execute: items query
    items_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [profile1, profile2]
    items_result.scalars.return_value = scalars_mock

    db.execute.side_effect = [count_result, items_result]

    svc = SupplierOnboardingService(db)
    items, total = await svc.list_profiles(
        tier=SupplierTier.BASIC,
        status=OnboardingStatus.APPROVED,
        limit=10,
        offset=0,
    )

    assert total == 2
    assert len(items) == 2
