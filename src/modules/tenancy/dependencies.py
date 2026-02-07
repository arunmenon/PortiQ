"""FastAPI dependency functions for tenant context injection."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.exceptions import ForbiddenException, UnauthorizedException
from src.modules.tenancy.auth import AuthenticatedUser, get_current_user
from src.modules.tenancy.permissions import PermissionService
from src.modules.tenancy.schemas import TenantContext


def get_tenant_context(request: Request) -> TenantContext | None:
    """Extract the TenantContext from request state, or return None if not set."""
    return getattr(request.state, "tenant_context", None)


def require_tenant(
    tenant: TenantContext | None = Depends(get_tenant_context),
) -> TenantContext:
    """Dependency that guarantees a valid tenant context exists.

    Raises UnauthorizedException if no tenant context is available.
    """
    if tenant is None:
        raise UnauthorizedException("Tenant context is required. Please authenticate.")
    return tenant


def require_permission(permission: str):
    """Factory that returns a FastAPI dependency checking a specific permission.

    Permission is checked against the user's role in their **JWT-active organization**
    (``user.organization_id``), NOT the ``org_id`` path parameter.  Use the router-level
    ``_require_permission`` helper when you need to check against a path-supplied org.
    """

    async def _check(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> AuthenticatedUser:
        # Platform admins bypass permission checks
        if user.is_platform_admin:
            return user
        svc = PermissionService(db)
        has = await svc.check_permission(user.id, user.organization_id, permission)
        if not has:
            raise ForbiddenException(f"Permission denied: {permission}")
        return user

    return _check
