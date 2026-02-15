"""Pydantic v2 schemas for Port Call Requirement endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import (
    RequirementCategory,
    RequirementPriority,
    RequirementStatus,
)


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class RequirementCreate(BaseModel):
    port_call_id: uuid.UUID
    product_id: uuid.UUID | None = None
    impa_code: str | None = Field(None, max_length=10)
    description: str = Field(..., min_length=1, max_length=500)
    quantity: Decimal = Field(..., gt=0)
    unit_of_measure: str = Field(..., min_length=1, max_length=20)
    category: RequirementCategory = RequirementCategory.OTHER
    priority: RequirementPriority = RequirementPriority.MEDIUM
    specifications: dict | None = None
    notes: str | None = None


class RequirementUpdate(BaseModel):
    product_id: uuid.UUID | None = None
    impa_code: str | None = Field(None, max_length=10)
    description: str | None = Field(None, min_length=1, max_length=500)
    quantity: Decimal | None = Field(None, gt=0)
    unit_of_measure: str | None = Field(None, min_length=1, max_length=20)
    category: RequirementCategory | None = None
    priority: RequirementPriority | None = None
    specifications: dict | None = None
    notes: str | None = None


class RequirementItemCreate(BaseModel):
    product_id: uuid.UUID | None = None
    impa_code: str | None = Field(None, max_length=10)
    description: str = Field(..., min_length=1, max_length=500)
    quantity: Decimal = Field(..., gt=0)
    unit_of_measure: str = Field(..., min_length=1, max_length=20)
    category: RequirementCategory = RequirementCategory.OTHER
    priority: RequirementPriority = RequirementPriority.MEDIUM
    specifications: dict | None = None
    notes: str | None = None


class RequirementBulkCreate(BaseModel):
    port_call_id: uuid.UUID
    items: list[RequirementItemCreate] = Field(..., min_length=1)


class CreateRfqFromRequirements(BaseModel):
    requirement_ids: list[uuid.UUID] = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=200)
    notes: str | None = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class RequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    port_call_id: uuid.UUID
    organization_id: uuid.UUID
    product_id: uuid.UUID | None = None
    impa_code: str | None = None
    description: str
    quantity: Decimal
    unit_of_measure: str
    category: RequirementCategory
    priority: RequirementPriority
    status: RequirementStatus
    rfq_id: uuid.UUID | None = None
    specifications: dict | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class RequirementListResponse(BaseModel):
    items: list[RequirementResponse]
    total: int
    limit: int
    offset: int
