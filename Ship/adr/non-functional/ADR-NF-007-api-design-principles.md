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
- NestJS backend with TypeScript
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

```typescript
// main.ts
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  const config = new DocumentBuilder()
    .setTitle('Ship Chandlery Platform API')
    .setDescription('Maritime B2B procurement platform API')
    .setVersion('1.0')
    .addBearerAuth()
    .addApiKey({ type: 'apiKey', name: 'X-Organization-ID', in: 'header' }, 'organization')
    .addTag('Products', 'Product catalog operations')
    .addTag('RFQs', 'Request for quotation operations')
    .addTag('Orders', 'Order management operations')
    .addTag('Users', 'User management operations')
    .build();

  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('api/docs', app, document, {
    swaggerOptions: {
      persistAuthorization: true
    }
  });

  // Export OpenAPI spec
  if (process.env.EXPORT_OPENAPI) {
    const fs = require('fs');
    fs.writeFileSync('./openapi.json', JSON.stringify(document, null, 2));
  }

  await app.listen(3000);
}
```

### Controller Implementation

```typescript
// products/products.controller.ts
@ApiTags('Products')
@Controller('api/v1/products')
@UseGuards(JwtAuthGuard, OrganizationGuard)
export class ProductsController {
  constructor(private readonly productsService: ProductsService) {}

  @Get()
  @ApiOperation({ summary: 'List products' })
  @ApiQuery({ name: 'category', required: false, description: 'Filter by category ID' })
  @ApiQuery({ name: 'q', required: false, description: 'Search query' })
  @ApiQuery({ name: 'page', required: false, type: Number, default: 1 })
  @ApiQuery({ name: 'limit', required: false, type: Number, default: 20 })
  @ApiResponse({ status: 200, type: ProductListResponse })
  async findAll(
    @Query() query: ProductQueryDto
  ): Promise<ProductListResponse> {
    const result = await this.productsService.findAll(query);
    return this.formatListResponse(result);
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get product by ID' })
  @ApiParam({ name: 'id', description: 'Product ID' })
  @ApiQuery({ name: 'include', required: false, description: 'Related resources to include' })
  @ApiResponse({ status: 200, type: ProductResponse })
  @ApiResponse({ status: 404, description: 'Product not found' })
  async findOne(
    @Param('id', ParseUUIDPipe) id: string,
    @Query('include') include?: string
  ): Promise<ProductResponse> {
    const product = await this.productsService.findById(id, include?.split(','));
    if (!product) {
      throw new NotFoundException('Product not found');
    }
    return this.formatSingleResponse(product);
  }

  @Post()
  @ApiOperation({ summary: 'Create product' })
  @ApiBody({ type: CreateProductDto })
  @ApiResponse({ status: 201, type: ProductResponse })
  @ApiResponse({ status: 400, description: 'Validation error' })
  @RequirePermission('products.create')
  async create(
    @Body() createProductDto: CreateProductDto,
    @CurrentOrganization() org: Organization
  ): Promise<ProductResponse> {
    const product = await this.productsService.create(createProductDto, org.id);
    return this.formatSingleResponse(product);
  }

  @Patch(':id')
  @ApiOperation({ summary: 'Update product' })
  @ApiParam({ name: 'id', description: 'Product ID' })
  @ApiBody({ type: UpdateProductDto })
  @ApiResponse({ status: 200, type: ProductResponse })
  @RequirePermission('products.update')
  async update(
    @Param('id', ParseUUIDPipe) id: string,
    @Body() updateProductDto: UpdateProductDto
  ): Promise<ProductResponse> {
    const product = await this.productsService.update(id, updateProductDto);
    return this.formatSingleResponse(product);
  }

  @Delete(':id')
  @ApiOperation({ summary: 'Delete product' })
  @ApiParam({ name: 'id', description: 'Product ID' })
  @ApiResponse({ status: 204, description: 'Product deleted' })
  @RequirePermission('products.delete')
  @HttpCode(HttpStatus.NO_CONTENT)
  async remove(@Param('id', ParseUUIDPipe) id: string): Promise<void> {
    await this.productsService.remove(id);
  }
}
```

