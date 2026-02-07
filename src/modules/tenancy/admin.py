"""Admin context service for cross-tenant operations with audit logging."""

import json
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.tenant import set_admin_bypass
from src.modules.tenancy.schemas import AuditContext

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def _create_audit_entry(session: AsyncSession, audit_context: AuditContext) -> None:
    """Insert an audit log entry for admin cross-tenant access."""
    await session.execute(
        text(
            "INSERT INTO product_audit_log "
            "(id, entity_type, entity_id, operation, changed_fields, changed_by_id, change_reason, version, created_at) "
            "VALUES (gen_random_uuid(), :entity_type, :entity_id, :operation, :changed_fields, :changed_by_id, :change_reason, 1, now())"
        ),
        {
            "entity_type": "admin_cross_tenant_access",
            "entity_id": str(audit_context.target_organization_id),
            "operation": audit_context.operation,
            "changed_fields": json.dumps({"justification": audit_context.justification}),
            "changed_by_id": str(audit_context.admin_user_id),
            "change_reason": audit_context.justification,
        },
    )


async def with_admin_context(
    session: AsyncSession,
    audit_context: AuditContext,
    callback: Callable[[AsyncSession], Awaitable[T]],
) -> T:
    """Execute a callback with admin RLS bypass enabled, after creating an audit record.

    The audit entry is created BEFORE enabling bypass to ensure every admin
    access is logged even if the callback fails.

    Args:
        session: The async database session.
        audit_context: Audit details for this admin operation.
        callback: An async callable that receives the session and returns a result.

    Returns:
        The result of the callback.
    """
    # Record audit BEFORE enabling bypass
    await _create_audit_entry(session, audit_context)

    # Enable admin bypass for the remainder of this transaction
    await set_admin_bypass(session, enable=True)
    logger.info(
        "Admin bypass enabled for user=%s targeting org=%s operation=%s",
        audit_context.admin_user_id,
        audit_context.target_organization_id,
        audit_context.operation,
    )

    try:
        result = await callback(session)
        await session.commit()
        return result
    finally:
        # Reset bypass regardless of success or failure
        await set_admin_bypass(session, enable=False)
