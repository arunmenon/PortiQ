# ADR-NF-005: Caching Strategy (Redis)

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Infrastructure

---

## Context

The platform requires caching to improve performance, reduce database load, and support real-time features like session management and WebSocket scaling.

### Business Context
Performance-critical scenarios:
- Product catalog browsing (repeated queries)
- Session management for logged-in users
- Real-time bidding state during auctions
- Search result caching
- Rate limiting for API protection

### Technical Context
- NestJS backend with TypeScript
- PostgreSQL as primary database
- BullMQ for async job processing (needs Redis)
- WebSocket scaling across instances
- JWT tokens with refresh token rotation

### Assumptions
- Cache invalidation complexity is manageable
- Redis provides sufficient performance
- Cloud-managed Redis available (AWS ElastiCache)
- Cache hit rates will justify complexity

---

## Decision Drivers

- Performance improvement for frequent queries
- Session management requirements
- BullMQ dependency on Redis
- WebSocket adapter for scaling
- Operational simplicity
- Cost efficiency

---

## Considered Options

### Option 1: Redis (Standalone/Cluster)
**Description:** In-memory data store for caching, sessions, and pub/sub.

**Pros:**
- High performance (<1ms latency)
- Rich data structures
- Pub/sub for real-time
- BullMQ compatible
- Socket.io adapter available
- Mature ecosystem

**Cons:**
- Additional infrastructure
- Memory costs
- Cache invalidation complexity

### Option 2: Memcached
**Description:** Simple, distributed memory caching system.

**Pros:**
- Simple and fast
- Multi-threaded
- Lower memory overhead

**Cons:**
- Limited data structures
- No pub/sub
- No persistence
- Not compatible with BullMQ

### Option 3: Application-Level Caching Only
**Description:** In-process caching with node-cache or similar.

**Pros:**
- No additional infrastructure
- Simple implementation
- No network latency

**Cons:**
- Not shared across instances
- Lost on restart
- Memory pressure on app
- No pub/sub capability

### Option 4: PostgreSQL as Cache
**Description:** Use PostgreSQL UNLOGGED tables or materialized views.

**Pros:**
- No additional infrastructure
- SQL interface
- Transactions

**Cons:**
- Not as fast as Redis
- Resource competition
- No pub/sub

---

## Decision

**Chosen Option:** Redis (AWS ElastiCache)

We will use Redis for caching, session management, real-time features, and as the backend for BullMQ job processing.

### Rationale
Redis is already required for BullMQ (our async processing choice) and Socket.io scaling, making it a necessary infrastructure component. Leveraging it for caching provides a unified solution without additional complexity. AWS ElastiCache offers managed Redis with high availability.

---

## Consequences

### Positive
- Unified solution for caching, queues, pub/sub
- High performance caching
- Enables WebSocket scaling
- Supports BullMQ requirements
- Managed service reduces ops burden

### Negative
- Additional infrastructure cost
- **Mitigation:** Start with small instance, scale as needed
- Cache invalidation complexity
- **Mitigation:** Clear invalidation patterns, TTL-based expiry

### Risks
- Cache stampede: Implement locking, staggered TTLs
- Memory exhaustion: Monitor usage, set maxmemory policies
- Data loss on failure: Don't cache critical data, use persistence for important state

---

## Implementation Notes

### AWS ElastiCache Configuration

```yaml
# terraform/modules/redis/main.tf
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "ship-chandlery-cache"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = "cache.t4g.micro"  # Start small
  num_cache_nodes      = 1
  parameter_group_name = aws_elasticache_parameter_group.redis.name
  port                 = 6379

  # Security
  security_group_ids = [aws_security_group.redis.id]
  subnet_group_name  = aws_elasticache_subnet_group.redis.name

  # Maintenance
  maintenance_window = "sun:05:00-sun:06:00"

  # Snapshots
  snapshot_retention_limit = 7
  snapshot_window          = "04:00-05:00"
}

resource "aws_elasticache_parameter_group" "redis" {
  family = "redis7"
  name   = "ship-chandlery-redis-params"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }
}
```

### Redis Configuration Service

