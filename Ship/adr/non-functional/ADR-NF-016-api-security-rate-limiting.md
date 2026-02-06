# ADR-NF-016: API Security & Rate Limiting

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Security

---

## Context

The platform requires comprehensive API security measures to protect against abuse, attacks, and ensure fair usage across tenants.

### Business Context
Security requirements:
- Protect financial and procurement data
- Prevent API abuse and scraping
- Ensure fair resource allocation across tenants
- Comply with security standards
- Protect against common web attacks
- Support rate limits for different user tiers

### Technical Context
- NestJS API backend (ADR-NF-006)
- JWT authentication (ADR-NF-015)
- Multi-tenant architecture (ADR-FN-023)
- AWS infrastructure with ALB (ADR-NF-011)
- Redis available for rate limiting state

### Assumptions
- Rate limiting at application level with Redis
- WAF provides additional protection layer
- Different rate limits per tenant tier
- API versioning handled via URL path
- Webhooks need separate rate limiting

---

## Decision Drivers

- Protection against abuse
- Fair resource distribution
- Performance impact
- Operational simplicity
- Compliance requirements
- Developer experience

---

## Considered Options

### Option 1: Application-Level Rate Limiting (Redis)
**Description:** Rate limiting in NestJS using Redis for distributed state.

**Pros:**
- Fine-grained control
- Tenant-aware limits
- Custom response handling
- Easy to adjust dynamically
- Full visibility

**Cons:**
- Additional Redis load
- Implementation complexity
- Not at network edge

### Option 2: API Gateway (Kong/AWS API Gateway)
**Description:** Dedicated API gateway for rate limiting.

**Pros:**
- Network-edge protection
- Built-in rate limiting
- Policy management
- Additional features (caching, auth)

**Cons:**
- Additional infrastructure
- Cost
- Potential latency
- Less customization

### Option 3: CloudFront + WAF Only
**Description:** Use CloudFront and WAF rules for protection.

**Pros:**
- Edge protection
- Scales automatically
- DDoS protection built-in

**Cons:**
- Less granular control
- Limited tenant awareness
- WAF rule limitations

---

## Decision

**Chosen Option:** Application-Level Rate Limiting + WAF

We will implement application-level rate limiting using @nestjs/throttler with Redis backend, combined with AWS WAF for edge protection against attacks.

### Rationale
Application-level rate limiting provides tenant-aware, fine-grained control needed for a multi-tenant B2B platform. Different organizations can have different limits based on their subscription tier. WAF adds an additional security layer at the edge for DDoS and common attack protection.

---

## Consequences

### Positive
- Tenant-aware rate limiting
- Dynamic limit adjustment
- Custom response handling
- Multiple protection layers
- Full audit capability

### Negative
- Redis dependency for rate limiting
- **Mitigation:** Redis cluster, fallback behavior
- Implementation complexity
- **Mitigation:** Standard patterns, thorough testing

### Risks
- Rate limiter bypass: Multiple layers, monitoring
- Redis failure: Fail-open or fail-closed strategy
- False positives: Generous limits, alerting, manual override

---

## Implementation Notes

### Security Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │                   Internet                   │
                    └────────────────────┬────────────────────────┘
                                         │
                    ┌────────────────────▼────────────────────────┐
                    │            CloudFront + WAF                  │
                    │  - DDoS Protection (Shield)                  │
                    │  - SQL Injection Rules                       │
                    │  - XSS Rules                                 │
                    │  - Rate Limiting (rough)                     │
                    └────────────────────┬────────────────────────┘
                                         │
                    ┌────────────────────▼────────────────────────┐
                    │         Application Load Balancer            │
                    │  - TLS Termination                           │
                    │  - Health Checks                             │
                    └────────────────────┬────────────────────────┘
                                         │
                    ┌────────────────────▼────────────────────────┐
                    │              NestJS Application              │
                    │  - Authentication (JWT)                      │
                    │  - Rate Limiting (Redis-backed)              │
                    │  - Input Validation                          │
                    │  - CORS                                      │
                    │  - Helmet Security Headers                   │
                    └─────────────────────────────────────────────┘
