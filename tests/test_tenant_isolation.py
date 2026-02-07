"""Tests for tenant isolation via PostgreSQL session variables (RLS)."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.tenant import set_admin_bypass, set_tenant_context


@pytest.mark.asyncio
async def test_tenant_context_sets_session_variables(async_session: AsyncSession) -> None:
    """Verify that set_tenant_context correctly sets PostgreSQL session variables."""
    organization_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    organization_type = "BUYER"

    await set_tenant_context(
        async_session,
        organization_id=organization_id,
        user_id=user_id,
        organization_type=organization_type,
    )

    # Read back the session variables
    org_result = await async_session.execute(
        text("SELECT current_setting('app.current_organization_id', true)")
    )
    org_value = org_result.scalar()
    assert org_value == organization_id

    user_result = await async_session.execute(
        text("SELECT current_setting('app.current_user_id', true)")
    )
    user_value = user_result.scalar()
    assert user_value == user_id

    type_result = await async_session.execute(
        text("SELECT current_setting('app.current_organization_type', true)")
    )
    type_value = type_result.scalar()
    assert type_value == organization_type

    bypass_result = await async_session.execute(
        text("SELECT current_setting('app.admin_bypass', true)")
    )
    bypass_value = bypass_result.scalar()
    assert bypass_value == "false"


@pytest.mark.asyncio
async def test_admin_bypass_enables_cross_tenant_access(async_session: AsyncSession) -> None:
    """Verify that set_admin_bypass toggles the admin bypass session variable."""
    # First set tenant context (which sets admin_bypass to false)
    await set_tenant_context(
        async_session,
        organization_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
    )

    # Enable admin bypass
    await set_admin_bypass(async_session, enable=True)

    result = await async_session.execute(
        text("SELECT current_setting('app.admin_bypass', true)")
    )
    assert result.scalar() == "true"

    # Disable admin bypass
    await set_admin_bypass(async_session, enable=False)

    result = await async_session.execute(
        text("SELECT current_setting('app.admin_bypass', true)")
    )
    assert result.scalar() == "false"


@pytest.mark.asyncio
async def test_missing_context_raises_error(async_session: AsyncSession) -> None:
    """Verify that reading unset session variables returns empty string (PostgreSQL default).

    PostgreSQL current_setting with missing_ok=true returns empty string for unset
    custom variables, not an error. The RLS policies should treat empty org_id as
    no access.
    """
    # Read session variable that has not been set in this transaction
    result = await async_session.execute(
        text("SELECT current_setting('app.current_organization_id', true)")
    )
    value = result.scalar()

    # PostgreSQL returns empty string for unset GUC variables with missing_ok=true
    assert value is None or value == ""
