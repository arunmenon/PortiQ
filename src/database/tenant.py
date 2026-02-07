from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_tenant_context(
    session: AsyncSession,
    organization_id: str,
    user_id: str | None = None,
    organization_type: str | None = None,
) -> None:
    """Set PostgreSQL session variables for RLS tenant isolation.

    Uses SET LOCAL so variables are scoped to the current transaction.
    """
    await session.execute(
        text("SELECT set_config('app.current_organization_id', :org_id, true)"),
        {"org_id": str(organization_id)},
    )
    if user_id:
        await session.execute(
            text("SELECT set_config('app.current_user_id', :user_id, true)"),
            {"user_id": str(user_id)},
        )
    if organization_type:
        await session.execute(
            text("SELECT set_config('app.current_organization_type', :org_type, true)"),
            {"org_type": organization_type},
        )
    await session.execute(
        text("SELECT set_config('app.admin_bypass', 'false', true)")
    )


async def set_admin_bypass(session: AsyncSession, *, enable: bool = True) -> None:
    """Enable or disable admin RLS bypass for the current transaction."""
    await session.execute(
        text("SELECT set_config('app.admin_bypass', :val, true)"),
        {"val": "true" if enable else "false"},
    )
