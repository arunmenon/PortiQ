# ADR-NF-007: API Design Principles

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

The platform requires a well-designed API layer serving web frontends, mobile apps, and potential third-party integrations.

### Business Context
The API serves multiple consumers:
- Next.js web application (buyer portal, supplier dashboard)
- React Native mobile apps
- ERP integrations (AMOS, SERTICA)
- Potential partner/third-party integrations
- Internal tooling and admin interfaces

Consistency, discoverability, and developer experience are critical.

### Technical Context
- FastAPI backend with Python
- Multiple client applications
- Need for API documentation
- Versioning for breaking changes
- Security considerations

### Assumptions
- REST is sufficient for most operations
- WebSocket needed for real-time features (separate)
- GraphQL complexity not justified currently
- API-first design approach

---

## Decision Drivers

- Developer experience (internal and external)
- Consistency across endpoints
- Documentation and discoverability
- Versioning strategy
- Performance considerations
- Security by design

---

## Considered Options

### Option 1: REST with OpenAPI 3.0
**Description:** RESTful API design with OpenAPI specification for documentation.

**Pros:**
- Industry standard
- Excellent tooling
- Auto-generated documentation
- Client SDK generation
- Wide understanding
- Caching friendly

**Cons:**
- Over/under-fetching
- Multiple roundtrips sometimes needed
- Versioning challenges

### Option 2: GraphQL
**Description:** Single endpoint with flexible querying.

**Pros:**
- Flexible queries
- No over/under-fetching
- Strong typing
- Single endpoint

**Cons:**
- Complexity overhead
- Caching challenges
- Learning curve
- N+1 query problems

### Option 3: gRPC
**Description:** High-performance RPC framework with Protocol Buffers.

**Pros:**
- High performance
- Strong typing
- Bi-directional streaming
- Generated clients

**Cons:**
- Browser support limited
- Learning curve
- Debugging harder
- Not RESTful

---

## Decision

**Chosen Option:** REST with OpenAPI 3.0

We will implement RESTful APIs following MACH principles (Microservices-based, API-first, Cloud-native, Headless) with OpenAPI 3.0 specification for documentation and client generation.

### Rationale
REST is the most widely understood API pattern, with excellent tooling and documentation support via OpenAPI. The additional flexibility of GraphQL doesn't justify its complexity for our use case. MACH principles ensure modern, composable architecture even within a modular monolith.

---

## Consequences

### Positive
- Wide understanding and adoption
- Excellent documentation with Swagger
- Client SDK generation
- Standard HTTP caching
- Easy debugging and testing

### Negative
- Multiple requests for related resources
- **Mitigation:** Use includes/expand patterns, compound documents
- Versioning requires planning
- **Mitigation:** URL versioning, deprecation strategy

### Risks
- API inconsistency: Design guidelines, code reviews, linting
- Documentation drift: Generate from code, automated validation
- Breaking changes: Versioning strategy, deprecation periods

---

## Implementation Notes

### API Design Guidelines

```typescript
// URL Structure
// Base: /api/v1/{resource}

// Collection operations
GET    /api/v1/products           # List products
POST   /api/v1/products           # Create product

// Single resource operations
GET    /api/v1/products/:id       # Get product
PATCH  /api/v1/products/:id       # Update product
DELETE /api/v1/products/:id       # Delete product

// Nested resources
GET    /api/v1/rfqs/:id/quotes    # List quotes for RFQ
POST   /api/v1/rfqs/:id/quotes    # Create quote for RFQ

// Actions (non-CRUD)
POST   /api/v1/rfqs/:id/publish   # Publish RFQ
POST   /api/v1/rfqs/:id/cancel    # Cancel RFQ

// Search/Filter
GET    /api/v1/products?category=123&minPrice=100
GET    /api/v1/products?q=stainless+bolt

// Pagination
GET    /api/v1/products?page=2&limit=20

// Sorting
GET    /api/v1/products?sort=price:asc,name:desc

// Field selection
GET    /api/v1/products?fields=id,name,price

// Include related resources
GET    /api/v1/products?include=category,supplier
```