```typescript
// cache/config/redis.config.ts
import { RedisOptions } from 'ioredis';

export const redisConfig: RedisOptions = {
  host: process.env.REDIS_HOST,
  port: parseInt(process.env.REDIS_PORT, 10) || 6379,
  password: process.env.REDIS_PASSWORD,

  // Connection pool
  maxRetriesPerRequest: 3,
  retryStrategy: (times) => {
    if (times > 3) return null;
    return Math.min(times * 200, 2000);
  },

  // TLS for production
  tls: process.env.NODE_ENV === 'production' ? {} : undefined,

  // Key prefix for namespacing
  keyPrefix: 'sc:',

  // Timeouts
  connectTimeout: 10000,
  commandTimeout: 5000
};

// Cache TTL configurations
export const CACHE_TTL = {
  SESSION: 86400,           // 24 hours
  PRODUCT_LIST: 300,        // 5 minutes
  PRODUCT_DETAIL: 600,      // 10 minutes
  CATEGORY_LIST: 3600,      // 1 hour
  SEARCH_RESULTS: 120,      // 2 minutes
  USER_PERMISSIONS: 300,    // 5 minutes
  RATE_LIMIT: 60,           // 1 minute window
  AIS_POSITION: 60,         // 1 minute
  AUCTION_STATE: 5          // 5 seconds
};
```

### Cache Service

```typescript
// cache/services/cache.service.ts
import { Injectable } from '@nestjs/common';
import { Redis } from 'ioredis';

@Injectable()
export class CacheService {
  constructor(private readonly redis: Redis) {}

  async get<T>(key: string): Promise<T | null> {
    const value = await this.redis.get(key);
    return value ? JSON.parse(value) : null;
  }

  async set<T>(key: string, value: T, ttlSeconds?: number): Promise<void> {
    const serialized = JSON.stringify(value);
    if (ttlSeconds) {
      await this.redis.setex(key, ttlSeconds, serialized);
    } else {
      await this.redis.set(key, serialized);
    }
  }

  async delete(key: string): Promise<void> {
    await this.redis.del(key);
  }

  async deletePattern(pattern: string): Promise<void> {
    const keys = await this.redis.keys(pattern);
    if (keys.length > 0) {
      await this.redis.del(...keys);
    }
  }

  // Cache-aside pattern with automatic refresh
  async getOrSet<T>(
    key: string,
    factory: () => Promise<T>,
    ttlSeconds: number
  ): Promise<T> {
    const cached = await this.get<T>(key);
    if (cached !== null) {
      return cached;
    }

    const value = await factory();
    await this.set(key, value, ttlSeconds);
    return value;
  }

  // Distributed lock for cache stampede prevention
  async withLock<T>(
    lockKey: string,
    factory: () => Promise<T>,
    lockTtlMs: number = 10000
  ): Promise<T> {
    const lockValue = Date.now().toString();
    const acquired = await this.redis.set(
      `lock:${lockKey}`,
      lockValue,
      'PX',
      lockTtlMs,
      'NX'
    );

    if (!acquired) {
      // Wait and retry
      await new Promise(resolve => setTimeout(resolve, 100));
      return this.withLock(lockKey, factory, lockTtlMs);
    }

    try {
      return await factory();
    } finally {
      // Release lock if we still own it
      const currentValue = await this.redis.get(`lock:${lockKey}`);
      if (currentValue === lockValue) {
        await this.redis.del(`lock:${lockKey}`);
      }
    }
  }
}
```

### Caching Decorator

```typescript
// cache/decorators/cacheable.decorator.ts
import { SetMetadata } from '@nestjs/common';

export const CACHE_KEY = 'cache_key';
export const CACHE_TTL = 'cache_ttl';

export interface CacheOptions {
  key: string | ((args: any[]) => string);
  ttl: number;
}

export const Cacheable = (options: CacheOptions) => {
  return (target: any, propertyKey: string, descriptor: PropertyDescriptor) => {
    const originalMethod = descriptor.value;

    descriptor.value = async function (...args: any[]) {
      const cacheService = this.cacheService;
      const cacheKey = typeof options.key === 'function'
        ? options.key(args)
        : options.key;

      return cacheService.getOrSet(
        cacheKey,
        () => originalMethod.apply(this, args),
        options.ttl
      );
    };

    return descriptor;
  };
};

// Cache invalidation decorator
export const CacheEvict = (keyPattern: string | ((args: any[]) => string)) => {
  return (target: any, propertyKey: string, descriptor: PropertyDescriptor) => {
    const originalMethod = descriptor.value;

    descriptor.value = async function (...args: any[]) {
      const result = await originalMethod.apply(this, args);

      const cacheService = this.cacheService;
      const pattern = typeof keyPattern === 'function'
        ? keyPattern(args)
        : keyPattern;

      await cacheService.deletePattern(pattern);

      return result;
    };

    return descriptor;
  };
};
```

