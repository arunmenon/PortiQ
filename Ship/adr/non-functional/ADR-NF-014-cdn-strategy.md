# ADR-NF-014: CDN Strategy

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Infrastructure

---

## Context

The platform needs efficient delivery of static assets and cacheable content to global maritime users with varying network conditions.

### Business Context
Content delivery needs:
- Product images (50K+ products)
- Static frontend assets (JS, CSS, fonts)
- PDF documents and reports
- API response caching for catalog data
- Low latency for Indian users (primary market)
- Global reach for international shipping routes

### Technical Context
- AWS as cloud provider (ADR-NF-011)
- S3 for object storage (ADR-NF-013)
- Next.js frontend with static generation
- API responses can be cached for catalog data
- Maritime users often on satellite connections

### Assumptions
- CloudFront provides adequate global coverage
- Edge caching improves user experience significantly
- Most static content can be cached aggressively
- API caching needs careful invalidation strategy

---

## Decision Drivers

- Latency reduction for end users
- Cost efficiency
- AWS integration
- Security (DDoS protection)
- Cache invalidation capabilities
- Edge computing potential

---

## Considered Options

### Option 1: Amazon CloudFront
**Description:** AWS native CDN service.

**Pros:**
- Deep AWS integration
- 450+ edge locations globally
- Lambda@Edge for compute
- Shield integration for DDoS
- Origin Shield for cache optimization
- WebSocket support

**Cons:**
- AWS lock-in
- Complex pricing model
- Configuration complexity

### Option 2: Cloudflare
**Description:** Independent CDN with security features.

**Pros:**
- Simple pricing
- Strong security features
- Workers for edge compute
- Good free tier
- Easy setup

**Cons:**
- Separate vendor management
- Additional network hop from AWS
- Less AWS integration

### Option 3: Fastly
**Description:** Developer-focused CDN.

**Pros:**
- Instant cache purge
- VCL for customization
- Real-time analytics
- Edge compute (Compute@Edge)

**Cons:**
- Higher cost
- Smaller edge network
- Steeper learning curve

---

## Decision

**Chosen Option:** Amazon CloudFront

We will use Amazon CloudFront as our CDN, leveraging its deep AWS integration with S3 and ALB origins.

### Rationale
CloudFront's integration with our AWS infrastructure eliminates additional network hops and simplifies architecture. AWS Shield provides DDoS protection. Lambda@Edge enables edge-side processing when needed. Origin Shield reduces load on origins during cache population.

---

## Consequences

### Positive
- Seamless S3 and ALB integration
- Global edge network
- Built-in DDoS protection
- Edge compute capabilities
- Single vendor management

### Negative
- AWS lock-in for CDN
- **Mitigation:** Standard HTTP caching headers, portable configuration
- Complex pricing
- **Mitigation:** Reserved capacity pricing, cost monitoring

### Risks
- Cache invalidation delays: Use versioned URLs, instant invalidation for critical content
- Stale content: Implement proper cache-control headers
- Cost overruns: Monitor usage, set billing alerts

---

## Implementation Notes

### CloudFront Distribution Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │              CloudFront                      │
                    │                                              │
User ───────────────│   Edge Location (450+ globally)             │
                    │              │                               │
                    │              ▼                               │
                    │       Origin Shield                          │
                    │         (Mumbai)                             │
                    └──────────────┬───────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
              ┌──────────┐  ┌──────────┐  ┌──────────┐
              │    S3    │  │   ALB    │  │  Next.js │
              │ (Static) │  │  (API)   │  │  (SSR)   │
              └──────────┘  └──────────┘  └──────────┘
```

### Terraform Configuration

```hcl
# terraform/modules/cloudfront/main.tf

