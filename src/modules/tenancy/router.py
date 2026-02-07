"""Tenancy module API router — organization, membership, role, and context endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.exceptions import ForbiddenException, NotFoundException
from src.models.enums import MembershipStatus, OrganizationType
from src.models.organization_membership import OrganizationMembership
from src.models.role import Role
from src.models.user import User
from src.modules.tenancy.auth import AuthenticatedUser, get_current_user
from src.modules.tenancy.membership_service import MembershipService
from src.modules.tenancy.organization_schemas import (
    InviteMemberRequest,
    MembershipResponse,
    OrganizationCreate,
    OrganizationDetailResponse,
    OrganizationResponse,
    OrganizationUpdate,
    PermissionCheckRequest,
    PermissionCheckResponse,
    RoleResponse,
    SwitchOrgResponse,
    UpdateMemberRoleRequest,
    UserOrganizationResponse,
)
from src.modules.tenancy.organization_service import OrganizationService
from src.modules.tenancy.permissions import PermissionService

router = APIRouter(prefix="/tenancy", tags=["tenancy"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _require_permission(
    user: AuthenticatedUser,
    db: AsyncSession,
    org_id: uuid.UUID,
    permission: str,
) -> None:
    """Check permission and raise ForbiddenException if denied."""
    if user.is_platform_admin:
        return
    svc = PermissionService(db)
    has_perm = await svc.check_permission(user.id, org_id, permission)
    if not has_perm:
        raise ForbiddenException(f"Missing required permission: {permission}")


async def _require_membership(
    user: AuthenticatedUser,
    db: AsyncSession,
    org_id: uuid.UUID,
) -> None:
    """Validate that the user has an active membership in the org."""
    if user.is_platform_admin:
        return
    svc = PermissionService(db)
    membership = await svc.validate_membership(user.id, org_id)
    if membership is None:
        raise ForbiddenException("You are not a member of this organization")


# ---------------------------------------------------------------------------
# Organization endpoints
# ---------------------------------------------------------------------------


@router.post("/organizations", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    body: OrganizationCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new organization. The requesting user becomes the admin."""
    svc = OrganizationService(db)
    org = await svc.create_organization(
        name=body.name,
        org_type=body.type,
        creator_user_id=user.id,
        legal_name=body.legal_name,
        slug=body.slug,
        primary_email=body.primary_email,
        address=body.address,
        registration_number=body.registration_number,
    )
    return org


@router.get("/organizations", response_model=list[UserOrganizationResponse])
async def list_organizations(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all organizations the current user belongs to."""
    svc = OrganizationService(db)
    items = await svc.list_user_organizations(user.id)
    return [
        UserOrganizationResponse(
            organization=OrganizationResponse.model_validate(item["organization"]),
            role=RoleResponse.model_validate(item["role"]),
            joined_at=item["membership"].joined_at,
        )
        for item in items
    ]


@router.get("/organizations/{org_id}", response_model=OrganizationDetailResponse)
async def get_organization(
    org_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get organization details including member count."""
    await _require_membership(user, db, org_id)
    svc = OrganizationService(db)
    org = await svc.get_organization(org_id)

    # Count active members
    result = await db.execute(
        select(func.count())
        .select_from(OrganizationMembership)
        .where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.status == MembershipStatus.ACTIVE,
        )
    )
    member_count = result.scalar() or 0

    return OrganizationDetailResponse(
        **OrganizationResponse.model_validate(org).model_dump(),
        member_count=member_count,
        settings=org.settings,
    )