### Product Caching Example

```typescript
// product/services/product.service.ts
@Injectable()
export class ProductService {
  constructor(
    private readonly productRepository: ProductRepository,
    private readonly cacheService: CacheService
  ) {}

  async findById(id: string): Promise<Product> {
    return this.cacheService.getOrSet(
      `product:${id}`,
      () => this.productRepository.findById(id),
      CACHE_TTL.PRODUCT_DETAIL
    );
  }

  async findByCategory(categoryId: string, page: number): Promise<Product[]> {
    return this.cacheService.getOrSet(
      `products:category:${categoryId}:page:${page}`,
      () => this.productRepository.findByCategory(categoryId, page),
      CACHE_TTL.PRODUCT_LIST
    );
  }

  async updateProduct(id: string, data: UpdateProductDto): Promise<Product> {
    const product = await this.productRepository.update(id, data);

    // Invalidate related caches
    await this.cacheService.delete(`product:${id}`);
    await this.cacheService.deletePattern(`products:category:${product.categoryId}:*`);
    await this.cacheService.deletePattern(`search:*`);

    return product;
  }
}
```

### Session Management

```typescript
// auth/services/session.service.ts
@Injectable()
export class SessionService {
  constructor(private readonly redis: Redis) {}

  async createSession(userId: string, data: SessionData): Promise<string> {
    const sessionId = crypto.randomUUID();
    const key = `session:${sessionId}`;

    await this.redis.hset(key, {
      userId,
      createdAt: Date.now(),
      ...data
    });
    await this.redis.expire(key, CACHE_TTL.SESSION);

    // Track user sessions
    await this.redis.sadd(`user:${userId}:sessions`, sessionId);

    return sessionId;
  }

  async getSession(sessionId: string): Promise<SessionData | null> {
    const key = `session:${sessionId}`;
    const data = await this.redis.hgetall(key);
    return Object.keys(data).length > 0 ? data as SessionData : null;
  }

  async refreshSession(sessionId: string): Promise<void> {
    await this.redis.expire(`session:${sessionId}`, CACHE_TTL.SESSION);
  }

  async invalidateSession(sessionId: string): Promise<void> {
    const session = await this.getSession(sessionId);
    if (session) {
      await this.redis.srem(`user:${session.userId}:sessions`, sessionId);
      await this.redis.del(`session:${sessionId}`);
    }
  }

  async invalidateAllUserSessions(userId: string): Promise<void> {
    const sessions = await this.redis.smembers(`user:${userId}:sessions`);
    if (sessions.length > 0) {
      await this.redis.del(...sessions.map(s => `session:${s}`));
      await this.redis.del(`user:${userId}:sessions`);
    }
  }
}
```

### Rate Limiting

```typescript
// rate-limit/services/rate-limit.service.ts
@Injectable()
export class RateLimitService {
  constructor(private readonly redis: Redis) {}

  async checkRateLimit(
    key: string,
    limit: number,
    windowSeconds: number
  ): Promise<RateLimitResult> {
    const now = Date.now();
    const windowStart = now - (windowSeconds * 1000);

    // Use sorted set for sliding window
    const redisKey = `ratelimit:${key}`;

    // Remove old entries
    await this.redis.zremrangebyscore(redisKey, 0, windowStart);

    // Count current entries
    const count = await this.redis.zcard(redisKey);

    if (count >= limit) {
      return {
        allowed: false,
        remaining: 0,
        resetAt: new Date(windowStart + (windowSeconds * 1000))
      };
    }

    // Add current request
    await this.redis.zadd(redisKey, now, `${now}-${Math.random()}`);
    await this.redis.expire(redisKey, windowSeconds);

    return {
      allowed: true,
      remaining: limit - count - 1,
      resetAt: new Date(now + (windowSeconds * 1000))
    };
  }
}
```

