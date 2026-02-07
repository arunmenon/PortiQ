"""Supplier onboarding API router."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.exceptions import ForbiddenException
from src.models.enums import OnboardingStatus, SupplierTier
from src.modules.supplier.constants import TIER_CAPABILITIES
from src.modules.supplier.onboarding_service import SupplierOnboardingService
from src.modules.supplier.review_service import SupplierReviewService
from src.modules.supplier.schemas import (
    KycDocumentCreate,
    KycDocumentResponse,
    KycDocumentUpdate,
    ReviewLogResponse,
    ReviewRequest,
    StatusUpdateRequest,
    SupplierListResponse,
    SupplierProfileCreate,
    SupplierProfileResponse,
    SupplierProfileUpdate,
    TierCapabilitiesResponse,
)
from src.modules.tenancy.auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_admin(user: AuthenticatedUser) -> None:
    """Raise ForbiddenException unless the user is a platform admin."""
    if not user.is_platform_admin:
        raise ForbiddenException("This action requires platform admin privileges")


# ---------------------------------------------------------------------------
# Supplier profile endpoints
# ---------------------------------------------------------------------------


@router.post("/", response_model=SupplierProfileResponse, status_code=201)
async def create_supplier_profile(
    body: SupplierProfileCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start supplier onboarding by creating a profile."""
    svc = SupplierOnboardingService(db)
    profile = await svc.create_profile(
        organization_id=body.organization_id,
        company_name=body.company_name,
        contact_name=body.contact_name,
        contact_email=body.contact_email,
        contact_phone=body.contact_phone,
        gst_number=body.gst_number,
        pan_number=body.pan_number,
        cin_number=body.cin_number,
        address_line1=body.address_line1,
        address_line2=body.address_line2,
        city=body.city,
        state=body.state,
        pincode=body.pincode,
        country=body.country,
        categories=body.categories,
        port_coverage=body.port_coverage,
    )
    return SupplierProfileResponse.model_validate(profile)


@router.get("/", response_model=SupplierListResponse)
async def list_suppliers(
    tier: SupplierTier | None = Query(None),
    status: OnboardingStatus | None = Query(None),
    search: str | None = Query(None, max_length=255),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List supplier profiles with optional filters."""
    svc = SupplierOnboardingService(db)
    items, total = await svc.list_profiles(
        tier=tier, status=status, search=search, limit=limit, offset=offset
    )
    return SupplierListResponse(
        items=[SupplierProfileResponse.model_validate(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/pending-reviews", response_model=SupplierListResponse)
async def get_pending_reviews(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get supplier profiles awaiting review. Platform admins only."""
    _require_admin(user)
    svc = SupplierReviewService(db)
    items, total = await svc.get_pending_reviews(limit=limit, offset=offset)
    return SupplierListResponse(
        items=[SupplierProfileResponse.model_validate(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{supplier_id}", response_model=SupplierProfileResponse)
async def get_supplier_profile(
    supplier_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single supplier profile by ID."""
    svc = SupplierOnboardingService(db)
    profile = await svc.get_profile(supplier_id)
    return SupplierProfileResponse.model_validate(profile)


@router.patch("/{supplier_id}", response_model=SupplierProfileResponse)
async def update_supplier_profile(
    supplier_id: uuid.UUID,
    body: SupplierProfileUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a supplier profile. Only allowed in editable statuses."""
    svc = SupplierOnboardingService(db)
    profile = await svc.update_profile(
        supplier_id, **body.model_dump(exclude_unset=True)
    )
    return SupplierProfileResponse.model_validate(profile)


# ---------------------------------------------------------------------------
# KYC document endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{supplier_id}/documents",
    response_model=KycDocumentResponse,
    status_code=201,
)
async def add_document(
    supplier_id: uuid.UUID,
    body: KycDocumentCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a KYC document to a supplier profile."""
    svc = SupplierOnboardingService(db)
    document = await svc.add_document(
        supplier_id=supplier_id,
        document_type=body.document_type,
        file_key=body.file_key,
        file_name=body.file_name,
        expiry_date=body.expiry_date,
    )
    return KycDocumentResponse.model_validate(document)


@router.get("/{supplier_id}/documents", response_model=list[KycDocumentResponse])
async def list_documents(
    supplier_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all KYC documents for a supplier."""
    svc = SupplierOnboardingService(db)
    documents = await svc.list_documents(supplier_id)
    return [KycDocumentResponse.model_validate(d) for d in documents]


@router.patch(
    "/{supplier_id}/documents/{document_id}",
    response_model=KycDocumentResponse,
)
async def update_document_status(
    supplier_id: uuid.UUID,
    document_id: uuid.UUID,
    body: KycDocumentUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the status of a KYC document."""
    svc = SupplierOnboardingService(db)
    document = await svc.update_document_status(
        supplier_id=supplier_id,
        document_id=document_id,
        status=body.status,
        rejection_reason=body.rejection_reason,
        verified_by=user.id,
    )
    return KycDocumentResponse.model_validate(document)


# ---------------------------------------------------------------------------
# Verification and review endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{supplier_id}/submit-for-verification",
    response_model=SupplierProfileResponse,
)
async def submit_for_verification(
    supplier_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a supplier profile for verification."""
    svc = SupplierOnboardingService(db)
    profile = await svc.submit_for_verification(supplier_id)
    return SupplierProfileResponse.model_validate(profile)


@router.post("/{supplier_id}/review", response_model=SupplierProfileResponse)
async def submit_review(
    supplier_id: uuid.UUID,
    body: ReviewRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a review decision for a supplier. Platform admins only."""
    _require_admin(user)
    svc = SupplierReviewService(db)
    profile = await svc.submit_review(
        supplier_id=supplier_id,
        reviewer_id=user.id,
        action=body.action,
        notes=body.notes,
    )
    return SupplierProfileResponse.model_validate(profile)


@router.get("/{supplier_id}/review-log", response_model=list[ReviewLogResponse])
async def get_review_log(
    supplier_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get review history for a supplier."""
    svc = SupplierReviewService(db)
    logs = await svc.get_review_history(supplier_id)
    return [ReviewLogResponse.model_validate(log) for log in logs]


# ---------------------------------------------------------------------------
# Tier management endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{supplier_id}/request-tier-upgrade",
    response_model=SupplierProfileResponse,
)
async def request_tier_upgrade(
    supplier_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request a tier upgrade for a supplier."""
    svc = SupplierOnboardingService(db)
    profile = await svc.request_tier_upgrade(supplier_id)
    return SupplierProfileResponse.model_validate(profile)


@router.get("/{supplier_id}/tier-capabilities", response_model=TierCapabilitiesResponse)
async def get_tier_capabilities(
    supplier_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current tier capabilities for a supplier."""
    svc = SupplierOnboardingService(db)
    profile = await svc.get_profile(supplier_id)
    capabilities = TIER_CAPABILITIES[profile.tier]
    return TierCapabilitiesResponse(tier=profile.tier, **capabilities)


@router.put("/{supplier_id}/status", response_model=SupplierProfileResponse)
async def update_status(
    supplier_id: uuid.UUID,
    body: StatusUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Suspend or reactivate a supplier. Platform admins only."""
    _require_admin(user)
    svc = SupplierOnboardingService(db)
    profile = await svc.transition_status(
        supplier_id=supplier_id,
        new_status=body.status,
        reviewer_id=user.id,
        notes=body.notes,
    )
    return SupplierProfileResponse.model_validate(profile)