# Origin Access Control for S3
resource "aws_cloudfront_origin_access_control" "s3" {
  name                              = "ship-chandlery-s3-oac"
  description                       = "OAC for S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# Main distribution
resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "Ship Chandlery CDN - ${var.environment}"
  default_root_object = "index.html"
  price_class         = "PriceClass_All"
  aliases             = var.domain_aliases
  web_acl_id          = aws_wafv2_web_acl.cdn.arn

  # S3 Origin for static assets
  origin {
    domain_name              = aws_s3_bucket.static.bucket_regional_domain_name
    origin_id                = "S3-static"
    origin_access_control_id = aws_cloudfront_origin_access_control.s3.id

    origin_shield {
      enabled              = true
      origin_shield_region = "ap-south-1"
    }
  }

  # S3 Origin for media/uploads
  origin {
    domain_name              = aws_s3_bucket.media.bucket_regional_domain_name
    origin_id                = "S3-media"
    origin_access_control_id = aws_cloudfront_origin_access_control.s3.id

    origin_shield {
      enabled              = true
      origin_shield_region = "ap-south-1"
    }
  }

  # ALB Origin for API
  origin {
    domain_name = aws_lb.api.dns_name
    origin_id   = "ALB-api"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }

    origin_shield {
      enabled              = true
      origin_shield_region = "ap-south-1"
    }
  }

  # Default behavior - Next.js SSR
  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-static"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 86400    # 1 day
    max_ttl                = 31536000 # 1 year
    compress               = true
  }

  # Static assets - aggressive caching
  ordered_cache_behavior {
    path_pattern     = "/static/*"
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-static"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 31536000 # 1 year
    default_ttl            = 31536000
    max_ttl                = 31536000
    compress               = true

    response_headers_policy_id = aws_cloudfront_response_headers_policy.static.id
  }

  # Product images
  ordered_cache_behavior {
    path_pattern     = "/media/products/*"
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-media"

    forwarded_values {
      query_string = true
      query_string_cache_keys = ["w", "h", "q"]  # Image resizing params
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 86400     # 1 day
    default_ttl            = 604800    # 1 week
    max_ttl                = 31536000  # 1 year
    compress               = true

    # Lambda@Edge for image optimization
    lambda_function_association {
      event_type   = "origin-response"
      lambda_arn   = aws_lambda_function.image_optimizer.qualified_arn
      include_body = false
    }
  }

  # API responses - selective caching
  ordered_cache_behavior {
    path_pattern     = "/api/v1/catalog/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "ALB-api"

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Accept-Language"]
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "https-only"
    min_ttl                = 0
    default_ttl            = 300   # 5 minutes
    max_ttl                = 3600  # 1 hour
    compress               = true
  }

  # API - no caching for authenticated endpoints
  ordered_cache_behavior {
    path_pattern     = "/api/*"
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "ALB-api"

    forwarded_values {
      query_string = true
      headers      = ["*"]
      cookies {
        forward = "all"
      }
    }

    viewer_protocol_policy = "https-only"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
    compress               = true
  }

  # SSL Certificate
  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.main.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  # Geographic restrictions (none for now)
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # Custom error pages
  custom_error_response {
    error_code         = 403
    response_code      = 404
    response_page_path = "/404.html"
  }

  custom_error_response {
    error_code         = 404
    response_code      = 404
    response_page_path = "/404.html"
  }

  custom_error_response {
    error_code            = 503
    response_code         = 503
    response_page_path    = "/maintenance.html"
    error_caching_min_ttl = 60
  }

  tags = {
    Environment = var.environment
    Service     = "cdn"
  }
}

# Response headers policy for static assets
resource "aws_cloudfront_response_headers_policy" "static" {
  name = "static-assets-policy"

  security_headers_config {
    content_type_options {
      override = true
    }

    frame_options {
      frame_option = "DENY"
      override     = true
    }

    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = true
      override                   = true
      preload                    = true
    }
  }

  custom_headers_config {
    items {
      header   = "Cache-Control"
      override = true
      value    = "public, max-age=31536000, immutable"
    }
  }
}

# Cache invalidation function
resource "aws_cloudfront_function" "cache_key" {
  name    = "cache-key-normalizer"
  runtime = "cloudfront-js-1.0"
  code    = <<-EOF
    function handler(event) {
      var request = event.request;
      var uri = request.uri;

      // Normalize query strings for better cache hit ratio
      var queryString = request.querystring;
      var sortedParams = Object.keys(queryString)
        .sort()
        .reduce(function(acc, key) {
          acc[key] = queryString[key];
          return acc;
        }, {});

      request.querystring = sortedParams;
      return request;
    }
  EOF
}
```

### Lambda@Edge for Image Optimization

```typescript
// lambda/image-optimizer/index.ts
import { CloudFrontResponseEvent, CloudFrontResponseResult } from 'aws-lambda';

