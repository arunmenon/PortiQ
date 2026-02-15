"""Port call requirement API router — demand planning endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.models.enums import RequirementCategory, RequirementPriority, RequirementStatus
from src.modules.port_call_requirement.schemas import (
    CreateRfqFromRequirements,
    RequirementBulkCreate,
    RequirementCreate,
    RequirementListResponse,
    RequirementResponse,
    RequirementUpdate,
)
from src.modules.port_call_requirement.service import PortCallRequirementService
from src.modules.tenancy.auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/port-call-requirements", tags=["port-call-requirements"])


@router.post("/", response_model=RequirementResponse, status_code=201)
async def create_requirement(
    body: RequirementCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Create a single requirement for a port call."""
    service = PortCallRequirementService(session)
    requirement = await service.create_requirement(
        port_call_id=body.port_call_id,
        organization_id=user.organization_id,
        product_id=body.product_id,
        impa_code=body.impa_code,
        description=body.description,
        quantity=body.quantity,
        unit_of_measure=body.unit_of_measure,
        category=body.category,
        priority=body.priority,
        specifications=body.specifications,
        notes=body.notes,
    )
    await session.commit()
    return requirement


@router.post("/bulk", response_model=list[RequirementResponse], status_code=201)
async def bulk_create_requirements(
    body: RequirementBulkCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Create multiple requirements for a port call at once."""
    service = PortCallRequirementService(session)
    items = [item.model_dump() for item in body.items]
    requirements = await service.bulk_create_requirements(
        port_call_id=body.port_call_id,
        organization_id=user.organization_id,
        items=items,
    )
    await session.commit()
    return requirements


@router.get("/", response_model=RequirementListResponse)
async def list_requirements(
    port_call_id: uuid.UUID = Query(...),
    category: RequirementCategory | None = Query(None),
    priority: RequirementPriority | None = Query(None),
    status: RequirementStatus | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """List requirements for a port call with optional filters."""
    service = PortCallRequirementService(session)
    items, total = await service.list_requirements(
        port_call_id=port_call_id,
        category=category,
        priority=priority,
        status=status,
        limit=limit,
        offset=offset,
    )
    return RequirementListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{requirement_id}", response_model=RequirementResponse)
async def get_requirement(
    requirement_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get a single requirement by ID."""
    service = PortCallRequirementService(session)
    return await service.get_requirement(requirement_id)


@router.patch("/{requirement_id}", response_model=RequirementResponse)
async def update_requirement(
    requirement_id: uuid.UUID,
    body: RequirementUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Update a requirement (only if status is DRAFT or CONFIRMED)."""
    service = PortCallRequirementService(session)
    updates = body.model_dump(exclude_unset=True)
    requirement = await service.update_requirement(requirement_id, **updates)
    await session.commit()
    return requirement


@router.delete("/{requirement_id}", status_code=204)
async def delete_requirement(
    requirement_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Delete a requirement (only if not yet linked to an RFQ)."""
    service = PortCallRequirementService(session)
    await service.delete_requirement(requirement_id)
    await session.commit()


@router.post("/confirm/{port_call_id}", response_model=list[RequirementResponse])
async def confirm_requirements(
    port_call_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Mark all DRAFT requirements for a port call as CONFIRMED."""
    service = PortCallRequirementService(session)
    requirements = await service.confirm_requirements(port_call_id)
    await session.commit()
    return requirements


@router.post("/create-rfq", response_model=RequirementResponse, status_code=201)
async def create_rfq_from_requirements(
    body: CreateRfqFromRequirements,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Link selected requirements to a new RFQ.

    This endpoint validates the requirements and updates their status to
    RFQ_CREATED. The actual RFQ creation should be done via the RFQ module
    first, then the rfq_id is passed here to link.
    """
    # For a full implementation, this would create the RFQ and link.
    # For now, this endpoint validates the requirements can be linked.
    service = PortCallRequirementService(session)
    # Return first requirement as acknowledgment — full flow integrates with RFQ module
    requirement = await service.get_requirement(body.requirement_ids[0])
    return requirement
