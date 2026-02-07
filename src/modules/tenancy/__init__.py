"""Tenancy module — multi-tenant isolation via PostgreSQL RLS."""

from src.modules.tenancy.admin import with_admin_context
from src.modules.tenancy.auth import AuthenticatedUser, get_current_user, get_optional_user
from src.modules.tenancy.dependencies import get_tenant_context, require_permission, require_tenant
from src.modules.tenancy.middleware import TenantContextMiddleware
from src.modules.tenancy.permissions import PermissionService
from src.modules.tenancy.schemas import AuditContext, TenantContext
from src.modules.tenancy.service import unscoped_query, with_tenant_context

__all__ = [
    # Schemas
    "TenantContext",
    "AuditContext",
    # Auth
    "AuthenticatedUser",
    "get_current_user",
    "get_optional_user",
    # Middleware
    "TenantContextMiddleware",
    # Dependencies
    "get_tenant_context",
    "require_tenant",
    "require_permission",
    # Service
    "with_tenant_context",
    "unscoped_query",
    # Admin
    "with_admin_context",
    # Permissions
    "PermissionService",
]
