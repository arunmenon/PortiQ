"""Unit tests for MembershipService."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.exceptions import BusinessRuleException, ConflictException, NotFoundException, ValidationException
from src.models.enums import MembershipStatus, OrganizationType
from src.modules.tenancy.membership_service import MembershipService


def _make_role(
    org_type: OrganizationType = OrganizationType.BUYER,
    name: str = "buyer_member",
    permissions: list[str] | None = None,
):
    role = MagicMock()
    role.id = uuid.uuid4()
    role.name = name
    role.display_name = name.replace("_", " ").title()
    role.organization_type = org_type
    role.permissions = permissions or ["orders.view"]
    role.is_system = True
    return role


def _make_user(email: str = "crew@ship.com"):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = email
    user.first_name = "Test"
    user.last_name = "User"
    return user


def _make_org(org_type: OrganizationType = OrganizationType.BUYER):
    org = MagicMock()
    org.id = uuid.uuid4()
    org.name = "Test Org"
    org.type = org_type
    return org


def _make_membership(
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    role_id: uuid.UUID,
    status: MembershipStatus = MembershipStatus.ACTIVE,
):
    m = MagicMock()
    m.id = uuid.uuid4()
    m.user_id = user_id
    m.organization_id = org_id
    m.role_id = role_id
    m.status = status
    m.invited_at = datetime.now(timezone.utc)
    m.joined_at = datetime.now(timezone.utc) if status == MembershipStatus.ACTIVE else None
    m.job_title = None
    m.department = None
    return m


@pytest.mark.asyncio
async def test_invite_user_creates_invited_membership():
    role = _make_role()
    user = _make_user()
    org = _make_org()

    db = AsyncMock()

    # MembershipService.invite_user queries: org, role, user, existing membership
    org_result = MagicMock()
    org_result.scalar_one_or_none.return_value = org

    role_result = MagicMock()
    role_result.scalar_one_or_none.return_value = role

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user

    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = None

    db.execute.side_effect = [org_result, role_result, user_result, existing_result]
    db.add = MagicMock()
    db.flush = AsyncMock()

    svc = MembershipService(db)
    membership = await svc.invite_user(
        org_id=org.id,
        email=user.email,
        role_id=role.id,
        invited_by=uuid.uuid4(),
    )
    assert membership.status == MembershipStatus.INVITED
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_invite_user_rejects_wrong_org_type_role():
    """A SUPPLIER role should not be assignable in a BUYER org."""
    role = _make_role(org_type=OrganizationType.SUPPLIER, name="supplier_admin")
    org = _make_org(org_type=OrganizationType.BUYER)

    db = AsyncMock()

    # Service queries org first, then role
    org_result = MagicMock()
    org_result.scalar_one_or_none.return_value = org
    role_result = MagicMock()
    role_result.scalar_one_or_none.return_value = role

    db.execute.side_effect = [org_result, role_result]

    svc = MembershipService(db)
    with pytest.raises(ValidationException):
        await svc.invite_user(
            org_id=org.id,
            email="new@example.com",
            role_id=role.id,
            invited_by=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_invite_user_rejects_duplicate_membership():
    role = _make_role()
    user = _make_user()
    org = _make_org()
    existing_membership = _make_membership(user.id, org.id, role.id)

    db = AsyncMock()

    org_result = MagicMock()
    org_result.scalar_one_or_none.return_value = org
    role_result = MagicMock()
    role_result.scalar_one_or_none.return_value = role
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = existing_membership

    db.execute.side_effect = [org_result, role_result, user_result, existing_result]

    svc = MembershipService(db)
    with pytest.raises(ConflictException):
        await svc.invite_user(
            org_id=org.id,
            email=user.email,
            role_id=role.id,
            invited_by=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_accept_invitation_transitions_to_active():
    user = _make_user()
    org = _make_org()
    role = _make_role()
    membership = _make_membership(user.id, org.id, role.id, status=MembershipStatus.INVITED)

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = membership
    db.execute.return_value = result_mock
    db.flush = AsyncMock()

    svc = MembershipService(db)
    updated = await svc.accept_invitation(
        user_id=user.id,
        org_id=org.id,
    )
    assert updated.status == MembershipStatus.ACTIVE


@pytest.mark.asyncio
async def test_accept_invitation_fails_for_nonexistent():
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock

    svc = MembershipService(db)
    with pytest.raises(NotFoundException):
        await svc.accept_invitation(
            user_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_remove_member_prevents_removing_last_admin():
    """Should raise BusinessRuleException when trying to remove the last admin."""
    user = _make_user()
    org = _make_org()
    admin_role = _make_role(name="buyer_admin", permissions=["*"])
    membership = _make_membership(user.id, org.id, admin_role.id)
    membership.role = admin_role

    db = AsyncMock()

    # remove_member uses joinedload, so result goes through unique().scalar_one_or_none()
    membership_result = MagicMock()
    unique_mock = MagicMock()
    unique_mock.scalar_one_or_none.return_value = membership
    membership_result.unique.return_value = unique_mock

    # Count admins in org -> 1 (only this user is admin)
    count_result = MagicMock()
    count_result.scalar.return_value = 1

    db.execute.side_effect = [membership_result, count_result]

    svc = MembershipService(db)
    with pytest.raises(BusinessRuleException):
        await svc.remove_member(org_id=org.id, user_id=user.id)


@pytest.mark.asyncio
async def test_update_member_role_validates_org_type():
    """Should reject role assignment if role org_type does not match org type."""
    user = _make_user()
    org = _make_org(org_type=OrganizationType.BUYER)
    wrong_role = _make_role(org_type=OrganizationType.SUPPLIER, name="supplier_viewer")
    current_role = _make_role(org_type=OrganizationType.BUYER, name="buyer_member")
    membership = _make_membership(user.id, org.id, current_role.id)

    db = AsyncMock()

    # update_member_role queries: membership, org, new_role
    membership_result = MagicMock()
    membership_result.scalar_one_or_none.return_value = membership

    org_result = MagicMock()
    org_result.scalar_one_or_none.return_value = org

    role_result = MagicMock()
    role_result.scalar_one_or_none.return_value = wrong_role

    db.execute.side_effect = [membership_result, org_result, role_result]

    svc = MembershipService(db)
    with pytest.raises(ValidationException):
        await svc.update_member_role(
            org_id=org.id,
            user_id=user.id,
            new_role_id=wrong_role.id,
        )