```

### Rate Limiting Configuration

```typescript
// rate-limiting/rate-limiting.module.ts
import { ThrottlerModule, ThrottlerGuard } from '@nestjs/throttler';
import { ThrottlerStorageRedisService } from 'nestjs-throttler-storage-redis';

@Module({
  imports: [
    ThrottlerModule.forRootAsync({
      imports: [ConfigModule],
      useFactory: (configService: ConfigService) => ({
        throttlers: [
          {
            name: 'short',
            ttl: 1000,  // 1 second
            limit: 10,  // 10 requests per second
          },
          {
            name: 'medium',
            ttl: 60000, // 1 minute
            limit: 100, // 100 requests per minute
          },
          {
            name: 'long',
            ttl: 3600000, // 1 hour
            limit: 1000,  // 1000 requests per hour
          },
        ],
        storage: new ThrottlerStorageRedisService({
          host: configService.get('REDIS_HOST'),
          port: configService.get('REDIS_PORT'),
          password: configService.get('REDIS_PASSWORD'),
        }),
      }),
      inject: [ConfigService],
    }),
  ],
  providers: [
    {
      provide: APP_GUARD,
      useClass: CustomThrottlerGuard,
    },
  ],
})
export class RateLimitingModule {}
```

### Custom Throttler Guard

```typescript
// rate-limiting/guards/custom-throttler.guard.ts
@Injectable()
export class CustomThrottlerGuard extends ThrottlerGuard {
  constructor(
    private readonly tenantService: TenantService,
    private readonly rateLimitService: RateLimitService,
    options: ThrottlerModuleOptions,
    storageService: ThrottlerStorageService,
    reflector: Reflector,
  ) {
    super(options, storageService, reflector);
  }

  async handleRequest(
    context: ExecutionContext,
    limit: number,
    ttl: number,
    throttler: ThrottlerGenerateKeyFunction,
  ): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const user = request.user;

    // Get tenant-specific limits
    if (user?.organizationId) {
      const tenantLimits = await this.tenantService.getRateLimits(
        user.organizationId
      );

      if (tenantLimits) {
        limit = tenantLimits.requestsPerMinute;
      }
    }

    // Use organization ID or IP as key
    const key = user?.organizationId || request.ip;

    const { totalHits, timeToExpire } = await this.storageService.increment(
      `rate_limit:${key}`,
      ttl,
    );

    if (totalHits > limit) {
      // Log rate limit hit
      await this.rateLimitService.recordLimitExceeded(key, {
        endpoint: request.url,
        method: request.method,
        userId: user?.id,
        organizationId: user?.organizationId,
      });

      throw new ThrottlerException('Rate limit exceeded');
    }

    // Add rate limit headers
    const response = context.switchToHttp().getResponse();
    response.header('X-RateLimit-Limit', limit);
    response.header('X-RateLimit-Remaining', Math.max(0, limit - totalHits));
    response.header('X-RateLimit-Reset', Date.now() + timeToExpire);

    return true;
  }

  protected getTracker(req: Record<string, any>): Promise<string> {
    // Use organization ID for authenticated requests, IP for anonymous
    return req.user?.organizationId || req.ip;
  }
}
```

### Endpoint-Specific Rate Limits

```typescript
// rate-limiting/decorators/rate-limit.decorator.ts
import { Throttle, SkipThrottle } from '@nestjs/throttler';

// Skip rate limiting for health checks
@SkipThrottle()
@Controller('health')
export class HealthController {}

// Strict limits for auth endpoints
@Controller('api/v1/auth')
export class AuthController {
  @Post('login')
  @Throttle({ default: { limit: 5, ttl: 60000 } }) // 5 per minute
  async login() {}

  @Post('forgot-password')
  @Throttle({ default: { limit: 3, ttl: 60000 } }) // 3 per minute
  async forgotPassword() {}
}