export const handler = async (
  event: CloudFrontResponseEvent
): Promise<CloudFrontResponseResult> => {
  const response = event.Records[0].cf.response;
  const request = event.Records[0].cf.request;

  // Add caching headers if not present
  if (!response.headers['cache-control']) {
    response.headers['cache-control'] = [{
      key: 'Cache-Control',
      value: 'public, max-age=31536000'
    }];
  }

  // Add image-specific headers
  if (request.uri.match(/\.(jpg|jpeg|png|gif|webp)$/i)) {
    response.headers['vary'] = [{
      key: 'Vary',
      value: 'Accept'
    }];
  }

  return response;
};
```

### Cache Invalidation Service

```typescript
// cdn/services/cache-invalidation.service.ts
import { CloudFrontClient, CreateInvalidationCommand } from '@aws-sdk/client-cloudfront';

@Injectable()
export class CacheInvalidationService {
  private readonly cloudfront: CloudFrontClient;
  private readonly distributionId: string;

  constructor(private readonly configService: ConfigService) {
    this.cloudfront = new CloudFrontClient({
      region: 'us-east-1', // CloudFront is global
    });
    this.distributionId = configService.get('CLOUDFRONT_DISTRIBUTION_ID');
  }

  async invalidatePaths(paths: string[]): Promise<string> {
    const command = new CreateInvalidationCommand({
      DistributionId: this.distributionId,
      InvalidationBatch: {
        CallerReference: `invalidation-${Date.now()}`,
        Paths: {
          Quantity: paths.length,
          Items: paths,
        },
      },
    });

    const response = await this.cloudfront.send(command);
    return response.Invalidation.Id;
  }

  async invalidateProduct(productId: string): Promise<void> {
    await this.invalidatePaths([
      `/media/products/${productId}/*`,
      `/api/v1/catalog/products/${productId}`,
    ]);
  }

  async invalidateCatalog(): Promise<void> {
    await this.invalidatePaths([
      '/api/v1/catalog/*',
    ]);
  }
}
```

### Frontend Asset Versioning

```typescript
// next.config.js
module.exports = {
  // Generate unique build IDs for cache busting
  generateBuildId: async () => {
    return process.env.GIT_SHA || crypto.randomUUID();
  },

  // Asset prefix for CDN
  assetPrefix: process.env.CDN_URL || '',

  // Image optimization via CloudFront
  images: {
    loader: 'custom',
    loaderFile: './lib/image-loader.ts',
    domains: ['cdn.shipchandlery.com'],
  },
};

// lib/image-loader.ts
export default function cloudFrontLoader({ src, width, quality }) {
  const params = new URLSearchParams({
    w: width.toString(),
    q: (quality || 75).toString(),
  });
  return `${process.env.CDN_URL}${src}?${params}`;
}
```

### Monitoring and Analytics

```typescript
// cdn/services/cdn-analytics.service.ts
@Injectable()
export class CDNAnalyticsService {
  constructor(
    private readonly cloudWatch: CloudWatchClient
  ) {}

  async getCacheMetrics(startTime: Date, endTime: Date): Promise<CacheMetrics> {
    const [hitRate, bytesTransferred, requests] = await Promise.all([
      this.getMetric('CacheHitRate', startTime, endTime),
      this.getMetric('BytesDownloaded', startTime, endTime),
      this.getMetric('Requests', startTime, endTime),
    ]);

    return {
      cacheHitRate: hitRate,
      bytesTransferred,
      totalRequests: requests,
      costEstimate: this.estimateCost(bytesTransferred, requests),
    };
  }

