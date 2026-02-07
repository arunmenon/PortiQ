"""Tenancy module constants for RLS and multi-tenant isolation."""

# PostgreSQL session variable names (used with set_config)
SESSION_VAR_ORG_ID = "app.current_organization_id"
SESSION_VAR_ORG_TYPE = "app.current_organization_type"
SESSION_VAR_USER_ID = "app.current_user_id"
SESSION_VAR_ADMIN_BYPASS = "app.admin_bypass"

# Metadata keys
METADATA_KEY_CROSS_TENANT = "cross_tenant_access"

# Cache configuration
CACHE_PREFIX = "tenant"
CACHE_TTL_DEFAULT = 300  # seconds

# Routes excluded from tenant context extraction
EXCLUDED_ROUTES = [
    "/auth",
    "/health",
    "/metrics",
    "/api/docs",
    "/api/openapi.json",
    "/api/redoc",
]
