"""FastAPI application factory for PortiQ Maritime Procurement API."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.config import settings
from src.database.engine import engine
from src.exceptions import AppException

logger = logging.getLogger(__name__)

# Rate limiter — keyed by client IP address
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — dispose async engine on shutdown."""
    yield
    await engine.dispose()


def _get_request_id(request: Request) -> str:
    """Retrieve the request ID stored by RequestIdMiddleware."""
    return getattr(request.state, "request_id", "unknown")


def _error_response(status_code: int, code: str, message: str, request_id: str, details: list | None = None) -> JSONResponse:
    """Build a structured error JSONResponse per ADR-NF-007."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "requestId": request_id,
            }
        },
    )


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    application = FastAPI(
        title="PortiQ Maritime Procurement API",
        description="B2B maritime ship chandlery platform with AI-native search and procurement workflows.",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # Rate limiter
    application.state.limiter = limiter

    # --- Middleware (last added = outermost in Starlette) ---

    # Tenant context middleware — extracts tenant info from authenticated requests
    from src.modules.tenancy.middleware import TenantContextMiddleware

    application.add_middleware(TenantContextMiddleware)

    # CORS — configured via CORS_ORIGINS env var, never wildcard with credentials
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID — registered last so it runs first (outermost)
    from src.middleware.request_id import RequestIdMiddleware

    application.add_middleware(RequestIdMiddleware)

    # --- Routers ---
    from src.api.v1 import v1_router

    application.include_router(v1_router)

    # --- Exception Handlers ---

    @application.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return _error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            request_id=_get_request_id(request),
            details=exc.details,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {"field": ".".join(str(loc) for loc in err.get("loc", [])), "message": err.get("msg", "")}
            for err in exc.errors()
        ]
        return _error_response(
            status_code=422,
            code="VALIDATION_ERROR",
            message="Validation failed",
            request_id=_get_request_id(request),
            details=details,
        )

    @application.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return _error_response(
            status_code=429,
            code="RATE_LIMITED",
            message=str(exc.detail),
            request_id=_get_request_id(request),
        )

    @application.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return _error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="An unexpected error occurred.",
            request_id=_get_request_id(request),
        )

    # Health check
    @application.get("/health")
    async def health_check() -> dict:
        return {"status": "ok"}

    return application


app = create_app()