### Response Format

```typescript
// Success response (single resource)
{
  "data": {
    "id": "uuid",
    "type": "product",
    "attributes": {
      "name": "Stainless Steel Bolt",
      "impaCode": "123456",
      "price": 10.50
    },
    "relationships": {
      "category": {
        "data": { "id": "cat-uuid", "type": "category" }
      }
    }
  },
  "included": [
    {
      "id": "cat-uuid",
      "type": "category",
      "attributes": { "name": "Fasteners" }
    }
  ],
  "meta": {
    "requestId": "req-uuid"
  }
}

// Success response (collection)
{
  "data": [
    { "id": "1", "type": "product", "attributes": {...} },
    { "id": "2", "type": "product", "attributes": {...} }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "limit": 20,
      "totalItems": 150,
      "totalPages": 8
    },
    "requestId": "req-uuid"
  },
  "links": {
    "self": "/api/v1/products?page=1",
    "next": "/api/v1/products?page=2",
    "last": "/api/v1/products?page=8"
  }
}

// Error response
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      {
        "field": "price",
        "message": "Price must be a positive number"
      }
    ],
    "requestId": "req-uuid"
  }
}
```

### OpenAPI Configuration

```python
# src/app.py
from fastapi import FastAPI

app = FastAPI(
    title="Ship Chandlery Platform API",
    description="Maritime B2B procurement platform API",
    version="1.0.0",
    docs_url="/api/docs",        # Swagger UI
    redoc_url="/api/redoc",      # ReDoc
    openapi_url="/api/openapi.json",
)

# FastAPI auto-generates OpenAPI 3.1 spec from route type hints and Pydantic models
# No manual DocumentBuilder needed — schema is derived from code
```

### Router Implementation

```python
# src/modules/catalog/router.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from src.database.session import get_db
from src.modules.tenancy.dependencies import get_tenant_context
from .schemas import (
    CreateProductDto, UpdateProductDto, ProductResponse, ProductListResponse, ProductQueryDto,
)
from .service import ProductsService

router = APIRouter(prefix="/api/v1/products", tags=["Products"])

@router.get("/", response_model=ProductListResponse, summary="List products")
async def list_products(
    category: UUID | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    tenant=Depends(get_tenant_context),
):
    service = ProductsService(db)
    return await service.find_all(
        ProductQueryDto(category=category, q=q, page=page, limit=limit)
    )

@router.get("/{product_id}", response_model=ProductResponse, summary="Get product by ID")
async def get_product(
    product_id: UUID,
    include: str | None = None,
    db=Depends(get_db),
):
    service = ProductsService(db)
    product = await service.find_by_id(product_id, include.split(",") if include else None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED, summary="Create product")
async def create_product(
    dto: CreateProductDto,
    db=Depends(get_db),
    tenant=Depends(get_tenant_context),
):
    service = ProductsService(db)
    return await service.create(dto, tenant.organization_id)

@router.patch("/{product_id}", response_model=ProductResponse, summary="Update product")
async def update_product(product_id: UUID, dto: UpdateProductDto, db=Depends(get_db)):
    service = ProductsService(db)
    return await service.update(product_id, dto)

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete product")
async def delete_product(product_id: UUID, db=Depends(get_db)):
    service = ProductsService(db)
    await service.remove(product_id)
```

### DTO Validation

```python
# src/modules/catalog/schemas.py
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
import re

class CreateProductDto(BaseModel):
    impa_code: str = Field(..., description="IMPA code (6 digits)", examples=["123456"])
    name: str = Field(..., max_length=255, description="Product name", examples=["Stainless Steel Bolt M10x50"])
    description: str | None = Field(None, description="Product description")
    category_id: UUID = Field(..., description="Category ID")
    base_price: float = Field(..., ge=0, description="Base price", examples=[10.50])
    unit_of_measure: str = Field(..., description="Unit of measure", examples=["PIECE"])
    specifications: dict | None = Field(None, description="Product specifications")

    @field_validator("impa_code")
    @classmethod
    def validate_impa_code(cls, v: str) -> str:
        if not re.match(r"^\d{6}$", v):
            raise ValueError("IMPA code must be 6 digits")
        return v
```