### DTO Validation

```typescript
// products/dto/create-product.dto.ts
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsString, IsNumber, IsOptional, IsUUID, Min, MaxLength, Matches } from 'class-validator';

export class CreateProductDto {
  @ApiProperty({ description: 'IMPA code (6 digits)', example: '123456' })
  @IsString()
  @Matches(/^\d{6}$/, { message: 'IMPA code must be 6 digits' })
  impaCode: string;

  @ApiProperty({ description: 'Product name', example: 'Stainless Steel Bolt M10x50' })
  @IsString()
  @MaxLength(255)
  name: string;

  @ApiPropertyOptional({ description: 'Product description' })
  @IsOptional()
  @IsString()
  description?: string;

  @ApiProperty({ description: 'Category ID' })
  @IsUUID()
  categoryId: string;

  @ApiProperty({ description: 'Base price', example: 10.50 })
  @IsNumber()
  @Min(0)
  basePrice: number;

  @ApiProperty({ description: 'Unit of measure', example: 'PIECE' })
  @IsString()
  unitOfMeasure: string;

  @ApiPropertyOptional({ description: 'Product specifications' })
  @IsOptional()
  specifications?: Record<string, any>;
}
```

### Error Handling

```typescript
// common/filters/http-exception.filter.ts
@Catch()
export class AllExceptionsFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost): void {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<Request>();

    let status = HttpStatus.INTERNAL_SERVER_ERROR;
    let errorResponse: ApiErrorResponse;

    if (exception instanceof HttpException) {
      status = exception.getStatus();
      const exceptionResponse = exception.getResponse();

      errorResponse = {
        error: {
          code: this.getErrorCode(status),
          message: typeof exceptionResponse === 'string'
            ? exceptionResponse
            : (exceptionResponse as any).message,
          details: (exceptionResponse as any).details,
          requestId: request.headers['x-request-id'] as string
        }
      };
    } else {
      errorResponse = {
        error: {
          code: 'INTERNAL_ERROR',
          message: 'An unexpected error occurred',
          requestId: request.headers['x-request-id'] as string
        }
      };

      // Log actual error for debugging
      this.logger.error('Unhandled exception', exception);
    }

    response.status(status).json(errorResponse);
  }

  private getErrorCode(status: number): string {
    const codes: Record<number, string> = {
      400: 'BAD_REQUEST',
      401: 'UNAUTHORIZED',
      403: 'FORBIDDEN',
      404: 'NOT_FOUND',
      409: 'CONFLICT',
      422: 'VALIDATION_ERROR',
      429: 'TOO_MANY_REQUESTS',
      500: 'INTERNAL_ERROR'
    };
    return codes[status] || 'UNKNOWN_ERROR';
  }
}
```

### Versioning Strategy

```typescript
// main.ts
app.enableVersioning({
  type: VersioningType.URI,
  defaultVersion: '1'
});

// With versioning, controllers can specify versions
@Controller({
  path: 'products',
  version: '1'
})
export class ProductsV1Controller {}

@Controller({
  path: 'products',
  version: '2'
})
export class ProductsV2Controller {}

// URL: /api/v1/products, /api/v2/products
```

### Dependencies
- ADR-NF-006: Modular Monolith vs Microservices
- ADR-NF-015: Authentication Strategy
- ADR-NF-016: API Security & Rate Limiting

### Migration Strategy
1. Establish API design guidelines document
2. Set up OpenAPI/Swagger in NestJS
3. Create base response DTOs
4. Implement exception filters
5. Generate initial API documentation
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
- [NestJS OpenAPI](https://docs.nestjs.com/openapi/introduction)
- [REST API Design Guidelines](https://docs.microsoft.com/en-us/azure/architecture/best-practices/api-design)
- [JSON:API Specification](https://jsonapi.org/)
