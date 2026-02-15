"""Dispute Resolution API router — 7 endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.exceptions import ForbiddenException
from src.models.enums import DisputeStatus, DisputeType
from src.modules.dispute.schemas import (
    AssignReviewerRequest,
    CommentCreate,
    DisputeCommentResponse,
    DisputeCreate,
    DisputeListResponse,
    DisputeResponse,
    EscalateRequest,
    ResolveRequest,
)
from src.modules.dispute.service import DisputeService
from src.modules.tenancy.auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/disputes", tags=["disputes"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_buyer(user: AuthenticatedUser) -> None:
    """Raise ForbiddenException unless the user is from a buyer org or platform."""
    if user.organization_type not in ("BUYER", "BOTH", "PLATFORM"):
        raise ForbiddenException("This action requires a buyer organization")


def _require_platform(user: AuthenticatedUser) -> None:
    """Raise ForbiddenException unless the user is a platform admin."""
    if user.organization_type != "PLATFORM" and not user.is_platform_admin:
        raise ForbiddenException("This action requires platform admin access")


# ---------------------------------------------------------------------------
# Dispute CRUD
# ---------------------------------------------------------------------------


@router.post("/", response_model=DisputeResponse, status_code=201)
async def create_dispute(
    body: DisputeCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Raise a new dispute against a delivery or order."""
    _require_buyer(user)
    svc = DisputeService(db)
    dispute = await svc.create_dispute(
        data=body.model_dump(),
        user=user,
    )
    return DisputeResponse.model_validate(dispute)


@router.get("/", response_model=DisputeListResponse)
async def list_disputes(
    status: DisputeStatus | None = Query(None),
    dispute_type: DisputeType | None = Query(None, alias="type"),
    order_id: uuid.UUID | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List disputes visible to the calling organization."""
    svc = DisputeService(db)
    items, total = await svc.list_disputes(
        organization_id=user.organization_id,
        status=status,
        dispute_type=dispute_type,
        order_id=order_id,
        limit=limit,
        offset=offset,
    )
    return DisputeListResponse(
        items=[DisputeResponse.model_validate(d) for d in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{dispute_id}", response_model=DisputeResponse)
async def get_dispute(
    dispute_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single dispute with comments and transitions."""
    svc = DisputeService(db)
    dispute = await svc.get_dispute(dispute_id)
    return DisputeResponse.model_validate(dispute)


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


@router.post(
    "/{dispute_id}/comments",
    response_model=DisputeCommentResponse,
    status_code=201,
)
async def add_comment(
    dispute_id: uuid.UUID,
    body: CommentCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a comment to a dispute (with optional attachment S3 key)."""
    svc = DisputeService(db)
    comment = await svc.add_comment(
        dispute_id=dispute_id,
        content=body.content,
        is_internal=body.is_internal,
        user=user,
        attachment_s3_key=body.attachment_s3_key,
        attachment_filename=body.attachment_filename,
        attachment_content_type=body.attachment_content_type,
    )
    return DisputeCommentResponse.model_validate(comment)


# ---------------------------------------------------------------------------
# State Transitions
# ---------------------------------------------------------------------------


@router.put("/{dispute_id}/assign", response_model=DisputeResponse)
async def assign_reviewer(
    dispute_id: uuid.UUID,
    body: AssignReviewerRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign a reviewer to a dispute (transitions to UNDER_REVIEW)."""
    svc = DisputeService(db)
    dispute = await svc.assign_reviewer(
        dispute_id=dispute_id,
        reviewer_id=body.reviewer_id,
        user=user,
    )
    return DisputeResponse.model_validate(dispute)


@router.post("/{dispute_id}/resolve", response_model=DisputeResponse)
async def resolve_dispute(
    dispute_id: uuid.UUID,
    body: ResolveRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a dispute with a financial outcome."""
    svc = DisputeService(db)
    dispute = await svc.resolve_dispute(
        dispute_id=dispute_id,
        resolution_type=body.resolution_type,
        resolution_amount=body.resolution_amount,
        notes=body.notes,
        user=user,
    )
    return DisputeResponse.model_validate(dispute)


@router.post("/{dispute_id}/escalate", response_model=DisputeResponse)
async def escalate_dispute(
    dispute_id: uuid.UUID,
    body: EscalateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Escalate a dispute to platform operations."""
    svc = DisputeService(db)
    dispute = await svc.escalate_dispute(
        dispute_id=dispute_id,
        reason=body.reason,
        user=user,
    )
    return DisputeResponse.model_validate(dispute)
