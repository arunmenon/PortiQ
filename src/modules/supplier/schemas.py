"""Pydantic v2 schemas for supplier onboarding API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import (
    KycDocumentStatus,
    KycDocumentType,
    OnboardingStatus,
    ReviewAction,
    SupplierTier,
)


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class SupplierProfileCreate(BaseModel):
    organization_id: uuid.UUID
    company_name: str = Field(..., min_length=1, max_length=255)
    contact_name: str = Field(..., min_length=1, max_length=255)
    contact_email: str = Field(..., min_length=1, max_length=255)
    contact_phone: str | None = Field(None, max_length=20)
    gst_number: str | None = Field(None, max_length=20)
    pan_number: str | None = Field(None, max_length=20)
    cin_number: str | None = Field(None, max_length=25)
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    pincode: str | None = Field(None, max_length=10)
    country: str = Field("India", max_length=100)
    categories: list[str] = Field(default_factory=list)
    port_coverage: list[str] = Field(default_factory=list)


class SupplierProfileUpdate(BaseModel):
    company_name: str | None = Field(None, min_length=1, max_length=255)
    contact_name: str | None = Field(None, min_length=1, max_length=255)
    contact_email: str | None = Field(None, min_length=1, max_length=255)
    contact_phone: str | None = Field(None, max_length=20)
    gst_number: str | None = Field(None, max_length=20)
    pan_number: str | None = Field(None, max_length=20)
    cin_number: str | None = Field(None, max_length=25)
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    pincode: str | None = Field(None, max_length=10)
    country: str | None = Field(None, max_length=100)
    categories: list[str] | None = None
    port_coverage: list[str] | None = None


class KycDocumentCreate(BaseModel):
    document_type: KycDocumentType
    file_key: str = Field(..., min_length=1, max_length=512)
    file_name: str = Field(..., min_length=1, max_length=255)
    expiry_date: datetime | None = None


class KycDocumentUpdate(BaseModel):
    status: KycDocumentStatus
    rejection_reason: str | None = Field(None, max_length=500)


class ReviewRequest(BaseModel):
    action: ReviewAction
    notes: str | None = None


class StatusUpdateRequest(BaseModel):
    status: OnboardingStatus
    notes: str | None = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class SupplierProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    tier: SupplierTier
    onboarding_status: OnboardingStatus
    company_name: str
    contact_name: str
    contact_email: str
    contact_phone: str | None = None
    gst_number: str | None = None
    pan_number: str | None = None
    cin_number: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    country: str
    categories: list = Field(default_factory=list)
    port_coverage: list = Field(default_factory=list)
    verification_results: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    organization_name: str | None = None


class SupplierListResponse(BaseModel):
    items: list[SupplierProfileResponse]
    total: int
    limit: int
    offset: int


class KycDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supplier_id: uuid.UUID
    document_type: KycDocumentType
    file_key: str
    file_name: str
    status: KycDocumentStatus
    verified_at: datetime | None = None
    verified_by: uuid.UUID | None = None
    expiry_date: datetime | None = None
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class ReviewLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supplier_id: uuid.UUID
    reviewer_id: uuid.UUID | None = None
    action: ReviewAction
    from_status: OnboardingStatus
    to_status: OnboardingStatus
    notes: str | None = None
    created_at: datetime
    reviewer_name: str | None = None


class TierCapabilitiesResponse(BaseModel):
    tier: SupplierTier
    max_quotes: int | None
    can_bid_rfq: bool
    financing_eligible: bool
    visibility: str
    commission_percent: int
    payment_terms: str | None