### Error Handling

```python
# src/app.py — Exception handlers
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

logger = logging.getLogger(__name__)

ERROR_CODES = {400: "BAD_REQUEST", 401: "UNAUTHORIZED", 403: "FORBIDDEN",
               404: "NOT_FOUND", 409: "CONFLICT", 422: "VALIDATION_ERROR",
               429: "TOO_MANY_REQUESTS", 500: "INTERNAL_ERROR"}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Validation failed",
            "details": exc.errors(),
            "requestId": request.headers.get("x-request-id"),
        }
    })

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(status_code=500, content={
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "requestId": request.headers.get("x-request-id"),
        }
    })
```

### Versioning Strategy

```python
# src/app.py — URL-based versioning via router prefixes
from fastapi import APIRouter

v1_router = APIRouter(prefix="/api/v1")
v2_router = APIRouter(prefix="/api/v2")

# src/modules/catalog/router.py
router = APIRouter(prefix="/products", tags=["Products"])

# Registration:
v1_router.include_router(catalog_v1_router)
v2_router.include_router(catalog_v2_router)
app.include_router(v1_router)
app.include_router(v2_router)
# URLs: /api/v1/products, /api/v2/products
```

### Dependencies
- ADR-NF-006: Modular Monolith vs Microservices
- ADR-NF-015: Authentication Strategy
- ADR-NF-016: API Security & Rate Limiting

### Migration Strategy
1. Establish API design guidelines document
2. Set up FastAPI with auto-generated OpenAPI/Swagger
3. Create base response Pydantic models
4. Implement exception handlers
5. Generate initial API documentation (auto from FastAPI)
6. Set up client SDK generation
7. Create API versioning strategy

---

## API Standards

### Versioning Strategy

| Aspect | Standard |
|--------|----------|
| **Version Format** | URL path: `/api/v1/`, `/api/v2/` |
| **Deprecation Notice** | 6 months minimum before removal |
| **Deprecation Header** | `Deprecation: true`, `Sunset: <date>` |
| **Parallel Support** | 2 major versions maximum |
| **Breaking Changes** | New major version required |

**Non-Breaking Changes (no version bump):**
- Adding new endpoints
- Adding optional fields to responses
- Adding optional query parameters
- Adding new enum values (if clients handle unknown)

**Breaking Changes (requires new version):**
- Removing or renaming fields
- Changing field types
- Removing endpoints
- Changing authentication

### Error Schema

```typescript
// Standard error codes and HTTP status mapping
const ERROR_CODES = {
  // 400 Bad Request
  VALIDATION_ERROR: { status: 400, message: 'Validation failed' },
  INVALID_INPUT: { status: 400, message: 'Invalid input provided' },

  // 401 Unauthorized
  UNAUTHORIZED: { status: 401, message: 'Authentication required' },
  TOKEN_EXPIRED: { status: 401, message: 'Token has expired' },

  // 403 Forbidden
  FORBIDDEN: { status: 403, message: 'Access denied' },
  INSUFFICIENT_PERMISSIONS: { status: 403, message: 'Insufficient permissions' },

  // 404 Not Found
  NOT_FOUND: { status: 404, message: 'Resource not found' },

  // 409 Conflict
  CONFLICT: { status: 409, message: 'Resource conflict' },
  DUPLICATE_ENTRY: { status: 409, message: 'Duplicate entry exists' },

  // 422 Unprocessable Entity
  BUSINESS_RULE_VIOLATION: { status: 422, message: 'Business rule violated' },

  // 429 Too Many Requests
  RATE_LIMITED: { status: 429, message: 'Rate limit exceeded' },

  // 500 Internal Server Error
  INTERNAL_ERROR: { status: 500, message: 'Internal server error' },
  SERVICE_UNAVAILABLE: { status: 503, message: 'Service temporarily unavailable' }
};
```