// Higher limits for search
@Controller('api/v1/products')
export class ProductController {
  @Get('search')
  @Throttle({ default: { limit: 30, ttl: 60000 } }) // 30 per minute
  async search() {}

  @Get(':id')
  @Throttle({ default: { limit: 60, ttl: 60000 } }) // 60 per minute
  async getProduct() {}
}

// Bulk operations have lower limits
@Controller('api/v1/import')
export class ImportController {
  @Post('products')
  @Throttle({ default: { limit: 5, ttl: 3600000 } }) // 5 per hour
  async importProducts() {}
}
```

### Tier-Based Rate Limits

```typescript
// rate-limiting/services/rate-limit.service.ts
@Injectable()
export class RateLimitService {
  private readonly TIER_LIMITS: Record<string, TierLimits> = {
    free: {
      requestsPerMinute: 60,
      requestsPerHour: 500,
      requestsPerDay: 5000,
      bulkOperationsPerDay: 5,
    },
    starter: {
      requestsPerMinute: 200,
      requestsPerHour: 2000,
      requestsPerDay: 20000,
      bulkOperationsPerDay: 20,
    },
    professional: {
      requestsPerMinute: 500,
      requestsPerHour: 10000,
      requestsPerDay: 100000,
      bulkOperationsPerDay: 100,
    },
    enterprise: {
      requestsPerMinute: 2000,
      requestsPerHour: 50000,
      requestsPerDay: 500000,
      bulkOperationsPerDay: 1000,
    },
  };

  async getLimitsForOrganization(organizationId: string): Promise<TierLimits> {
    const org = await this.organizationRepository.findOne({
      where: { id: organizationId },
      select: ['subscriptionTier'],
    });

    return this.TIER_LIMITS[org?.subscriptionTier || 'free'];
  }

  async recordLimitExceeded(
    key: string,
    metadata: RateLimitMetadata
  ): Promise<void> {
    await this.redis.hincrby(`rate_limit_exceeded:${key}`, 'count', 1);

    this.eventEmitter.emit('rate_limit.exceeded', {
      key,
      ...metadata,
      timestamp: new Date(),
    });
  }

  async getRateLimitStats(organizationId: string): Promise<RateLimitStats> {
    const usage = await this.redis.hgetall(`rate_limit:${organizationId}`);
    const limits = await this.getLimitsForOrganization(organizationId);

    return {
      usage: {
        minute: parseInt(usage.minute || '0'),
        hour: parseInt(usage.hour || '0'),
        day: parseInt(usage.day || '0'),
      },
      limits,
      remainingRequests: {
        minute: Math.max(0, limits.requestsPerMinute - (parseInt(usage.minute || '0'))),
        hour: Math.max(0, limits.requestsPerHour - (parseInt(usage.hour || '0'))),
        day: Math.max(0, limits.requestsPerDay - (parseInt(usage.day || '0'))),
      },
    };
  }
}
```

### WAF Configuration

```hcl
# terraform/modules/waf/main.tf

resource "aws_wafv2_web_acl" "api" {
  name        = "ship-chandlery-api-waf"
  description = "WAF rules for API protection"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  # Rate limiting at edge (coarse)
  rule {
    name     = "RateLimitRule"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitRule"
      sampled_requests_enabled   = true
    }
  }

  # AWS Managed Rules - Common attacks
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "CommonRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # SQL Injection protection
  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "SQLiRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # Known bad inputs
  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 4

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "KnownBadInputs"
      sampled_requests_enabled   = true
    }
  }

  # Block known bad IP addresses
  rule {
    name     = "AWSManagedRulesAmazonIpReputationList"
    priority = 5

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAmazonIpReputationList"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "IpReputationList"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "ship-chandlery-waf"
    sampled_requests_enabled   = true
  }
}

# Associate WAF with ALB
resource "aws_wafv2_web_acl_association" "api" {
  resource_arn = aws_lb.api.arn
  web_acl_arn  = aws_wafv2_web_acl.api.arn
}
```

### Security Headers Middleware

```typescript
// security/middleware/security-headers.middleware.ts
import helmet from 'helmet';