### Dependencies
- ADR-NF-008: Async Processing (BullMQ)
- ADR-NF-015: Authentication Strategy
- ADR-UI-012: Real-Time Notifications

### Migration Strategy
1. Provision AWS ElastiCache Redis
2. Configure connection in NestJS
3. Implement cache service
4. Add caching to high-traffic endpoints
5. Implement session management
6. Add rate limiting
7. Monitor cache hit rates and performance

---

## Operational Considerations

### Cache Tiers, TTLs, and Invalidation Patterns

#### Multi-Tier Cache Architecture

| Tier | Storage | TTL Range | Use Case | Invalidation Strategy |
|------|---------|-----------|----------|----------------------|
| **L1: Application Memory** | Node.js LRU cache | 30s - 5min | Hot path data (current user, active session) | Process restart, explicit clear |
| **L2: Redis Local** | ElastiCache (same AZ) | 5min - 1hr | Shared application data (product catalog, categories) | Event-driven + TTL |
| **L3: Redis Cluster** | ElastiCache Cluster | 1hr - 24hr | Cross-region data (reference data, configurations) | TTL-based with warm-through |

#### TTL Configuration by Data Type

```typescript
// cache/config/ttl-config.ts
export const CACHE_TTL_CONFIG = {
  // User & Session (high sensitivity, short TTL)
  session: {
    ttl: 86400,           // 24 hours
    staleWhileRevalidate: 0,  // No stale serving
    invalidateOn: ['user.logout', 'user.password_changed', 'security.breach']
  },
  userPermissions: {
    ttl: 300,             // 5 minutes
    staleWhileRevalidate: 60,
    invalidateOn: ['user.role_changed', 'org.permissions_updated']
  },

  // Product Catalog (medium sensitivity, moderate TTL)
  productDetail: {
    ttl: 600,             // 10 minutes
    staleWhileRevalidate: 120,
    invalidateOn: ['product.updated', 'product.price_changed']
  },
  productList: {
    ttl: 300,             // 5 minutes
    staleWhileRevalidate: 60,
    invalidateOn: ['product.created', 'product.deleted', 'category.updated']
  },
  categoryTree: {
    ttl: 3600,            // 1 hour
    staleWhileRevalidate: 300,
    invalidateOn: ['category.created', 'category.updated', 'category.deleted']
  },

  // Search (low sensitivity, short TTL due to dynamic nature)
  searchResults: {
    ttl: 120,             // 2 minutes
    staleWhileRevalidate: 30,
    invalidateOn: []       // TTL-only, too dynamic for event invalidation
  },
  searchFacets: {
    ttl: 300,             // 5 minutes
    staleWhileRevalidate: 60,
    invalidateOn: ['product.created', 'product.deleted']
  },

  // Real-time Data (very short TTL)
  auctionState: {
    ttl: 5,               // 5 seconds
    staleWhileRevalidate: 0,
    invalidateOn: ['auction.bid_placed', 'auction.ended']
  },
  vesselPosition: {
    ttl: 60,              // 1 minute
    staleWhileRevalidate: 30,
    invalidateOn: ['ais.position_updated']
  },

  // Reference Data (low sensitivity, long TTL)
  portList: {
    ttl: 86400,           // 24 hours
    staleWhileRevalidate: 3600,
    invalidateOn: ['port.updated']
  },
  impaCodebook: {
    ttl: 604800,          // 7 days
    staleWhileRevalidate: 86400,
    invalidateOn: ['impa.catalog_updated']
  }
};
```

#### Invalidation Patterns

