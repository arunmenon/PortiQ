"""JWT authentication dependency for FastAPI.

Validates Bearer tokens from the Authorization header, extracts user claims,
and sets request.state.user for downstream middleware and dependencies.
"""

import logging
import uuid
from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from src.config import settings
from src.exceptions import UnauthorizedException

logger = logging.getLogger(__name__)

# FastAPI security scheme — extracts Bearer token from Authorization header
_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedUser:
    """Represents the authenticated user extracted from a JWT token."""

    id: uuid.UUID
    email: str
    organization_id: uuid.UUID
    organization_type: str
    role: str
    is_platform_admin: bool = False


def _decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises UnauthorizedException on failure."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise UnauthorizedException("Invalid or expired token") from exc


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthenticatedUser:
    """FastAPI dependency that extracts and validates the current user from JWT.

    Sets request.state.user so that downstream middleware (TenantContextMiddleware)
    can build the tenant context.
    """
    if credentials is None:
        raise UnauthorizedException("Authentication required")

    payload = _decode_token(credentials.credentials)

    # Extract required claims
    try:
        user = AuthenticatedUser(
            id=uuid.UUID(payload["sub"]),
            email=payload["email"],
            organization_id=uuid.UUID(payload["org_id"]),
            organization_type=payload.get("org_type", "BUYER"),
            role=payload.get("role", "MEMBER"),
            is_platform_admin=payload.get("is_platform_admin", False),
        )
    except (KeyError, ValueError) as exc:
        raise UnauthorizedException("Token is missing required claims") from exc

    # Store on request state for TenantContextMiddleware
    request.state.user = user
    return user


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthenticatedUser | None:
    """Like get_current_user but returns None instead of raising for unauthenticated requests."""
    if credentials is None:
        return None

    try:
        return await get_current_user(request, credentials)
    except UnauthorizedException:
        return None