@router.patch("/organizations/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: uuid.UUID,
    body: OrganizationUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update organization details. Requires organization.manage permission."""
    await _require_permission(user, db, org_id, "organization.manage")
    svc = OrganizationService(db)
    org = await svc.update_organization(org_id, **body.model_dump(exclude_unset=True))
    return org


# ---------------------------------------------------------------------------
# Membership endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/organizations/{org_id}/members",
    response_model=list[MembershipResponse],
)
async def list_members(
    org_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all members of an organization."""
    await _require_membership(user, db, org_id)
    svc = MembershipService(db)
    memberships = await svc.list_members(org_id)
    return [
        MembershipResponse(
            id=m.id,
            user_id=m.user_id,
            email=m.user.email,
            first_name=m.user.first_name,
            last_name=m.user.last_name,
            role_name=m.role.name,
            role_display_name=m.role.display_name,
            status=m.status.value if hasattr(m.status, "value") else str(m.status),
            joined_at=m.joined_at,
            invited_at=m.invited_at,
            job_title=m.job_title,
            department=m.department,
        )
        for m in memberships
    ]


@router.post(
    "/organizations/{org_id}/members/invite",
    response_model=MembershipResponse,
    status_code=201,
)
async def invite_member(
    org_id: uuid.UUID,
    body: InviteMemberRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Invite a user to the organization. Requires users.manage permission."""
    await _require_permission(user, db, org_id, "users.manage")
    svc = MembershipService(db)
    membership = await svc.invite_user(
        org_id=org_id,
        email=body.email,
        role_id=body.role_id,
        invited_by=user.id,
        job_title=body.job_title,
        department=body.department,
    )
    # Fetch the role for the response since invite_user doesn't eagerly load it
    role_result = await db.execute(select(Role).where(Role.id == body.role_id))
    role = role_result.scalar_one_or_none()
    return MembershipResponse(
        id=membership.id,
        user_id=membership.user_id,
        email=body.email,
        first_name=None,
        last_name=None,
        role_name=role.name if role else "",
        role_display_name=role.display_name if role else "",
        status=membership.status.value if hasattr(membership.status, "value") else str(membership.status),
        joined_at=membership.joined_at,
        invited_at=membership.invited_at,
        job_title=membership.job_title,
        department=membership.department,
    )


@router.post("/organizations/{org_id}/members/accept", status_code=200)
async def accept_invitation(
    org_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept a pending invitation for the current user."""
    svc = MembershipService(db)
    membership = await svc.accept_invitation(
        user_id=user.id,
        org_id=org_id,
    )
    return {"status": "accepted", "organization_id": str(org_id), "membership_id": str(membership.id)}


@router.patch(
    "/organizations/{org_id}/members/{user_id}/role",
    response_model=dict,
)
async def update_member_role(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    body: UpdateMemberRoleRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a member's role. Requires users.manage permission."""
    await _require_permission(user, db, org_id, "users.manage")
    svc = MembershipService(db)
    await svc.update_member_role(
        org_id=org_id,
        user_id=user_id,
        new_role_id=body.role_id,
    )
    return {"status": "updated", "user_id": str(user_id), "role_id": str(body.role_id)}


@router.delete(
    "/organizations/{org_id}/members/{user_id}",
    status_code=204,
)
async def remove_member(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from the organization. Requires users.manage permission."""
    await _require_permission(user, db, org_id, "users.manage")
    svc = MembershipService(db)
    await svc.remove_member(org_id=org_id, user_id=user_id)
    return None


# ---------------------------------------------------------------------------
# Role endpoints
# ---------------------------------------------------------------------------


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    organization_type: OrganizationType | None = Query(None),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List available roles, optionally filtered by organization type."""
    query = select(Role)
    if organization_type is not None:
        query = query.where(Role.organization_type == organization_type)
    query = query.order_by(Role.organization_type, Role.name)
    result = await db.execute(query)
    roles = result.scalars().all()
    return [RoleResponse.model_validate(r) for r in roles]


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single role by ID."""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if role is None:
        raise NotFoundException(f"Role {role_id} not found")
    return RoleResponse.model_validate(role)


# ---------------------------------------------------------------------------
# Context endpoints
# ---------------------------------------------------------------------------


@router.get("/context")
async def get_tenant_context(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current tenant context including user permissions."""
    perm_svc = PermissionService(db)
    permissions = await perm_svc.get_user_permissions(user.id, user.organization_id)
    role = await perm_svc.get_user_role_in_org(user.id, user.organization_id)

    return {
        "user_id": str(user.id),
        "email": user.email,
        "organization_id": str(user.organization_id),
        "organization_type": user.organization_type,
        "role": role.name if role else user.role,
        "role_display_name": role.display_name if role else user.role,
        "is_platform_admin": user.is_platform_admin,
        "permissions": permissions,
    }


@router.post("/switch-org/{org_id}", response_model=SwitchOrgResponse)
async def switch_organization(
    org_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Switch active organization. Validates membership and persists as default."""
    perm_svc = PermissionService(db)
    membership = await perm_svc.validate_membership(user.id, org_id)
    if membership is None:
        raise ForbiddenException("You are not a member of this organization")

    org_svc = OrganizationService(db)
    org = await org_svc.get_organization(org_id)
    role = await perm_svc.get_user_role_in_org(user.id, org_id)

    # Persist the switch as the user's default organization
    result = await db.execute(select(User).where(User.id == user.id))
    db_user = result.scalar_one_or_none()
    if db_user:
        db_user.default_organization_id = org_id
        await db.flush()

    return SwitchOrgResponse(
        organization_id=org.id,
        organization_name=org.name,
        role=role.name if role else "MEMBER",
    )


@router.post("/check-permission", response_model=PermissionCheckResponse)
async def check_permission(
    body: PermissionCheckRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if the current user has a specific permission."""
    svc = PermissionService(db)
    has_perm = await svc.check_permission(user.id, user.organization_id, body.permission)
    return PermissionCheckResponse(has_permission=has_perm, permission=body.permission)
