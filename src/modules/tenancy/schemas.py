"""Pydantic schemas for tenant context and audit."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.models.enums import OrganizationType


class TenantContext(BaseModel):
    """Represents the current tenant context extracted from an authenticated request."""

    organization_id: uuid.UUID
    organization_type: OrganizationType
    user_id: uuid.UUID
    is_platform_admin: bool = False


class AuditContext(BaseModel):
    """Context for admin cross-tenant access, recorded for audit compliance."""

    admin_user_id: uuid.UUID
    target_organization_id: uuid.UUID
    justification: str
    accessed_at: datetime = Field(default_factory=datetime.utcnow)
    operation: str
