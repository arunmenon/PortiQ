"""Unit tests for supplier router endpoints."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.database.session import get_db
from src.models.enums import (
    KycDocumentStatus,
    KycDocumentType,
    OnboardingStatus,
    ReviewAction,
    SupplierTier,
)
from src.modules.supplier.router import router
from src.modules.tenancy.auth import AuthenticatedUser, get_current_user

# ── Test app setup ────────────────────────────────────────────────────────

app = FastAPI()
app.include_router(router)

_test_user = AuthenticatedUser(
    id=uuid.uuid4(),
    email="admin@portiq.com",
    organization_id=uuid.uuid4(),
    organization_type="PLATFORM",
    role="super_admin",
    is_platform_admin=True,
)

_mock_db = AsyncMock()


async def _override_get_current_user():
    return _test_user


async def _override_get_db():
    yield _mock_db


app.dependency_overrides[get_current_user] = _override_get_current_user
app.dependency_overrides[get_db] = _override_get_db

client = TestClient(app)


def _make_mock_profile(
    supplier_id: uuid.UUID | None = None,
    org_id: uuid.UUID | None = None,
):
    profile = MagicMock()
    profile.id = supplier_id or uuid.uuid4()
    profile.organization_id = org_id or uuid.uuid4()
    profile.tier = SupplierTier.PENDING
    profile.onboarding_status = OnboardingStatus.STARTED
    profile.company_name = "Test Supplies Ltd"
    profile.contact_name = "Test User"
    profile.contact_email = "test@supplies.com"
    profile.contact_phone = None
    profile.gst_number = None
    profile.pan_number = None
    profile.cin_number = None
    profile.address_line1 = None
    profile.address_line2 = None
    profile.city = None
    profile.state = None
    profile.pincode = None
    profile.country = "India"
    profile.categories = []
    profile.port_coverage = []
    profile.verification_results = {}
    profile.created_at = "2026-01-01T00:00:00Z"
    profile.updated_at = "2026-01-01T00:00:00Z"
    profile.organization_name = None
    return profile


def _make_mock_document(supplier_id: uuid.UUID):
    doc = MagicMock()
    doc.id = uuid.uuid4()
    doc.supplier_id = supplier_id
    doc.document_type = KycDocumentType.GST_CERTIFICATE
    doc.file_key = "uploads/gst.pdf"
    doc.file_name = "gst.pdf"
    doc.status = KycDocumentStatus.PENDING
    doc.verified_at = None
    doc.verified_by = None
    doc.expiry_date = None
    doc.rejection_reason = None
    doc.created_at = "2026-01-01T00:00:00Z"
    doc.updated_at = "2026-01-01T00:00:00Z"
    return doc


@patch("src.modules.supplier.router.SupplierOnboardingService")
def test_create_supplier_endpoint(mock_svc_cls):
    """POST /suppliers/ creates a supplier profile."""
    mock_profile = _make_mock_profile()
    mock_svc = AsyncMock()
    mock_svc.create_profile.return_value = mock_profile
    mock_svc_cls.return_value = mock_svc

    response = client.post(
        "/suppliers/",
        json={
            "organization_id": str(uuid.uuid4()),
            "company_name": "Test Supplies Ltd",
            "contact_name": "Test User",
            "contact_email": "test@supplies.com",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["company_name"] == "Test Supplies Ltd"
    mock_svc.create_profile.assert_called_once()


@patch("src.modules.supplier.router.SupplierOnboardingService")
def test_list_suppliers_endpoint(mock_svc_cls):
    """GET /suppliers/ returns paginated list."""
    mock_profile = _make_mock_profile()
    mock_svc = AsyncMock()
    mock_svc.list_profiles.return_value = ([mock_profile], 1)
    mock_svc_cls.return_value = mock_svc

    response = client.get("/suppliers/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


@patch("src.modules.supplier.router.SupplierOnboardingService")
def test_get_supplier_endpoint(mock_svc_cls):
    """GET /suppliers/{id} returns a single profile."""
    mock_profile = _make_mock_profile()
    mock_svc = AsyncMock()
    mock_svc.get_profile.return_value = mock_profile
    mock_svc_cls.return_value = mock_svc

    response = client.get(f"/suppliers/{mock_profile.id}")
    assert response.status_code == 200
    assert response.json()["company_name"] == "Test Supplies Ltd"


@patch("src.modules.supplier.router.SupplierOnboardingService")
def test_update_supplier_endpoint(mock_svc_cls):
    """PATCH /suppliers/{id} updates the profile."""
    mock_profile = _make_mock_profile()
    mock_profile.company_name = "Updated Name"
    mock_svc = AsyncMock()
    mock_svc.update_profile.return_value = mock_profile
    mock_svc_cls.return_value = mock_svc

    response = client.patch(
        f"/suppliers/{mock_profile.id}",
        json={"company_name": "Updated Name"},
    )
    assert response.status_code == 200
    assert response.json()["company_name"] == "Updated Name"


@patch("src.modules.supplier.router.SupplierOnboardingService")
def test_add_document_endpoint(mock_svc_cls):
    """POST /suppliers/{id}/documents adds a KYC document."""
    supplier_id = uuid.uuid4()
    mock_doc = _make_mock_document(supplier_id)
    mock_svc = AsyncMock()
    mock_svc.add_document.return_value = mock_doc
    mock_svc_cls.return_value = mock_svc

    response = client.post(
        f"/suppliers/{supplier_id}/documents",
        json={
            "document_type": "GST_CERTIFICATE",
            "file_key": "uploads/gst.pdf",
            "file_name": "gst.pdf",
        },
    )
    assert response.status_code == 201
    assert response.json()["document_type"] == "GST_CERTIFICATE"


@patch("src.modules.supplier.router.SupplierReviewService")
def test_submit_review_endpoint(mock_svc_cls):
    """POST /suppliers/{id}/review submits a review decision."""
    mock_profile = _make_mock_profile()
    mock_profile.onboarding_status = OnboardingStatus.APPROVED
    mock_profile.tier = SupplierTier.BASIC

    mock_svc = AsyncMock()
    mock_svc.submit_review.return_value = mock_profile
    mock_svc_cls.return_value = mock_svc

    response = client.post(
        f"/suppliers/{mock_profile.id}/review",
        json={"action": "APPROVED", "notes": "All good"},
    )
    assert response.status_code == 200
    assert response.json()["onboarding_status"] == "APPROVED"
