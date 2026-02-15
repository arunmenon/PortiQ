"""Port call requirement service — demand planning before RFQ creation."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import BusinessRuleException, NotFoundException
from src.models.enums import RequirementCategory, RequirementPriority, RequirementStatus
from src.models.port_call_requirement import PortCallRequirement

logger = logging.getLogger(__name__)


class PortCallRequirementService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_requirement(
        self,
        port_call_id: uuid.UUID,
        organization_id: uuid.UUID,
        *,
        product_id: uuid.UUID | None = None,
        impa_code: str | None = None,
        description: str,
        quantity: float,
        unit_of_measure: str,
        category: RequirementCategory = RequirementCategory.OTHER,
        priority: RequirementPriority = RequirementPriority.MEDIUM,
        specifications: dict | None = None,
        notes: str | None = None,
    ) -> PortCallRequirement:
        requirement = PortCallRequirement(
            port_call_id=port_call_id,
            organization_id=organization_id,
            product_id=product_id,
            impa_code=impa_code,
            description=description,
            quantity=quantity,
            unit_of_measure=unit_of_measure,
            category=category,
            priority=priority,
            status=RequirementStatus.DRAFT,
            specifications=specifications,
            notes=notes,
        )
        self.db.add(requirement)
        await self.db.flush()
        await self.db.refresh(requirement)
        return requirement

    async def bulk_create_requirements(
        self,
        port_call_id: uuid.UUID,
        organization_id: uuid.UUID,
        items: list[dict],
    ) -> list[PortCallRequirement]:
        requirements = []
        for item in items:
            req = PortCallRequirement(
                port_call_id=port_call_id,
                organization_id=organization_id,
                product_id=item.get("product_id"),
                impa_code=item.get("impa_code"),
                description=item["description"],
                quantity=item["quantity"],
                unit_of_measure=item["unit_of_measure"],
                category=item.get("category", RequirementCategory.OTHER),
                priority=item.get("priority", RequirementPriority.MEDIUM),
                status=RequirementStatus.DRAFT,
                specifications=item.get("specifications"),
                notes=item.get("notes"),
            )
            self.db.add(req)
            requirements.append(req)
        await self.db.flush()
        for req in requirements:
            await self.db.refresh(req)
        return requirements

    async def get_requirement(self, requirement_id: uuid.UUID) -> PortCallRequirement:
        result = await self.db.execute(
            select(PortCallRequirement).where(PortCallRequirement.id == requirement_id)
        )
        requirement = result.scalar_one_or_none()
        if not requirement:
            raise NotFoundException(f"Requirement {requirement_id} not found")
        return requirement

    async def list_requirements(
        self,
        port_call_id: uuid.UUID,
        *,
        category: RequirementCategory | None = None,
        priority: RequirementPriority | None = None,
        status: RequirementStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PortCallRequirement], int]:
        query = select(PortCallRequirement).where(
            PortCallRequirement.port_call_id == port_call_id
        )
        count_query = select(func.count()).select_from(PortCallRequirement).where(
            PortCallRequirement.port_call_id == port_call_id
        )

        if category:
            query = query.where(PortCallRequirement.category == category)
            count_query = count_query.where(PortCallRequirement.category == category)
        if priority:
            query = query.where(PortCallRequirement.priority == priority)
            count_query = count_query.where(PortCallRequirement.priority == priority)
        if status:
            query = query.where(PortCallRequirement.status == status)
            count_query = count_query.where(PortCallRequirement.status == status)

        total = (await self.db.execute(count_query)).scalar() or 0
        result = await self.db.execute(
            query.order_by(PortCallRequirement.created_at).limit(limit).offset(offset)
        )
        items = list(result.scalars().all())
        return items, total

    async def update_requirement(
        self,
        requirement_id: uuid.UUID,
        **updates: object,
    ) -> PortCallRequirement:
        requirement = await self.get_requirement(requirement_id)
        if requirement.status == RequirementStatus.RFQ_CREATED:
            raise BusinessRuleException(
                "Cannot update a requirement that already has an RFQ"
            )
        for key, value in updates.items():
            if value is not None and hasattr(requirement, key):
                setattr(requirement, key, value)
        await self.db.flush()
        await self.db.refresh(requirement)
        return requirement

    async def delete_requirement(self, requirement_id: uuid.UUID) -> None:
        requirement = await self.get_requirement(requirement_id)
        if requirement.status == RequirementStatus.RFQ_CREATED:
            raise BusinessRuleException(
                "Cannot delete a requirement that already has an RFQ"
            )
        await self.db.delete(requirement)
        await self.db.flush()

    async def confirm_requirements(
        self,
        port_call_id: uuid.UUID,
    ) -> list[PortCallRequirement]:
        """Mark all DRAFT requirements for a port call as CONFIRMED."""
        result = await self.db.execute(
            select(PortCallRequirement).where(
                PortCallRequirement.port_call_id == port_call_id,
                PortCallRequirement.status == RequirementStatus.DRAFT,
            )
        )
        requirements = list(result.scalars().all())
        for req in requirements:
            req.status = RequirementStatus.CONFIRMED
        await self.db.flush()
        return requirements

    async def link_to_rfq(
        self,
        requirement_ids: list[uuid.UUID],
        rfq_id: uuid.UUID,
    ) -> list[PortCallRequirement]:
        """Link requirements to an RFQ and update their status."""
        result = await self.db.execute(
            select(PortCallRequirement).where(
                PortCallRequirement.id.in_(requirement_ids)
            )
        )
        requirements = list(result.scalars().all())
        if len(requirements) != len(requirement_ids):
            raise NotFoundException("One or more requirements not found")
        for req in requirements:
            if req.status not in (RequirementStatus.DRAFT, RequirementStatus.CONFIRMED):
                raise BusinessRuleException(
                    f"Requirement {req.id} is in status {req.status.value} "
                    "and cannot be linked to an RFQ"
                )
            req.rfq_id = rfq_id
            req.status = RequirementStatus.RFQ_CREATED
        await self.db.flush()
        return requirements
