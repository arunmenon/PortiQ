"""Unit tests for OrganizationService."""

import uuid
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from src.exceptions import ConflictException, NotFoundException
from src.models.enums import MembershipStatus, OrganizationStatus, OrganizationType
from src.modules.tenancy.organization_service import OrganizationService


def _make_org(
    name: str = "Acme Shipping",
    slug: str = "acme-shipping",
    org_type: OrganizationType = OrganizationType.BUYER,
):
    org = MagicMock()
    org.id = uuid.uuid4()
    org.name = name
    org.type = org_type
    org.slug = slug
    org.legal_name = None
    org.status = OrganizationStatus.ACTIVE
    org.primary_email = None
    org.website = None
    org.settings = {}
    org.created_at = "2026-01-01T00:00:00Z"
    return org


def _make_role(name: str = "buyer_admin", org_type: OrganizationType = OrganizationType.BUYER):
    role = MagicMock()
    role.id = uuid.uuid4()
    role.name = name
    role.display_name = name.replace("_", " ").title()
    role.organization_type = org_type
    role.permissions = ["*"]
    role.is_system = True
    return role


@pytest.mark.asyncio
async def test_create_organization_creates_org_and_admin_membership():
    admin_role = _make_role()
    creator_id = uuid.uuid4()

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    # First execute: check slug doesn't exist -> None
    # (only called if slug is provided; without slug, generate_slug is called)
    # For this test, provide explicit slug
    slug_result = MagicMock()
    slug_result.scalar_one_or_none.return_value = None  # slug available

    # Second execute (after flush): find admin role
    role_result = MagicMock()
    role_result.scalar_one_or_none.return_value = admin_role

    db.execute.side_effect = [slug_result, role_result]

    svc = OrganizationService(db)
    org = await svc.create_organization(
        name="Test Org",
        org_type=OrganizationType.BUYER,
        creator_user_id=creator_id,
        slug="test-org",
    )

    # Should have added the org and the membership
    assert db.add.call_count == 2
    assert db.flush.call_count == 2


@pytest.mark.asyncio
async def test_create_organization_rejects_duplicate_slug():
    existing_org = _make_org(slug="taken-slug")

    db = AsyncMock()
    slug_result = MagicMock()
    slug_result.scalar_one_or_none.return_value = existing_org
    db.execute.return_value = slug_result

    svc = OrganizationService(db)
    with pytest.raises(ConflictException):
        await svc.create_organization(
            name="Another Org",
            org_type=OrganizationType.BUYER,
            creator_user_id=uuid.uuid4(),
            slug="taken-slug",
        )


@pytest.mark.asyncio
async def test_get_organization_raises_not_found():
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock

    svc = OrganizationService(db)
    with pytest.raises(NotFoundException):
        await svc.get_organization(uuid.uuid4())


@pytest.mark.asyncio
async def test_list_user_organizations_returns_correct_data():
    org = _make_org()
    role = _make_role()
    membership = MagicMock()
    membership.organization = org
    membership.role = role
    membership.joined_at = "2026-01-01T00:00:00Z"

    db = AsyncMock()
    result_mock = MagicMock()
    # unique().scalars().all() chain
    unique_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [membership]
    unique_mock.scalars.return_value = scalars_mock
    result_mock.unique.return_value = unique_mock
    db.execute.return_value = result_mock

    svc = OrganizationService(db)
    items = await svc.list_user_organizations(uuid.uuid4())

    assert len(items) == 1
    assert items[0]["organization"] == org
    assert items[0]["role"] == role
    assert items[0]["membership"] == membership


@pytest.mark.asyncio
async def test_generate_slug_creates_url_friendly_slug():
    db = AsyncMock()
    # First call: check slug "acme-shipping" -> None (available)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock

    svc = OrganizationService(db)
    slug = await svc.generate_slug("Acme Shipping Co.")
    assert slug == "acme-shipping-co"
    assert " " not in slug
    assert slug == slug.lower()


@pytest.mark.asyncio
async def test_generate_slug_handles_duplicates_with_counter():
    existing_org = _make_org(slug="acme")

    db = AsyncMock()

    # First call: "acme" exists
    result_exists = MagicMock()
    result_exists.scalar_one_or_none.return_value = existing_org

    # Second call: "acme-1" exists
    result_exists_1 = MagicMock()
    result_exists_1.scalar_one_or_none.return_value = existing_org

    # Third call: "acme-2" is free
    result_free = MagicMock()
    result_free.scalar_one_or_none.return_value = None

    db.execute.side_effect = [result_exists, result_exists_1, result_free]

    svc = OrganizationService(db)
    slug = await svc.generate_slug("Acme")
    assert slug == "acme-2"


@pytest.mark.asyncio
async def test_update_organization_updates_fields():
    org = _make_org()

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = org
    db.execute.return_value = result_mock
    db.flush = AsyncMock()

    svc = OrganizationService(db)
    updated = await svc.update_organization(org.id, name="New Name", website="https://new.com")

    assert updated.name == "New Name"
    assert updated.website == "https://new.com"