### Pagination Standards

```typescript
// Cursor-based pagination (preferred for large datasets)
GET /api/v1/orders?cursor=eyJpZCI6MTIzfQ&limit=20

Response:
{
  "data": [...],
  "meta": {
    "pagination": {
      "limit": 20,
      "hasMore": true,
      "nextCursor": "eyJpZCI6MTQzfQ"
    }
  }
}

// Offset-based pagination (for smaller, stable datasets)
GET /api/v1/products?page=2&limit=20

Response:
{
  "data": [...],
  "meta": {
    "pagination": {
      "page": 2,
      "limit": 20,
      "totalItems": 150,
      "totalPages": 8
    }
  },
  "links": {
    "first": "/api/v1/products?page=1&limit=20",
    "prev": "/api/v1/products?page=1&limit=20",
    "next": "/api/v1/products?page=3&limit=20",
    "last": "/api/v1/products?page=8&limit=20"
  }
}
```

| Use Case | Pagination Type | Max Limit |
|----------|-----------------|-----------|
| Products listing | Offset | 100 |
| Orders history | Cursor | 50 |
| Audit logs | Cursor | 100 |
| Search results | Offset | 50 |

## Idempotency and Consistency

### Idempotency Requirements

| Operation | Idempotent | Idempotency Key Required |
|-----------|------------|--------------------------|
| GET | Yes (inherently) | No |
| POST (create) | No | Yes - `Idempotency-Key` header |
| PUT (full update) | Yes (inherently) | No |
| PATCH (partial) | No | Recommended |
| DELETE | Yes (inherently) | No |

```typescript
// Idempotency implementation
@Post()
async createOrder(
  @Headers('Idempotency-Key') idempotencyKey: string,
  @Body() dto: CreateOrderDto
): Promise<Order> {
  if (!idempotencyKey) {
    throw new BadRequestException('Idempotency-Key header required');
  }

  // Check for existing request with same key
  const existing = await this.idempotencyService.get(idempotencyKey);
  if (existing) {
    return existing.response; // Return cached response
  }

  const order = await this.ordersService.create(dto);
  await this.idempotencyService.store(idempotencyKey, order, '24h');
  return order;
}
```

### Consistency Guarantees

| Endpoint Type | Consistency | Notes |
|---------------|-------------|-------|
| Read (single resource) | Strong | Always from primary |
| Read (list/search) | Eventual | May use read replica |
| Write operations | Strong | Always to primary |
| Aggregations/reports | Eventual | Acceptable 30s lag |

### Rate Limit Headers

All responses include rate limit information:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000
Retry-After: 60  # Only on 429 responses
```

### Retry Semantics

| Status Code | Retry | Backoff Strategy |
|-------------|-------|------------------|
| 429 | Yes | Use `Retry-After` header |
| 500 | Yes | Exponential: 1s, 2s, 4s (max 3) |
| 502, 503, 504 | Yes | Exponential: 1s, 2s, 4s (max 3) |
| 4xx (except 429) | No | Fix request, don't retry |

```typescript
// Client retry configuration example
const retryConfig = {
  maxRetries: 3,
  retryOn: [429, 500, 502, 503, 504],
  backoff: (attempt: number, response?: Response) => {
    if (response?.status === 429) {
      return parseInt(response.headers.get('Retry-After') || '60') * 1000;
    }
    return Math.pow(2, attempt) * 1000; // Exponential backoff
  }
};
```

---

## References
- [OpenAPI Specification](https://spec.openapis.org/oas/v3.1.0)
- [FastAPI OpenAPI](https://fastapi.tiangolo.com/tutorial/metadata/)
- [REST API Design Guidelines](https://docs.microsoft.com/en-us/azure/architecture/best-practices/api-design)
- [JSON:API Specification](https://jsonapi.org/)
