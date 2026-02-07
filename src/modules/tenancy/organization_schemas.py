"""Pydantic v2 schemas for tenancy API endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import OrganizationStatus, OrganizationType


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class OrganizationCreate(BaseModel):
    type: OrganizationType
    name: str = Field(..., min_length=1, max_length=255)
    legal_name: str | None = None
    slug: str | None = Field(None, max_length=100, pattern=r"^[a-z0-9][a-z0-9\-]*$")
    primary_email: str | None = None
    address: dict | None = None
    registration_number: str | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    legal_name: str | None = None
    primary_email: str | None = None
    primary_phone: str | None = None
    website: str | None = None
    settings: dict | None = None


class InviteMemberRequest(BaseModel):
    email: str
    role_id: uuid.UUID
    job_title: str | None = None
    department: str | None = None


class UpdateMemberRoleRequest(BaseModel):
    role_id: uuid.UUID


class PermissionCheckRequest(BaseModel):
    permission: str


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: OrganizationType
    name: str
    legal_name: str | None = None
    slug: str | None = None
    status: OrganizationStatus
    primary_email: str | None = None
    website: str | None = None
    created_at: datetime


class OrganizationDetailResponse(OrganizationResponse):
    member_count: int
    settings: dict | None = None


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    role_name: str
    role_display_name: str
    status: str
    joined_at: datetime | None = None
    invited_at: datetime | None = None
    job_title: str | None = None
    department: str | None = None


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    display_name: str
    description: str | None = None
    organization_type: OrganizationType
    permissions: list[str]
    is_system: bool


class UserOrganizationResponse(BaseModel):
    organization: OrganizationResponse
    role: RoleResponse
    joined_at: datetime | None = None


class PermissionCheckResponse(BaseModel):
    has_permission: bool
    permission: str


class SwitchOrgResponse(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    role: str
