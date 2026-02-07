"""Service layer for executing queries within a tenant-scoped transaction."""

from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.tenant import set_tenant_context
from src.modules.tenancy.schemas import TenantContext

T = TypeVar("T")


async def with_tenant_context(
    session: AsyncSession,
    tenant_context: TenantContext,
    callback: Callable[[AsyncSession], Awaitable[T]],
) -> T:
    """Execute a callback within a transaction that has RLS tenant context set.

    Sets all four PostgreSQL session variables (org_id, user_id, org_type,
    admin_bypass=false) before executing the callback. The session variables
    are transaction-scoped via set_config(..., true).

    Args:
        session: The async database session.
        tenant_context: The tenant context to apply.
        callback: An async callable that receives the session and returns a result.

    Returns:
        The result of the callback.
    """
    await set_tenant_context(
        session,
        organization_id=str(tenant_context.organization_id),
        user_id=str(tenant_context.user_id),
        organization_type=tenant_context.organization_type.value,
    )

    result = await callback(session)
    await session.commit()
    return result


async def unscoped_query(
    session: AsyncSession,
    callback: Callable[[AsyncSession], Awaitable[T]],
) -> T:
    """Execute a callback without tenant context, for shared/reference data.

    No RLS session variables are set, so PostgreSQL policies that require
    a tenant context will block access. Use only for tables with permissive
    policies (e.g., shared product catalog, IMPA codes, units).

    Args:
        session: The async database session.
        callback: An async callable that receives the session and returns a result.

    Returns:
        The result of the callback.
    """
    return await callback(session)
