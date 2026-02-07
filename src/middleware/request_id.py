"""Middleware that assigns a unique request ID to every request."""

import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Generate or propagate a request ID for every HTTP request.

    If the incoming request carries an ``X-Request-ID`` header, that value is
    reused.  Otherwise a new UUID-4 is generated.  The ID is stored on
    ``request.state.request_id`` and echoed back via the ``X-Request-ID``
    response header.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
