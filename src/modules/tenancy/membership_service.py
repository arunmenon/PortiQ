"""Membership lifecycle service -- invite, accept, remove, update role."""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.exceptions import (
    BusinessRuleException,
    ConflictException,
    NotFoundException,
    ValidationException,
)
from src.models.enums import MembershipStatus
from src.models.organization import Organization
from src.models.organization_membership import OrganizationMembership
from src.models.role import Role
from src.models.user import User

logger = logging.getLogger(__name__)


class MembershipService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def invite_user(
        self,
        org_id: uuid.UUID,
        email: str,
        role_id: uuid.UUID,
        invited_by: uuid.UUID,
        job_title: str | None = None,
        department: str | None = None,
    ) -> OrganizationMembership:
        """Create INVITED membership. Validates role matches org type."""
        # Get org
        org_result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = org_result.scalar_one_or_none()
        if org is None:
            raise NotFoundException(f"Organization {org_id} not found")

        # Get role and validate it matches org type
        role_result = await self.db.execute(
            select(Role).where(Role.id == role_id)
        )
        role = role_result.scalar_one_or_none()
        if role is None:
            raise NotFoundException(f"Role {role_id} not found")

        if role.organization_type != org.type:
            raise ValidationException(
                f"Role '{role.name}' is for {role.organization_type.value} organizations, "
                f"but this organization is {org.type.value}"
            )

        # Find user by email
        user_result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            raise NotFoundException(f"User with email '{email}' not found")

        # Check for existing membership
        existing = await self.db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == org_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictException(
                f"User '{email}' already has a membership in this organization"
            )

        membership = OrganizationMembership(
            user_id=user.id,
            organization_id=org_id,
            role_id=role_id,
            status=MembershipStatus.INVITED,
            invited_by=invited_by,
            invited_at=datetime.now(timezone.utc),
            job_title=job_title,
            department=department,
        )
        self.db.add(membership)
        await self.db.flush()
        return membership

    async def accept_invitation(
        self, user_id: uuid.UUID, org_id: uuid.UUID
    ) -> OrganizationMembership:
        """Transition INVITED -> ACTIVE. Set joined_at."""
        result = await self.db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == org_id,
                OrganizationMembership.status == MembershipStatus.INVITED,
            )
        )
        membership = result.scalar_one_or_none()
        if membership is None:
            raise NotFoundException("No pending invitation found")

        membership.status = MembershipStatus.ACTIVE
        membership.joined_at = datetime.now(timezone.utc)
        await self.db.flush()
        return membership

    async def remove_member(
        self, org_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """Remove membership. Cannot remove last admin/owner."""
        result = await self.db.execute(
            select(OrganizationMembership)
            .options(joinedload(OrganizationMembership.role))
            .where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == org_id,
            )
        )
        membership = result.unique().scalar_one_or_none()
        if membership is None:
            raise NotFoundException("Membership not found")

        # Check if this is the last admin
        if membership.role and "*" in membership.role.permissions:
            admin_count_result = await self.db.execute(
                select(func.count(OrganizationMembership.id))
                .join(Role)
                .where(
                    OrganizationMembership.organization_id == org_id,
                    OrganizationMembership.status == MembershipStatus.ACTIVE,
                    Role.permissions.contains(["*"]),
                )
            )
            admin_count = admin_count_result.scalar()
            if admin_count is not None and admin_count <= 1:
                raise BusinessRuleException(
                    "Cannot remove the last admin from the organization"
                )

        await self.db.delete(membership)
        await self.db.flush()

    async def update_member_role(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        new_role_id: uuid.UUID,
    ) -> OrganizationMembership:
        """Change a member's role. Validates role matches org type.

        Prevents demoting the last admin (wildcard permission holder) to a
        non-admin role, which would leave the org with no admin.
        """
        # Get membership with current role eagerly loaded
        result = await self.db.execute(
            select(OrganizationMembership)
            .options(joinedload(OrganizationMembership.role))
            .where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == org_id,
            )
        )
        membership = result.unique().scalar_one_or_none()
        if membership is None:
            raise NotFoundException("Membership not found")

        # Get org for type validation
        org_result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = org_result.scalar_one_or_none()
        if org is None:
            raise NotFoundException(f"Organization {org_id} not found")

        # Get and validate new role
        role_result = await self.db.execute(
            select(Role).where(Role.id == new_role_id)
        )
        new_role = role_result.scalar_one_or_none()
        if new_role is None:
            raise NotFoundException(f"Role {new_role_id} not found")

        if new_role.organization_type != org.type:
            raise ValidationException(
                f"Role '{new_role.name}' is for {new_role.organization_type.value} organizations, "
                f"but this organization is {org.type.value}"
            )

        # Prevent demoting the last admin to a non-admin role
        current_role = membership.role
        current_is_admin = current_role and "*" in current_role.permissions
        new_is_admin = "*" in new_role.permissions
        if current_is_admin and not new_is_admin:
            admin_count_result = await self.db.execute(
                select(func.count(OrganizationMembership.id))
                .join(Role)
                .where(
                    OrganizationMembership.organization_id == org_id,
                    OrganizationMembership.status == MembershipStatus.ACTIVE,
                    Role.permissions.contains(["*"]),
                )
            )
            admin_count = admin_count_result.scalar()
            if admin_count is not None and admin_count <= 1:
                raise BusinessRuleException(
                    "Cannot demote the last admin of the organization"
                )

        membership.role_id = new_role_id
        await self.db.flush()
        return membership

    async def list_members(
        self,
        org_id: uuid.UUID,
        status: MembershipStatus | None = None,
    ) -> list[OrganizationMembership]:
        """List org members with role and user details."""
        query = (
            select(OrganizationMembership)
            .options(
                joinedload(OrganizationMembership.user),
                joinedload(OrganizationMembership.role),
            )
            .where(OrganizationMembership.organization_id == org_id)
        )
        if status is not None:
            query = query.where(OrganizationMembership.status == status)
        result = await self.db.execute(query)
        return list(result.unique().scalars().all())
