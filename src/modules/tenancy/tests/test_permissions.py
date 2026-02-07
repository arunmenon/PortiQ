"""Unit tests for PermissionService."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.enums import MembershipStatus, OrganizationType
from src.modules.tenancy.permissions import PermissionService


def _make_role(permissions: list[str], name: str = "buyer_admin"):
    role = MagicMock()
    role.id = uuid.uuid4()
    role.name = name
    role.display_name = name.replace("_", " ").title()
    role.organization_type = OrganizationType.BUYER
    role.permissions = permissions
    role.is_system = True
    return role


def _make_membership(role_id: uuid.UUID, status=MembershipStatus.ACTIVE):
    membership = MagicMock()
    membership.id = uuid.uuid4()
    membership.user_id = uuid.uuid4()
    membership.organization_id = uuid.uuid4()
    membership.role_id = role_id
    membership.status = status
    return membership


def _mock_db_returning(value):
    """Create a mock AsyncSession whose execute returns a result with scalar_one_or_none."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    db.execute.return_value = result
    return db


@pytest.mark.asyncio
async def test_check_permission_returns_true_for_wildcard():
    role = _make_role(["*"])
    membership = _make_membership(role.id)

    db = AsyncMock()
    # First call: validate_membership -> returns membership
    membership_result = MagicMock()
    membership_result.scalar_one_or_none.return_value = membership
    # Second call: get role -> returns role
    role_result = MagicMock()
    role_result.scalar_one_or_none.return_value = role

    db.execute.side_effect = [membership_result, role_result]

    svc = PermissionService(db)
    result = await svc.check_permission(
        membership.user_id, membership.organization_id, "anything.here"
    )
    assert result is True


@pytest.mark.asyncio
async def test_check_permission_returns_true_for_matching_permission():
    role = _make_role(["users.manage", "organization.view"])
    membership = _make_membership(role.id)

    db = AsyncMock()
    membership_result = MagicMock()
    membership_result.scalar_one_or_none.return_value = membership
    role_result = MagicMock()
    role_result.scalar_one_or_none.return_value = role

    db.execute.side_effect = [membership_result, role_result]

    svc = PermissionService(db)
    result = await svc.check_permission(
        membership.user_id, membership.organization_id, "users.manage"
    )
    assert result is True


@pytest.mark.asyncio
async def test_check_permission_returns_false_for_missing_permission():
    role = _make_role(["organization.view"])
    membership = _make_membership(role.id)

    db = AsyncMock()
    membership_result = MagicMock()
    membership_result.scalar_one_or_none.return_value = membership
    role_result = MagicMock()
    role_result.scalar_one_or_none.return_value = role

    db.execute.side_effect = [membership_result, role_result]

    svc = PermissionService(db)
    result = await svc.check_permission(
        membership.user_id, membership.organization_id, "users.manage"
    )
    assert result is False


@pytest.mark.asyncio
async def test_check_permission_returns_false_for_no_membership():
    db = AsyncMock()
    # validate_membership returns None
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock

    svc = PermissionService(db)
    result = await svc.check_permission(
        uuid.uuid4(), uuid.uuid4(), "users.manage"
    )
    assert result is False


@pytest.mark.asyncio
async def test_get_user_permissions_returns_permission_list():
    role = _make_role(["orders.view", "orders.create", "products.view"])
    membership = _make_membership(role.id)

    db = AsyncMock()
    membership_result = MagicMock()
    membership_result.scalar_one_or_none.return_value = membership
    role_result = MagicMock()
    role_result.scalar_one_or_none.return_value = role

    db.execute.side_effect = [membership_result, role_result]

    svc = PermissionService(db)
    permissions = await svc.get_user_permissions(
        membership.user_id, membership.organization_id
    )
    assert permissions == ["orders.view", "orders.create", "products.view"]


@pytest.mark.asyncio
async def test_get_user_permissions_returns_empty_for_no_membership():
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock

    svc = PermissionService(db)
    permissions = await svc.get_user_permissions(uuid.uuid4(), uuid.uuid4())
    assert permissions == []


@pytest.mark.asyncio
async def test_validate_membership_returns_none_for_nonexistent():
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock

    svc = PermissionService(db)
    result = await svc.validate_membership(uuid.uuid4(), uuid.uuid4())
    assert result is None