```typescript
// cache/services/invalidation.service.ts
@Injectable()
export class CacheInvalidationService {
  constructor(
    private readonly redis: Redis,
    private readonly eventEmitter: EventEmitter2
  ) {
    this.setupEventListeners();
  }

  private setupEventListeners(): void {
    // Product events
    this.eventEmitter.on('product.updated', async (event) => {
      await this.invalidateProduct(event.productId);
    });

    this.eventEmitter.on('product.price_changed', async (event) => {
      await this.invalidateProduct(event.productId);
      await this.invalidatePattern(`search:*`);  // Price affects search results
    });

    // Category events
    this.eventEmitter.on('category.updated', async (event) => {
      await this.invalidateCategory(event.categoryId);
      await this.invalidatePattern(`products:category:${event.categoryId}:*`);
    });
  }

  // Write-through invalidation
  async invalidateProduct(productId: string): Promise<void> {
    const keys = [
      `product:${productId}`,
      `product:${productId}:details`,
      `product:${productId}:pricing`
    ];
    await this.redis.del(...keys);

    // Invalidate related lists (use SCAN for pattern matching)
    await this.invalidatePattern(`products:*:${productId}`);
  }

  // Pattern-based invalidation with SCAN (non-blocking)
  async invalidatePattern(pattern: string): Promise<number> {
    let cursor = '0';
    let deletedCount = 0;

    do {
      const [nextCursor, keys] = await this.redis.scan(
        cursor,
        'MATCH', `sc:${pattern}`,
        'COUNT', 100
      );
      cursor = nextCursor;

      if (keys.length > 0) {
        await this.redis.del(...keys);
        deletedCount += keys.length;
      }
    } while (cursor !== '0');

    return deletedCount;
  }

  // Tag-based invalidation for complex dependencies
  async invalidateByTag(tag: string): Promise<void> {
    const keys = await this.redis.smembers(`tag:${tag}`);
    if (keys.length > 0) {
      await this.redis.del(...keys);
      await this.redis.del(`tag:${tag}`);
    }
  }
}

// Cache key tagging for group invalidation
async setWithTags<T>(
  key: string,
  value: T,
  ttl: number,
  tags: string[]
): Promise<void> {
  const pipeline = this.redis.pipeline();

  pipeline.setex(key, ttl, JSON.stringify(value));

  for (const tag of tags) {
    pipeline.sadd(`tag:${tag}`, key);
    pipeline.expire(`tag:${tag}`, ttl + 60);  // Tag expires after last member
  }

  await pipeline.exec();
}
```

### Observability: Hit Rate, Latency, and Eviction Monitoring

#### Prometheus Metrics

```typescript
// cache/metrics/cache-metrics.ts
import { Counter, Histogram, Gauge } from 'prom-client';

export const cacheMetrics = {
  // Hit/Miss tracking
  cacheOperations: new Counter({
    name: 'cache_operations_total',
    help: 'Total cache operations',
    labelNames: ['operation', 'result', 'cache_tier', 'key_prefix']
  }),

  // Latency tracking
  cacheLatency: new Histogram({
    name: 'cache_operation_duration_seconds',
    help: 'Cache operation latency',
    labelNames: ['operation', 'cache_tier'],
    buckets: [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1]
  }),

  // Memory usage
  cacheMemoryUsage: new Gauge({
    name: 'cache_memory_usage_bytes',
    help: 'Redis memory usage in bytes',
    labelNames: ['instance']
  }),

  // Key count
  cacheKeyCount: new Gauge({
    name: 'cache_key_count',
    help: 'Number of keys in cache',
    labelNames: ['key_prefix']
  }),

  // Eviction tracking
  cacheEvictions: new Counter({
    name: 'cache_evictions_total',
    help: 'Total cache evictions',
    labelNames: ['reason']  // 'ttl_expired', 'lru_evicted', 'explicit_delete'
  }),

  // Hit rate (calculated gauge)
  cacheHitRate: new Gauge({
    name: 'cache_hit_rate',
    help: 'Cache hit rate (0-1)',
    labelNames: ['key_prefix', 'time_window']
  })
};

// Instrumented cache service
@Injectable()
export class InstrumentedCacheService {
  async get<T>(key: string): Promise<T | null> {
    const startTime = Date.now();
    const prefix = this.extractPrefix(key);

    try {
      const value = await this.redis.get(key);
      const result = value ? 'hit' : 'miss';

      cacheMetrics.cacheOperations.inc({
        operation: 'get',
        result,
        cache_tier: 'l2_redis',
        key_prefix: prefix
      });

      cacheMetrics.cacheLatency.observe(
        { operation: 'get', cache_tier: 'l2_redis' },
        (Date.now() - startTime) / 1000
      );

      return value ? JSON.parse(value) : null;
    } catch (error) {
      cacheMetrics.cacheOperations.inc({
        operation: 'get',
        result: 'error',
        cache_tier: 'l2_redis',
        key_prefix: prefix
      });
      throw error;
    }
  }
}
```

#### Grafana Dashboard Queries

