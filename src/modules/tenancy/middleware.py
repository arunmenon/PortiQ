"""FastAPI middleware for extracting and setting tenant context via PostgreSQL RLS."""

import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from src.modules.tenancy.constants import EXCLUDED_ROUTES
from src.modules.tenancy.schemas import TenantContext

logger = logging.getLogger(__name__)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Extracts tenant information from the authenticated user and stores it in request state.

    For excluded routes (health, docs, etc.), passes through without tenant context.
    For authenticated routes, builds a TenantContext from request.state.user
    (set by the auth middleware upstream) and stores it in request.state.tenant_context.

    The actual PostgreSQL session variable setting happens at the service layer
    (via with_tenant_context) when a database session is used, not in this middleware,
    because the middleware does not own the DB session lifecycle.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # Skip tenant extraction for excluded routes
        if any(path.startswith(route) for route in EXCLUDED_ROUTES):
            return await call_next(request)

        # Extract user info set by auth middleware
        user = getattr(request.state, "user", None)
        if user is None:
            # No authenticated user — let downstream handlers decide (e.g. return 401)
            return await call_next(request)

        try:
            tenant_context = TenantContext(
                organization_id=user.organization_id,
                organization_type=user.organization_type,
                user_id=user.id,
                is_platform_admin=getattr(user, "is_platform_admin", False),
            )
            request.state.tenant_context = tenant_context
        except (AttributeError, ValueError) as exc:
            logger.warning("Failed to build tenant context from user: %s", exc)
            # Let the request proceed; dependency injection will raise 401 if needed

        return await call_next(request)