// main.ts
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      scriptSrc: ["'self'"],
      imgSrc: ["'self'", 'data:', 'https://cdn.shipchandlery.com'],
      connectSrc: ["'self'", 'https://api.shipchandlery.com'],
      fontSrc: ["'self'"],
      objectSrc: ["'none'"],
      mediaSrc: ["'self'"],
      frameSrc: ["'none'"],
    },
  },
  crossOriginEmbedderPolicy: true,
  crossOriginOpenerPolicy: true,
  crossOriginResourcePolicy: { policy: 'same-site' },
  dnsPrefetchControl: { allow: false },
  frameguard: { action: 'deny' },
  hsts: {
    maxAge: 31536000,
    includeSubDomains: true,
    preload: true,
  },
  ieNoOpen: true,
  noSniff: true,
  originAgentCluster: true,
  permittedCrossDomainPolicies: { permittedPolicies: 'none' },
  referrerPolicy: { policy: 'strict-origin-when-cross-origin' },
  xssFilter: true,
}));
```

### CORS Configuration

```typescript
// main.ts
app.enableCors({
  origin: (origin, callback) => {
    const allowedOrigins = [
      'https://shipchandlery.com',
      'https://app.shipchandlery.com',
      'https://admin.shipchandlery.com',
    ];

    if (process.env.NODE_ENV === 'development') {
      allowedOrigins.push('http://localhost:3000');
    }

    if (!origin || allowedOrigins.includes(origin)) {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true,
  methods: ['GET', 'HEAD', 'PUT', 'PATCH', 'POST', 'DELETE', 'OPTIONS'],
  allowedHeaders: [
    'Content-Type',
    'Authorization',
    'X-Requested-With',
    'X-Device-ID',
    'X-Correlation-ID',
  ],
  exposedHeaders: [
    'X-RateLimit-Limit',
    'X-RateLimit-Remaining',
    'X-RateLimit-Reset',
    'X-Request-ID',
  ],
  maxAge: 86400, // 24 hours
});
```

### Input Validation

```typescript
// common/pipes/validation.pipe.ts
app.useGlobalPipes(
  new ValidationPipe({
    whitelist: true,           // Strip unknown properties
    forbidNonWhitelisted: true, // Throw on unknown properties
    transform: true,            // Transform to DTO types
    transformOptions: {
      enableImplicitConversion: false,
    },
    validationError: {
      target: false,
      value: false,
    },
  }),
);

// Example DTO with validation
export class CreateOrderDto {
  @IsUUID()
  supplierId: string;

  @IsArray()
  @ArrayMinSize(1)
  @ArrayMaxSize(100)
  @ValidateNested({ each: true })
  @Type(() => OrderLineItemDto)
  lineItems: OrderLineItemDto[];

  @IsOptional()
  @IsString()
  @MaxLength(500)
  @Transform(({ value }) => sanitizeHtml(value))
  notes?: string;
}
```

### API Key Authentication for Integrations

```typescript
// auth/strategies/api-key.strategy.ts
@Injectable()
export class ApiKeyStrategy extends PassportStrategy(Strategy, 'api-key') {
  constructor(
    private readonly apiKeyService: ApiKeyService,
  ) {
    super({
      header: 'X-API-Key',
      prefix: '',
    });
  }

  async validate(apiKey: string): Promise<ApiKeyContext> {
    const keyData = await this.apiKeyService.validate(apiKey);

    if (!keyData) {
      throw new UnauthorizedException('Invalid API key');
    }

    // Check rate limits for API key
    await this.apiKeyService.checkRateLimit(keyData.id);

    return {
      keyId: keyData.id,
      organizationId: keyData.organizationId,
      scopes: keyData.scopes,
    };
  }
}

// API Key management
@Injectable()
export class ApiKeyService {
  async create(organizationId: string, dto: CreateApiKeyDto): Promise<ApiKeyCreated> {
    const rawKey = crypto.randomBytes(32).toString('base64url');
    const hashedKey = crypto.createHash('sha256').update(rawKey).digest('hex');

    const apiKey = await this.apiKeyRepository.save({
      organizationId,
      name: dto.name,
      keyHash: hashedKey,
      keyPrefix: rawKey.substring(0, 8),
      scopes: dto.scopes,
      expiresAt: dto.expiresAt,
    });

    // Return raw key only once
    return {
      id: apiKey.id,
      key: rawKey,
      prefix: apiKey.keyPrefix,
      expiresAt: apiKey.expiresAt,
    };
  }

  async validate(rawKey: string): Promise<ApiKey | null> {
    const hashedKey = crypto.createHash('sha256').update(rawKey).digest('hex');

    const apiKey = await this.apiKeyRepository.findOne({
      where: {
        keyHash: hashedKey,
        isActive: true,
      },
      relations: ['organization'],
    });

    if (!apiKey) return null;

    if (apiKey.expiresAt && apiKey.expiresAt < new Date()) {
      return null;
    }

    // Update last used
    await this.apiKeyRepository.update(apiKey.id, {
      lastUsedAt: new Date(),
    });

    return apiKey;
  }
}
```

### Dependencies
- ADR-NF-015: Authentication Strategy
- ADR-NF-011: Cloud Provider - AWS Mumbai
- ADR-NF-005: Caching Strategy (Redis)

### Migration Strategy
1. Implement rate limiting module
2. Configure WAF rules
3. Add security headers middleware
4. Set up CORS properly
5. Implement input validation
6. Add API key authentication
7. Set up monitoring and alerting
8. Test under load

---

## Operational Considerations

### Per-Tenant Rate Limit Policy

**Tier-Based Rate Limits:**

| Tier | Requests/Minute | Requests/Hour | Requests/Day | Burst Capacity | Monthly Price |
|------|-----------------|---------------|--------------|----------------|---------------|
| Free | 60 | 500 | 5,000 | 2x for 10s | $0 |
| Starter | 200 | 2,000 | 20,000 | 3x for 15s | $99 |
| Professional | 500 | 10,000 | 100,000 | 4x for 20s | $499 |
| Enterprise | 2,000 | 50,000 | 500,000 | 5x for 30s | Custom |

**Endpoint-Specific Limits (Applied on top of tier limits):**

| Endpoint Category | Limit Multiplier | Burst Allowed | Rationale |
|-------------------|------------------|---------------|-----------|
| `/api/v1/auth/login` | 0.1x | No | Prevent brute force |
| `/api/v1/auth/register` | 0.05x | No | Prevent spam accounts |
| `/api/v1/auth/forgot-password` | 0.05x | No | Prevent enumeration |
| `/api/v1/products/search` | 1.5x | Yes | High-frequency legitimate use |
| `/api/v1/catalog/*` | 1.5x | Yes | Read-heavy operations |
| `/api/v1/orders` (POST) | 0.5x | No | Prevent order spam |
| `/api/v1/rfq` (POST) | 0.3x | No | Resource-intensive |
| `/api/v1/import/*` | 0.1x | No | Bulk operations |
| `/api/v1/export/*` | 0.2x | No | Resource-intensive |

**Rate Limit Implementation:**

```typescript
// rate-limiting/services/tenant-rate-limit.service.ts
@Injectable()
export class TenantRateLimitService {
  private readonly TIER_CONFIGS: Record<SubscriptionTier, RateLimitConfig> = {
    free: {
      requestsPerMinute: 60,
      requestsPerHour: 500,
      requestsPerDay: 5000,
      burstMultiplier: 2,
      burstDurationSeconds: 10,
    },
    starter: {
      requestsPerMinute: 200,
      requestsPerHour: 2000,
      requestsPerDay: 20000,
      burstMultiplier: 3,
      burstDurationSeconds: 15,
    },
    professional: {
      requestsPerMinute: 500,
      requestsPerHour: 10000,
      requestsPerDay: 100000,
      burstMultiplier: 4,
      burstDurationSeconds: 20,
    },
    enterprise: {
      requestsPerMinute: 2000,
      requestsPerHour: 50000,
      requestsPerDay: 500000,
      burstMultiplier: 5,
      burstDurationSeconds: 30,
    },
  };

  private readonly ENDPOINT_MULTIPLIERS: Record<string, EndpointConfig> = {
    'POST:/api/v1/auth/login': { multiplier: 0.1, allowBurst: false },
    'POST:/api/v1/auth/register': { multiplier: 0.05, allowBurst: false },
    'GET:/api/v1/products/search': { multiplier: 1.5, allowBurst: true },
    'POST:/api/v1/orders': { multiplier: 0.5, allowBurst: false },
    'POST:/api/v1/import/*': { multiplier: 0.1, allowBurst: false },
  };

  async checkRateLimit(
    organizationId: string,
    endpoint: string,
    method: string,
  ): Promise<RateLimitResult> {
    const org = await this.getOrganization(organizationId);
    const tierConfig = this.TIER_CONFIGS[org.subscriptionTier];
    const endpointConfig = this.getEndpointConfig(method, endpoint);

    const effectiveLimit = Math.floor(
      tierConfig.requestsPerMinute * endpointConfig.multiplier
    );

    // Check minute window
    const minuteKey = `ratelimit:${organizationId}:minute:${Math.floor(Date.now() / 60000)}`;
    const minuteCount = await this.redis.incr(minuteKey);
    await this.redis.expire(minuteKey, 60);

    // Check burst allowance
    const inBurst = await this.checkBurstStatus(organizationId, tierConfig);
    const currentLimit = inBurst && endpointConfig.allowBurst
      ? effectiveLimit * tierConfig.burstMultiplier
      : effectiveLimit;

    if (minuteCount > currentLimit) {
      return {
        allowed: false,
        limit: currentLimit,
        remaining: 0,
        resetAt: this.getNextMinute(),
        retryAfter: this.calculateRetryAfter(minuteCount, currentLimit),
      };
    }

    return {
      allowed: true,
      limit: currentLimit,
      remaining: currentLimit - minuteCount,
      resetAt: this.getNextMinute(),
    };
  }
}
```

### Burst Handling

**Burst Detection and Management:**

```typescript
// Sliding window with burst tracking
async checkBurstStatus(
  organizationId: string,
  config: RateLimitConfig,
): Promise<boolean> {
  const burstKey = `ratelimit:${organizationId}:burst`;
  const burstData = await this.redis.hgetall(burstKey);

  const now = Date.now();
  const burstStart = parseInt(burstData.start || '0');
  const burstUsed = parseInt(burstData.used || '0');

  // Check if within burst window
  if (burstStart && now - burstStart < config.burstDurationSeconds * 1000) {
    // Still in burst period
    if (burstUsed < config.burstMultiplier - 1) {
      // Can still burst
      await this.redis.hincrby(burstKey, 'used', 1);
      return true;
    }
    return false;  // Burst exhausted
  }

  // Start new burst window
  await this.redis.hset(burstKey, {
    start: now.toString(),
    used: '1',
  });
  await this.redis.expire(burstKey, config.burstDurationSeconds * 2);
  return true;
}
```

**Graceful Degradation on Rate Limit:**

| Scenario | Response Code | Retry-After | User Message |
|----------|---------------|-------------|--------------|
| Soft limit (80%) | 200 + Warning Header | N/A | None (header only) |
| Hard limit exceeded | 429 | Calculated | "Rate limit exceeded" |
| Abuse detected | 429 | 3600 (1 hour) | "Account temporarily restricted" |
| Account suspended | 403 | N/A | "Contact support" |

### WAF Configuration

**AWS WAF Rules:**

| Rule Name | Priority | Action | Description |
|-----------|----------|--------|-------------|
| IPReputationList | 1 | Block | Known malicious IPs |
| RateLimitByIP | 2 | Block | 3000 req/5min per IP |
| SQLiRuleSet | 3 | Block | SQL injection patterns |
| XSSRuleSet | 4 | Block | Cross-site scripting |
| CommonRuleSet | 5 | Count/Block | OWASP top threats |
| BotControl | 6 | Challenge/Block | Bot detection |
| GeoBlock | 7 | Block | Sanctioned countries |
| CustomRateLimit | 8 | Block | Auth endpoint protection |

**WAF Terraform Configuration:**

```hcl
resource "aws_wafv2_web_acl" "api" {
  name        = "ship-chandlery-api-waf"
  scope       = "REGIONAL"

  default_action { allow {} }

  # Bot Control with challenge
  rule {
    name     = "BotControl"
    priority = 6

    override_action { none {} }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesBotControlRuleSet"
        vendor_name = "AWS"

        managed_rule_group_configs {
          aws_managed_rules_bot_control_rule_set {
            inspection_level = "TARGETED"
          }
        }

        rule_action_override {
          name = "CategoryHttpLibrary"
          action_to_use { challenge {} }
        }

        rule_action_override {
          name = "CategoryScrapingFramework"
          action_to_use { block {} }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "BotControl"
      sampled_requests_enabled   = true
    }
  }

  # Custom rate limit for auth endpoints
  rule {
    name     = "AuthEndpointRateLimit"
    priority = 8

    action { block {} }

    statement {
      rate_based_statement {
        limit              = 100
        aggregate_key_type = "IP"

        scope_down_statement {
          byte_match_statement {
            search_string         = "/api/v1/auth/"
            positional_constraint = "STARTS_WITH"
            field_to_match { uri_path {} }
            text_transformation {
              priority = 0
              type     = "LOWERCASE"
            }
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AuthRateLimit"
      sampled_requests_enabled   = true
    }
  }
}
```

### Bot Detection

**Bot Classification:**

| Category | Detection Method | Action |
|----------|------------------|--------|
| Verified Bots (Googlebot, etc.) | User-Agent + IP verification | Allow |
| Good Bots (partners, monitoring) | API key + whitelist | Allow with higher limits |
| Unverified Bots | Behavioral analysis | Challenge (CAPTCHA) |
| Bad Bots (scrapers) | Pattern matching | Block |
| Credential Stuffing | Login failure patterns | Block + alert |

**Bot Detection Implementation:**

```typescript
@Injectable()
export class BotDetectionService {
  private readonly SUSPICIOUS_PATTERNS = [
    /python-requests/i,
    /curl/i,
    /wget/i,
    /scrapy/i,
    /phantom/i,
    /selenium/i,
  ];

  async analyzeRequest(request: Request): Promise<BotAnalysis> {
    const signals: BotSignal[] = [];

    // User-Agent analysis
    const userAgent = request.headers['user-agent'] || '';
    if (this.SUSPICIOUS_PATTERNS.some(p => p.test(userAgent))) {
      signals.push({ type: 'suspicious_ua', weight: 0.6 });
    }
    if (!userAgent) {
      signals.push({ type: 'missing_ua', weight: 0.8 });
    }

    // Header analysis
    if (!request.headers['accept-language']) {
      signals.push({ type: 'missing_accept_language', weight: 0.3 });
    }
    if (!request.headers['accept-encoding']) {
      signals.push({ type: 'missing_accept_encoding', weight: 0.2 });
    }

    // Behavioral analysis (requires session tracking)
    const behavior = await this.getBehaviorMetrics(request.ip);
    if (behavior.requestsPerSecond > 5) {
      signals.push({ type: 'high_frequency', weight: 0.7 });
    }
    if (behavior.uniqueEndpoints < 3 && behavior.totalRequests > 100) {
      signals.push({ type: 'targeted_scraping', weight: 0.8 });
    }
    if (behavior.avgTimeBetweenRequests < 100) {  // < 100ms
      signals.push({ type: 'automated_timing', weight: 0.9 });
    }

    // Calculate bot score (0-1)
    const botScore = signals.reduce((sum, s) => sum + s.weight, 0) / signals.length || 0;

    return {
      isBot: botScore > 0.5,
      botScore,
      signals,
      recommendation: this.getRecommendation(botScore),
    };
  }

  private getRecommendation(score: number): BotAction {
    if (score < 0.3) return 'allow';
    if (score < 0.5) return 'monitor';
    if (score < 0.7) return 'challenge';
    return 'block';
  }
}
```

### Abuse Monitoring

**Abuse Detection Metrics:**

| Metric | Threshold | Action |
|--------|-----------|--------|
| Failed logins/hour/IP | > 10 | Temporary IP block |
| Failed logins/hour/account | > 5 | Account lockout + alert |
| 4xx errors/minute/IP | > 50 | Challenge required |
| Same endpoint/second/IP | > 10 | Rate limit |
| Data export volume/day | > 10x average | Alert + review |
| New account + high API usage | < 1 hour | Flag for review |

**Abuse Monitoring Dashboard:**

```typescript
// Abuse detection CloudWatch metrics
const abuseMetrics = [
  {
    name: 'FailedLoginsByIP',
    namespace: 'ShipChandlery/Security',
    dimensions: [{ name: 'IP', value: ip }],
    threshold: 10,
    period: 3600,
    alertAction: 'block_ip',
  },
  {
    name: 'RateLimitExceeded',
    namespace: 'ShipChandlery/Security',
    dimensions: [{ name: 'OrganizationId', value: orgId }],
    threshold: 100,
    period: 300,
    alertAction: 'notify_admin',
  },
  {
    name: 'SuspiciousBotActivity',
    namespace: 'ShipChandlery/Security',
    dimensions: [{ name: 'IP', value: ip }],
    threshold: 5,
    period: 60,
    alertAction: 'challenge',
  },
];
```

### Open Questions - Answered

- **Q:** What telemetry differentiates abuse from legitimate spikes?
  - **A:** We use multiple signals to differentiate abuse from legitimate traffic spikes:

    **Legitimate Spike Indicators:**
    - Gradual increase over minutes (not sudden)
    - Diverse endpoint access patterns
    - Normal error rates (< 1% 4xx/5xx)
    - Requests from known/verified organizations
    - Traffic aligned with business hours or marketing campaigns
    - Diverse geographic distribution matching user base

    **Abuse Indicators:**
    - Sudden traffic spike (10x in < 1 minute)
    - Single or few endpoints targeted repeatedly
    - High error rates (> 5% 4xx responses)
    - Requests from unknown IPs or data center ranges
    - Traffic outside normal business patterns
    - Sequential/predictable request patterns
    - Missing or suspicious headers
    - Credential stuffing patterns (many accounts, same IP)

    **Telemetry Implementation:**

    ```typescript
    interface TrafficAnalysis {
      // Volume metrics
      requestsPerMinute: number;
      requestsPerMinuteBaseline: number;  // 7-day rolling average
      volumeAnomalyScore: number;  // Standard deviations from baseline

      // Pattern metrics
      uniqueEndpoints: number;
      endpointConcentration: number;  // Gini coefficient
      errorRate: number;

      // Source metrics
      isKnownOrganization: boolean;
      ipReputation: 'good' | 'neutral' | 'suspicious' | 'bad';
      geoLocation: string;
      isDataCenterIP: boolean;

      // Timing metrics
      avgTimeBetweenRequests: number;
      requestTimingVariance: number;  // Low = automated

      // Classification
      classification: 'legitimate_spike' | 'potential_abuse' | 'confirmed_abuse';
      confidence: number;
    }
    ```

    **Response by Classification:**

    | Classification | Confidence | Action |
    |----------------|------------|--------|
    | Legitimate spike | > 80% | Allow, scale infrastructure |
    | Legitimate spike | 50-80% | Allow, monitor closely |
    | Potential abuse | Any | Challenge (CAPTCHA), alert |
    | Confirmed abuse | > 80% | Block, alert, log for review |
    | Confirmed abuse | 50-80% | Challenge, strict rate limit |

---

## References
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [AWS WAF Documentation](https://docs.aws.amazon.com/waf/)
- [NestJS Security](https://docs.nestjs.com/security/helmet)
