"""Organization management service."""

import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.exceptions import BusinessRuleException, ConflictException, NotFoundException
from src.models.enums import MembershipStatus, OrganizationStatus, OrganizationType
from src.models.organization import Organization
from src.models.organization_membership import OrganizationMembership
from src.models.role import Role

logger = logging.getLogger(__name__)


class OrganizationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_organization(
        self,
        name: str,
        org_type: OrganizationType,
        creator_user_id: uuid.UUID,
        legal_name: str | None = None,
        slug: str | None = None,
        primary_email: str | None = None,
        address: dict | None = None,
        registration_number: str | None = None,
    ) -> Organization:
        """Create org + auto-create ACTIVE membership for creator with admin role."""
        if slug is None:
            slug = await self.generate_slug(name)
        else:
            existing = await self._get_by_slug(slug)
            if existing:
                raise ConflictException(f"Organization slug '{slug}' already exists")

        org = Organization(
            name=name,
            type=org_type,
            legal_name=legal_name,
            slug=slug,
            status=OrganizationStatus.ACTIVE,
            primary_email=primary_email,
            address=address,
            registration_number=registration_number,
        )
        self.db.add(org)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            if "ix_organizations_slug" in str(exc):
                raise ConflictException(f"Organization slug '{slug}' already exists") from exc
            raise

        # Find admin role for org type.
        # BOTH orgs use BUYER admin role since there's no dedicated BOTH admin.
        role_lookup_type = org_type
        if org_type == OrganizationType.BOTH:
            role_lookup_type = OrganizationType.BUYER

        admin_role_name = {
            OrganizationType.BUYER: "buyer_admin",
            OrganizationType.SUPPLIER: "supplier_admin",
            OrganizationType.PLATFORM: "super_admin",
        }.get(role_lookup_type, "buyer_admin")

        result = await self.db.execute(
            select(Role).where(
                Role.name == admin_role_name,
                Role.organization_type == role_lookup_type,
            )
        )
        admin_role = result.scalar_one_or_none()

        if admin_role is None:
            raise BusinessRuleException(
                f"Cannot create organization: no admin role found for type '{org_type.value}'. "
                "Ensure system roles have been seeded."
            )

        membership = OrganizationMembership(
            user_id=creator_user_id,
            organization_id=org.id,
            role_id=admin_role.id,
            status=MembershipStatus.ACTIVE,
            joined_at=datetime.now(timezone.utc),
        )
        self.db.add(membership)
        await self.db.flush()

        return org

    async def get_organization(self, org_id: uuid.UUID) -> Organization:
        """Get organization by ID."""
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = result.scalar_one_or_none()
        if org is None:
            raise NotFoundException(f"Organization {org_id} not found")
        return org

    async def update_organization(
        self, org_id: uuid.UUID, **kwargs
    ) -> Organization:
        """Update organization fields. Supports setting nullable fields to None."""
        org = await self.get_organization(org_id)
        for key, value in kwargs.items():
            if hasattr(org, key):
                setattr(org, key, value)
        await self.db.flush()
        return org

    async def list_user_organizations(self, user_id: uuid.UUID) -> list[dict]:
        """List all orgs a user belongs to, with their role in each."""
        result = await self.db.execute(
            select(OrganizationMembership)
            .options(
                joinedload(OrganizationMembership.organization),
                joinedload(OrganizationMembership.role),
            )
            .where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.status == MembershipStatus.ACTIVE,
            )
        )
        memberships = result.unique().scalars().all()
        return [
            {
                "organization": m.organization,
                "role": m.role,
                "membership": m,
            }
            for m in memberships
        ]

    async def generate_slug(self, name: str, max_retries: int = 5) -> str:
        """Generate unique URL-friendly slug from org name.

        Uses optimistic approach: generates a candidate slug, and if a race
        condition causes a conflict at flush time, retries with a suffix.
        """
        base_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if not base_slug:
            base_slug = "org"
        slug = base_slug
        counter = 1
        while await self._get_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1
            if counter > max_retries + 100:
                raise ConflictException(f"Could not generate unique slug for '{name}'")
        return slug

    async def _get_by_slug(self, slug: str) -> Organization | None:
        result = await self.db.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()