```promql
# Cache Hit Rate (5-minute window)
sum(rate(cache_operations_total{result="hit"}[5m])) by (key_prefix)
/
sum(rate(cache_operations_total{result=~"hit|miss"}[5m])) by (key_prefix)

# P99 Cache Latency
histogram_quantile(0.99, rate(cache_operation_duration_seconds_bucket[5m]))

# Eviction Rate
rate(cache_evictions_total[5m])

# Memory Pressure Alert
cache_memory_usage_bytes / redis_max_memory_bytes > 0.85
```

#### Alert Rules

```yaml
# prometheus/alerts/cache-alerts.yml
groups:
  - name: cache-alerts
    rules:
      - alert: CacheHitRateLow
        expr: |
          (sum(rate(cache_operations_total{result="hit"}[10m]))
           / sum(rate(cache_operations_total{result=~"hit|miss"}[10m]))) < 0.7
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Cache hit rate below 70%"
          description: "Cache hit rate is {{ $value | humanizePercentage }}"

      - alert: CacheLatencyHigh
        expr: |
          histogram_quantile(0.99, rate(cache_operation_duration_seconds_bucket[5m])) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Cache P99 latency above 100ms"

      - alert: CacheMemoryPressure
        expr: cache_memory_usage_bytes / 1073741824 > 0.9  # 90% of 1GB
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Redis memory usage above 90%"

      - alert: CacheEvictionRateHigh
        expr: rate(cache_evictions_total{reason="lru_evicted"}[5m]) > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High LRU eviction rate indicates memory pressure"
```

### Cache Warming Strategy

```typescript
// cache/services/cache-warmer.service.ts
@Injectable()
export class CacheWarmerService {
  @Cron('0 */15 * * * *')  // Every 15 minutes
  async warmFrequentlyAccessedData(): Promise<void> {
    // Warm top categories
    const topCategories = await this.analyticsService.getTopCategories(20);
    for (const category of topCategories) {
      await this.productService.findByCategory(category.id, 1);
    }

    // Warm popular products
    const popularProducts = await this.analyticsService.getPopularProducts(100);
    for (const product of popularProducts) {
      await this.productService.findById(product.id);
    }
  }

  // Warm on deployment
  async warmOnStartup(): Promise<void> {
    await this.warmCategoryTree();
    await this.warmPortList();
    await this.warmIMPACodes();
  }
}
```

### Open Questions

- **Q:** What data must not be cached due to compliance or privacy?
  - **A:** The following data categories are excluded from caching:

  **Never Cache (Privacy/Compliance):**
  | Data Type | Reason | Alternative |
  |-----------|--------|-------------|
  | PII (personal identifiable information) | GDPR/DPDP compliance | Database query with row-level security |
  | Payment card data | PCI-DSS requirement | Tokenized references only |
  | Bank account details | Financial regulations | Encrypted at-rest in DB |
  | Authentication tokens (refresh) | Security risk if leaked | Secure cookie or DB |
  | KYC documents | Regulatory requirement | S3 with signed URLs |
  | Audit logs | Compliance immutability | TimescaleDB with retention |

  **Cache with Restrictions:**
  | Data Type | Allowed Caching | Restrictions |
  |-----------|-----------------|--------------|
  | User preferences | L1/L2 with user isolation | Key includes userId, invalidate on logout |
  | Order history | L2 with short TTL | Max 5 minutes, user-scoped keys |
  | Invoice data | L2 read-through only | No sensitive amounts, metadata only |
  | Supplier pricing | L2 with supplier scope | Supplier-specific keys, invalidate on update |

  **Implementation Safeguards:**
  ```typescript
  // Sensitive data filter middleware
  const NEVER_CACHE_PATTERNS = [
    /user:\w+:pii/,
    /payment:.*/,
    /kyc:.*/,
    /bank:.*/,
    /audit:.*/
  ];

  function shouldCache(key: string): boolean {
    return !NEVER_CACHE_PATTERNS.some(pattern => pattern.test(key));
  }
  ```

---

## References
- [Redis Documentation](https://redis.io/documentation)
- [AWS ElastiCache](https://aws.amazon.com/elasticache/)
- [NestJS Caching](https://docs.nestjs.com/techniques/caching)
- [Cache Invalidation Patterns](https://martinfowler.com/bliki/TwoHardThings.html)
