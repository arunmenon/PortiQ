"""Permission checking service for multi-tenant RBAC."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.models.enums import MembershipStatus
from src.models.organization_membership import OrganizationMembership
from src.models.role import Role

logger = logging.getLogger(__name__)


class PermissionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_permission(
        self, user_id: uuid.UUID, organization_id: uuid.UUID, permission: str
    ) -> bool:
        """Check if user has a specific permission in an org via their membership role."""
        role = await self.get_user_role_in_org(user_id, organization_id)
        if role is None:
            return False
        # Wildcard permission grants everything
        if "*" in role.permissions:
            return True
        return permission in role.permissions

    async def get_user_role_in_org(
        self, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Role | None:
        """Get the user's role in an organization via a single query with joinedload."""
        membership = await self._get_membership_with_role(user_id, organization_id)
        if membership is None:
            return None
        return membership.role

    async def get_user_permissions(
        self, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> list[str]:
        """Get all permissions for a user in an org."""
        role = await self.get_user_role_in_org(user_id, organization_id)
        if role is None:
            return []
        return list(role.permissions)

    async def validate_membership(
        self, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> OrganizationMembership | None:
        """Validate user has active membership in org (without loading role)."""
        result = await self.db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.status == MembershipStatus.ACTIVE,
            )
        )
        return result.scalar_one_or_none()

    async def _get_membership_with_role(
        self, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> OrganizationMembership | None:
        """Fetch active membership with role eagerly loaded in a single query."""
        result = await self.db.execute(
            select(OrganizationMembership)
            .options(joinedload(OrganizationMembership.role))
            .where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.status == MembershipStatus.ACTIVE,
            )
        )
        return result.unique().scalar_one_or_none()
