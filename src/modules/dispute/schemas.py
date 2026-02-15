"""Pydantic v2 schemas for Dispute Resolution API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import (
    DisputePriority,
    DisputeResolutionType,
    DisputeStatus,
    DisputeType,
)

# ---------------------------------------------------------------------------
# Dispute Create / Response
# ---------------------------------------------------------------------------


class DisputeCreate(BaseModel):
    order_id: uuid.UUID
    delivery_id: uuid.UUID | None = None
    delivery_item_id: uuid.UUID | None = None
    vendor_order_id: uuid.UUID | None = None
    supplier_org_id: uuid.UUID
    dispute_type: DisputeType
    priority: DisputePriority = DisputePriority.MEDIUM
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    disputed_amount: Decimal | None = Field(None, ge=0)
    currency: str = Field("USD", max_length=3)


class DisputeCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dispute_id: uuid.UUID
    author_id: uuid.UUID
    author_org_id: uuid.UUID
    content: str
    is_internal: bool
    attachment_s3_key: str | None = None
    attachment_filename: str | None = None
    attachment_content_type: str | None = None
    created_at: datetime


class DisputeTransitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dispute_id: uuid.UUID
    from_status: DisputeStatus
    to_status: DisputeStatus
    transitioned_by: uuid.UUID
    reason: str | None = None
    created_at: datetime


class DisputeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dispute_number: str
    organization_id: uuid.UUID
    order_id: uuid.UUID
    delivery_id: uuid.UUID | None = None
    delivery_item_id: uuid.UUID | None = None
    vendor_order_id: uuid.UUID | None = None
    raised_by_org_id: uuid.UUID
    raised_by_user_id: uuid.UUID
    supplier_org_id: uuid.UUID
    assigned_reviewer_id: uuid.UUID | None = None
    dispute_type: DisputeType
    status: DisputeStatus
    priority: DisputePriority
    title: str
    description: str
    disputed_amount: Decimal | None = None
    currency: str
    resolution_type: DisputeResolutionType | None = None
    resolution_amount: Decimal | None = None
    resolution_notes: str | None = None
    response_due_at: datetime | None = None
    resolution_due_at: datetime | None = None
    sla_breached: bool
    resolved_at: datetime | None = None
    resolved_by: uuid.UUID | None = None
    escalated_at: datetime | None = None
    escalated_by: uuid.UUID | None = None
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    comments: list[DisputeCommentResponse] = Field(default_factory=list)
    transitions: list[DisputeTransitionResponse] = Field(default_factory=list)


class DisputeListResponse(BaseModel):
    items: list[DisputeResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Comment
# ---------------------------------------------------------------------------


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1)
    is_internal: bool = False
    attachment_s3_key: str | None = Field(None, max_length=500)
    attachment_filename: str | None = Field(None, max_length=255)
    attachment_content_type: str | None = Field(None, max_length=50)


# ---------------------------------------------------------------------------
# Assign Reviewer
# ---------------------------------------------------------------------------


class AssignReviewerRequest(BaseModel):
    reviewer_id: uuid.UUID


# ---------------------------------------------------------------------------
# Resolve
# ---------------------------------------------------------------------------


class ResolveRequest(BaseModel):
    resolution_type: DisputeResolutionType
    resolution_amount: Decimal | None = Field(None, ge=0)
    notes: str | None = Field(None, max_length=2000)


# ---------------------------------------------------------------------------
# Escalate
# ---------------------------------------------------------------------------


class EscalateRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)