  private async getMetric(
    metricName: string,
    startTime: Date,
    endTime: Date
  ): Promise<number> {
    const command = new GetMetricStatisticsCommand({
      Namespace: 'AWS/CloudFront',
      MetricName: metricName,
      Dimensions: [{
        Name: 'DistributionId',
        Value: process.env.CLOUDFRONT_DISTRIBUTION_ID,
      }],
      StartTime: startTime,
      EndTime: endTime,
      Period: 3600,
      Statistics: ['Average', 'Sum'],
    });

    const response = await this.cloudWatch.send(command);
    return response.Datapoints?.[0]?.Average || 0;
  }
}
```

### Dependencies
- ADR-NF-011: Cloud Provider - AWS Mumbai
- ADR-NF-013: Object Storage (S3)
- ADR-NF-016: API Security & Rate Limiting

### Migration Strategy
1. Create CloudFront distribution via Terraform
2. Configure S3 bucket policies for OAC
3. Set up SSL certificate in ACM
4. Update DNS to point to CloudFront
5. Configure cache behaviors
6. Set up monitoring and alerts
7. Implement cache invalidation in deployment pipeline

---

## Operational Considerations

### Cache Key Rules

**Cache Key Configuration by Content Type:**

| Path Pattern | Cache Key Includes | TTL | Rationale |
|--------------|-------------------|-----|-----------|
| `/static/*` | Path only | 1 year | Immutable hashed assets |
| `/_next/static/*` | Path only | 1 year | Next.js build assets (hashed) |
| `/media/products/*` | Path + `w`, `h`, `q` params | 1 week | Image resizing parameters |
| `/api/v1/catalog/*` | Path + query string + `Accept-Language` | 5 min | Public catalog data |
| `/api/v1/*` | No caching | 0 | Authenticated API endpoints |
| `/*.html` | Path only | 1 hour | HTML pages (SPA fallback) |

**Cache Key Policy Configuration:**

```hcl
resource "aws_cloudfront_cache_policy" "static_assets" {
  name        = "static-assets-policy"
  min_ttl     = 31536000  # 1 year
  default_ttl = 31536000
  max_ttl     = 31536000

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"
    }
    headers_config {
      header_behavior = "none"
    }
    query_strings_config {
      query_string_behavior = "none"
    }
    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true
  }
}

resource "aws_cloudfront_cache_policy" "product_images" {
  name        = "product-images-policy"
  min_ttl     = 86400     # 1 day
  default_ttl = 604800    # 1 week
  max_ttl     = 31536000  # 1 year

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"
    }
    headers_config {
      header_behavior = "whitelist"
      headers {
        items = ["Accept"]  # For WebP/AVIF negotiation
      }
    }
    query_strings_config {
      query_string_behavior = "whitelist"
      query_strings {
        items = ["w", "h", "q", "f"]  # width, height, quality, format
      }
    }
    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true
  }
}

resource "aws_cloudfront_cache_policy" "api_catalog" {
  name        = "api-catalog-policy"
  min_ttl     = 0
  default_ttl = 300       # 5 minutes
  max_ttl     = 3600      # 1 hour

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"
    }
    headers_config {
      header_behavior = "whitelist"
      headers {
        items = ["Accept-Language", "Accept"]
      }
    }
    query_strings_config {
      query_string_behavior = "all"
    }
  }
}
```

### Invalidation Strategy

**Invalidation Triggers and Methods:**

| Event | Invalidation Scope | Method | SLA |
|-------|-------------------|--------|-----|
| Product image update | `/media/products/{id}/*` | Immediate API call | < 1 minute |
| Catalog bulk update | `/api/v1/catalog/*` | Batch invalidation | < 5 minutes |
| Frontend deployment | `/_next/*`, `/static/*` | Deploy-time, versioned | Instant (cache bypass) |
| Price update | `/api/v1/catalog/products/{id}` | Event-driven | < 2 minutes |
| Emergency content removal | Specific path | Manual + automated | < 30 seconds |

**Invalidation Budget Management:**

| Environment | Free Invalidations/Month | Strategy |
|-------------|-------------------------|----------|
| Production | 1,000 paths | Use wildcards, batch updates |
| Staging | 1,000 paths | Liberal invalidation for testing |

**Invalidation Service Implementation:**

```typescript
@Injectable()
export class CacheInvalidationService {
  private readonly invalidationQueue: Queue;
  private readonly BATCH_SIZE = 15;  // CloudFront limit per request
  private readonly BATCH_DELAY = 1000;  // 1 second between batches

  constructor(
    private readonly cloudfront: CloudFrontClient,
    @InjectQueue('cache-invalidation') queue: Queue,
  ) {
    this.invalidationQueue = queue;
  }

  // Immediate invalidation for critical updates
  async invalidateImmediate(paths: string[]): Promise<string> {
    const command = new CreateInvalidationCommand({
      DistributionId: this.distributionId,
      InvalidationBatch: {
        CallerReference: `immediate-${Date.now()}`,
        Paths: {
          Quantity: paths.length,
          Items: paths,
        },
      },
    });

    const result = await this.cloudfront.send(command);
    return result.Invalidation.Id;
  }

  // Queued invalidation for batch updates
  async queueInvalidation(paths: string[], priority: 'high' | 'normal' = 'normal'): Promise<void> {
    await this.invalidationQueue.add('invalidate', { paths }, {
      priority: priority === 'high' ? 1 : 5,
      attempts: 3,
      backoff: { type: 'exponential', delay: 5000 },
    });
  }

  // Processor for batched invalidations
  @Processor('cache-invalidation')
  async processInvalidation(job: Job<{ paths: string[] }>): Promise<void> {
    const { paths } = job.data;

    // Deduplicate and optimize paths
    const optimizedPaths = this.optimizePaths(paths);

    // Process in batches
    for (let i = 0; i < optimizedPaths.length; i += this.BATCH_SIZE) {
      const batch = optimizedPaths.slice(i, i + this.BATCH_SIZE);
      await this.invalidateImmediate(batch);

      if (i + this.BATCH_SIZE < optimizedPaths.length) {
        await this.delay(this.BATCH_DELAY);
      }
    }
  }

  private optimizePaths(paths: string[]): string[] {
    // Convert specific paths to wildcards when beneficial
    const pathGroups = new Map<string, string[]>();

    for (const path of paths) {
      const dir = path.substring(0, path.lastIndexOf('/'));
      if (!pathGroups.has(dir)) {
        pathGroups.set(dir, []);
      }
      pathGroups.get(dir).push(path);
    }

    const optimized: string[] = [];
    for (const [dir, dirPaths] of pathGroups) {
      // If more than 5 files in same directory, use wildcard
      if (dirPaths.length > 5) {
        optimized.push(`${dir}/*`);
      } else {
        optimized.push(...dirPaths);
      }
    }

    return [...new Set(optimized)];
  }
}
```

### Asset Versioning Strategy

**Versioning Methods by Asset Type:**

| Asset Type | Versioning Method | Example |
|------------|-------------------|---------|
| JS/CSS bundles | Content hash in filename | `main.a1b2c3d4.js` |
| Product images | Query string + ETag | `/products/123/main.jpg?v=abc123` |
| Static images | Build hash in path | `/static/v1.2.3/logo.svg` |
| API responses | Cache-Control headers | `max-age=300, stale-while-revalidate=60` |

**Next.js Asset Versioning:**

```javascript
// next.config.js
module.exports = {
  // Generate unique build ID from git commit
  generateBuildId: async () => {
    return process.env.GIT_COMMIT_SHA || require('child_process')
      .execSync('git rev-parse HEAD')
      .toString().trim();
  },

  // All static assets include build hash
  assetPrefix: process.env.CDN_URL,

  // Configure headers for caching
  async headers() {
    return [
      {
        source: '/_next/static/:path*',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
        ],
      },
      {
        source: '/static/:path*',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
        ],
      },
    ];
  },
};
```

### Geo Coverage and Edge Locations

**CloudFront Price Class Selection:**

| Price Class | Edge Locations | Monthly Cost Impact | Use Case |
|-------------|----------------|---------------------|----------|
| PriceClass_All | 450+ global | Highest | Global users required |
| PriceClass_200 | 200+ (no SA, AU) | Medium | **Selected** - Primary India + global reach |
| PriceClass_100 | 100 (US, EU only) | Lowest | Not suitable - poor India coverage |

**India-Specific Edge Locations (Primary Market):**
- Mumbai (2 locations)
- Chennai
- Hyderabad
- New Delhi
- Bengaluru

**Origin Shield Configuration:**

```hcl
# Origin Shield in Mumbai for optimal India performance
origin {
  domain_name = aws_s3_bucket.media.bucket_regional_domain_name
  origin_id   = "S3-media"

  origin_shield {
    enabled              = true
    origin_shield_region = "ap-south-1"  # Mumbai
  }
}
```

### Cost Controls

**Cost Optimization Strategies:**

| Strategy | Implementation | Estimated Savings |
|----------|----------------|-------------------|
| Origin Shield | Single cache fill point | 30-50% origin requests |
| Compression | Brotli/Gzip for text | 60-80% bandwidth |
| Price Class 200 | Skip expensive regions | 20-30% vs PriceClass_All |
| Long TTLs | Aggressive caching | 40-60% origin requests |
| Reserved Capacity | 1-year commitment | 30% for predictable traffic |

**Monthly Cost Estimation:**

| Component | Unit | Est. Volume | Est. Cost |
|-----------|------|-------------|-----------|
| Data Transfer Out | GB | 500 GB | $42.50 |
| HTTP Requests | 10K | 10M | $7.50 |
| HTTPS Requests | 10K | 50M | $50.00 |
| Origin Shield | Requests | 5M | $4.00 |
| Invalidations | Paths | 500 | $0 (under 1000) |
| **Total** | | | **~$104/month** |

**Cost Alerts:**

```hcl
resource "aws_cloudwatch_metric_alarm" "cdn_cost_anomaly" {
  alarm_name          = "cloudfront-cost-anomaly"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = 86400  # Daily
  statistic           = "Maximum"
  threshold           = 200    # Alert if daily CDN cost > $200
  alarm_description   = "CloudFront costs exceeded daily threshold"

  dimensions = {
    ServiceName = "AmazonCloudFront"
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}
```

### Open Questions - Answered

- **Q:** How will private assets and signed URLs be managed?
  - **A:** Private assets use CloudFront signed URLs with the following implementation:

    **Signed URL Configuration:**

    ```hcl
    # CloudFront Key Group for signing
    resource "aws_cloudfront_public_key" "signing" {
      name        = "ship-chandlery-signing-key"
      encoded_key = file("${path.module}/keys/cloudfront-public.pem")
    }

    resource "aws_cloudfront_key_group" "signing" {
      name  = "ship-chandlery-signers"
      items = [aws_cloudfront_public_key.signing.id]
    }

    # Cache behavior for private documents
    ordered_cache_behavior {
      path_pattern     = "/documents/*"
      allowed_methods  = ["GET", "HEAD"]
      cached_methods   = ["GET", "HEAD"]
      target_origin_id = "S3-documents"

      trusted_key_groups = [aws_cloudfront_key_group.signing.id]

      forwarded_values {
        query_string = true  # For signed URL parameters
        cookies { forward = "none" }
      }

      viewer_protocol_policy = "https-only"
      min_ttl                = 0
      default_ttl            = 0
      max_ttl                = 3600
    }
    ```

    **Signed URL Service:**

    ```typescript
    @Injectable()
    export class SignedUrlService {
      private readonly keyPairId: string;
      private readonly privateKey: string;
      private readonly cloudFrontDomain: string;

      async generateSignedUrl(
        key: string,
        expiresIn: number = 3600,
        options: SignedUrlOptions = {},
      ): Promise<string> {
        const url = `https://${this.cloudFrontDomain}/${key}`;
        const expires = Math.floor(Date.now() / 1000) + expiresIn;

        const policy = {
          Statement: [{
            Resource: url,
            Condition: {
              DateLessThan: { 'AWS:EpochTime': expires },
              ...(options.ipAddress && {
                IpAddress: { 'AWS:SourceIp': `${options.ipAddress}/32` },
              }),
            },
          }],
        };

        const signedUrl = getSignedUrl({
          url,
          keyPairId: this.keyPairId,
          privateKey: this.privateKey,
          policy: JSON.stringify(policy),
        });

        return signedUrl;
      }

      // Generate signed cookies for streaming/multiple files
      async generateSignedCookies(
        pathPattern: string,
        expiresIn: number = 3600,
      ): Promise<SignedCookies> {
        const expires = Math.floor(Date.now() / 1000) + expiresIn;

        const policy = {
          Statement: [{
            Resource: `https://${this.cloudFrontDomain}${pathPattern}`,
            Condition: {
              DateLessThan: { 'AWS:EpochTime': expires },
            },
          }],
        };

        return getSignedCookies({
          keyPairId: this.keyPairId,
          privateKey: this.privateKey,
          policy: JSON.stringify(policy),
        });
      }
    }
    ```

    **Access Pattern for Private Documents:**

    | Document Type | URL Expiration | IP Restriction | Audit Logging |
    |---------------|----------------|----------------|---------------|
    | Invoice downloads | 5 minutes | Optional | Yes |
    | Contract viewing | 1 hour | Yes | Yes |
    | Bulk export files | 15 minutes | Yes | Yes |
    | KYC documents | 5 minutes | Yes | Yes |

---

## References
- [Amazon CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [CloudFront Best Practices](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/best-practices.html)
- [Lambda@Edge](https://docs.aws.amazon.com/lambda/latest/dg/lambda-edge.html)
