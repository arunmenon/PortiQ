# ADR-NF-019: Observability Stack

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Infrastructure

---

## Context

The platform requires comprehensive observability for monitoring, debugging, and maintaining production systems.

### Business Context
Observability requirements:
- Real-time system health monitoring
- Performance tracking and optimization
- Error tracking and debugging
- Audit trail for compliance
- Business metrics visibility
- SLA monitoring and reporting

### Technical Context
- AWS infrastructure (ADR-NF-011)
- ECS Fargate containers (ADR-NF-012)
- NestJS application (ADR-NF-006)
- Multiple services (API, workers, schedulers)
- BullMQ job processing (ADR-NF-008)

### Assumptions
- AWS-native solutions preferred for integration
- Centralized logging essential
- Distributed tracing needed for debugging
- Custom metrics for business KPIs
- Cost-effective at startup scale

---

## Decision Drivers

- AWS integration
- Cost efficiency
- Operational simplicity
- Debugging capability
- Alerting flexibility
- Scalability

---

## Considered Options

### Option 1: AWS Native (CloudWatch + X-Ray)
**Description:** Full AWS observability stack.

**Pros:**
- Native AWS integration
- No additional infrastructure
- Unified billing
- X-Ray for tracing
- Container Insights for ECS

**Cons:**
- CloudWatch Logs query limitations
- X-Ray complexity
- Vendor lock-in

### Option 2: Datadog
**Description:** Comprehensive SaaS observability platform.

**Pros:**
- Excellent UX
- Powerful querying
- Great APM
- Easy setup

**Cons:**
- Expensive at scale
- Data egress to SaaS
- Vendor dependency

### Option 3: Grafana Stack (Loki + Tempo + Prometheus)
**Description:** Open-source observability stack.

**Pros:**
- No vendor lock-in
- Powerful Grafana dashboards
- Cost-effective
- Flexible

**Cons:**
- Operational overhead
- Self-managed infrastructure
- Setup complexity

### Option 4: Hybrid (CloudWatch + Grafana Cloud)
**Description:** AWS native logging with Grafana Cloud for visualization.

**Pros:**
- Best of both worlds
- Powerful dashboards
- Managed Grafana
- Reasonable cost

**Cons:**
- Two systems to manage
- Data duplication concerns

---

## Decision

**Chosen Option:** AWS Native (CloudWatch + X-Ray) with Grafana for Dashboards

We will use AWS CloudWatch for logs and metrics, AWS X-Ray for distributed tracing, and self-hosted Grafana for dashboards and visualization.

### Rationale
AWS native services integrate seamlessly with our ECS infrastructure. CloudWatch provides good-enough logging and metrics at reasonable cost. X-Ray handles distributed tracing without additional infrastructure. Grafana provides superior dashboards and can query CloudWatch directly.

---

## Consequences

### Positive
- Native ECS/AWS integration
- No additional log infrastructure
- Unified AWS billing
- Distributed tracing out of box
- Flexible dashboards with Grafana

### Negative
- CloudWatch query limitations
- **Mitigation:** Export to S3 for complex analysis
- Multiple tools to learn
- **Mitigation:** Standard patterns, documentation

### Risks
- Log costs at scale: Log retention policies, sampling
- X-Ray sampling: Tune sampling rates for cost/visibility
- Alert fatigue: Careful threshold tuning, runbooks

---

## Implementation Notes

### Observability Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Observability Architecture                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │                    Application Layer                        │     │
│  │                                                             │     │
│  │   NestJS API    ─────┬───────────────┬────────────────┐    │     │
│  │   Workers       ─────┤               │                │    │     │
│  │   Schedulers    ─────┘               │                │    │     │
│  │                                      │                │    │     │
│  │   Winston       Pino-http       OpenTelemetry   Custom    │     │
│  │   (Logs)        (Access)        (Traces)        (Metrics) │     │
│  │                                                             │     │
│  └───────┬──────────────┬──────────────┬──────────────┬──────┘     │
│          │              │              │              │              │
│          ▼              ▼              ▼              ▼              │
│  ┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐       │
│  │  CloudWatch  │ │CloudWatch│ │  X-Ray   │ │  CloudWatch  │       │
│  │    Logs      │ │  Logs    │ │          │ │   Metrics    │       │
│  └──────┬───────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘       │
│         │              │            │              │                 │
│         └──────────────┴────────────┴──────────────┘                 │
│                              │                                        │
│                              ▼                                        │
│                    ┌──────────────────┐                              │
│                    │     Grafana      │                              │
│                    │   (Dashboards)   │                              │
│                    └────────┬─────────┘                              │
│                             │                                        │
│                    ┌────────▼─────────┐                              │
│                    │      Alerts      │                              │
│                    │  (CloudWatch +   │                              │
│                    │   Grafana)       │                              │
│                    └──────────────────┘                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Structured Logging Configuration

```typescript
// logging/logging.module.ts
import { WinstonModule } from 'nest-winston';
import * as winston from 'winston';

@Module({
  imports: [
    WinstonModule.forRootAsync({
      imports: [ConfigModule],
      useFactory: (configService: ConfigService) => ({
        transports: [
          // Console for local development
          new winston.transports.Console({
            format: winston.format.combine(
              winston.format.timestamp(),
              winston.format.colorize(),
              winston.format.printf(({ timestamp, level, message, ...meta }) => {
                return `${timestamp} [${level}]: ${message} ${
                  Object.keys(meta).length ? JSON.stringify(meta) : ''
                }`;
              }),
            ),
          }),
          // JSON format for CloudWatch
          ...(configService.get('NODE_ENV') === 'production'
            ? [
                new winston.transports.Console({
                  format: winston.format.combine(
                    winston.format.timestamp(),
                    winston.format.json(),
                  ),
                }),
              ]
            : []),
        ],
        // Default metadata
        defaultMeta: {
          service: configService.get('SERVICE_NAME'),
          environment: configService.get('NODE_ENV'),
          version: configService.get('APP_VERSION'),
        },
      }),
      inject: [ConfigService],
    }),
  ],
  exports: [WinstonModule],
})
export class LoggingModule {}
```

### Request Context Logging

```typescript
// logging/middleware/request-context.middleware.ts
import { v4 as uuidv4 } from 'uuid';
import { AsyncLocalStorage } from 'async_hooks';

export const requestContext = new AsyncLocalStorage<RequestContext>();

interface RequestContext {
  requestId: string;
  correlationId: string;
  userId?: string;
  organizationId?: string;
  traceId?: string;
}

@Injectable()
export class RequestContextMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction) {
    const requestId = uuidv4();
    const correlationId = req.headers['x-correlation-id'] as string || requestId;
    const traceId = req.headers['x-amzn-trace-id'] as string;

    const context: RequestContext = {
      requestId,
      correlationId,
      traceId,
    };

    res.setHeader('x-request-id', requestId);
    res.setHeader('x-correlation-id', correlationId);

    requestContext.run(context, () => {
      next();
    });
  }
}

// Utility to get current context
export function getRequestContext(): RequestContext | undefined {
  return requestContext.getStore();
}
```

### Logger Service with Context

```typescript
// logging/services/logger.service.ts
import { Inject, Injectable, LoggerService } from '@nestjs/common';
import { WINSTON_MODULE_PROVIDER } from 'nest-winston';
import { Logger } from 'winston';
import { getRequestContext } from '../middleware/request-context.middleware';

@Injectable()
export class AppLoggerService implements LoggerService {
  constructor(
    @Inject(WINSTON_MODULE_PROVIDER)
    private readonly logger: Logger,
  ) {}

  private addContext(meta: Record<string, any> = {}): Record<string, any> {
    const context = getRequestContext();
    return {
      ...meta,
      requestId: context?.requestId,
      correlationId: context?.correlationId,
      userId: context?.userId,
      organizationId: context?.organizationId,
      traceId: context?.traceId,
    };
  }

  log(message: string, meta?: Record<string, any>) {
    this.logger.info(message, this.addContext(meta));
  }

  error(message: string, trace?: string, meta?: Record<string, any>) {
    this.logger.error(message, this.addContext({ ...meta, trace }));
  }

  warn(message: string, meta?: Record<string, any>) {
    this.logger.warn(message, this.addContext(meta));
  }

  debug(message: string, meta?: Record<string, any>) {
    this.logger.debug(message, this.addContext(meta));
  }

  verbose(message: string, meta?: Record<string, any>) {
    this.logger.verbose(message, this.addContext(meta));
  }
}
```

### CloudWatch Metrics

```typescript
// metrics/services/metrics.service.ts
import {
  CloudWatchClient,
  PutMetricDataCommand,
} from '@aws-sdk/client-cloudwatch';

@Injectable()
export class MetricsService {
  private readonly cloudwatch: CloudWatchClient;
  private readonly namespace: string;
  private readonly buffer: MetricDatum[] = [];
  private readonly FLUSH_INTERVAL = 60000; // 1 minute

  constructor(private readonly configService: ConfigService) {
    this.cloudwatch = new CloudWatchClient({
      region: configService.get('AWS_REGION'),
    });
    this.namespace = `ShipChandlery/${configService.get('NODE_ENV')}`;

    // Flush metrics periodically
    setInterval(() => this.flush(), this.FLUSH_INTERVAL);
  }

  // Business metrics
  recordOrderCreated(value: number = 1, dimensions?: Record<string, string>) {
    this.putMetric('OrdersCreated', value, 'Count', dimensions);
  }

  recordOrderValue(value: number, dimensions?: Record<string, string>) {
    this.putMetric('OrderValue', value, 'None', dimensions);
  }

  recordRfqPublished(value: number = 1, dimensions?: Record<string, string>) {
    this.putMetric('RfqsPublished', value, 'Count', dimensions);
  }

  recordQuoteSubmitted(value: number = 1, dimensions?: Record<string, string>) {
    this.putMetric('QuotesSubmitted', value, 'Count', dimensions);
  }

  // Technical metrics
  recordApiLatency(endpoint: string, latencyMs: number) {
    this.putMetric('ApiLatency', latencyMs, 'Milliseconds', { endpoint });
  }

  recordDocumentProcessingTime(documentId: string, timeMs: number) {
    this.putMetric('DocumentProcessingTime', timeMs, 'Milliseconds');
  }

  recordJobQueueDepth(queueName: string, depth: number) {
    this.putMetric('JobQueueDepth', depth, 'Count', { queue: queueName });
  }

  recordCacheHitRate(cache: string, hitRate: number) {
    this.putMetric('CacheHitRate', hitRate, 'Percent', { cache });
  }

  private putMetric(
    name: string,
    value: number,
    unit: string,
    dimensions?: Record<string, string>,
  ) {
    const metric: MetricDatum = {
      MetricName: name,
      Value: value,
      Unit: unit,
      Timestamp: new Date(),
      Dimensions: dimensions
        ? Object.entries(dimensions).map(([Name, Value]) => ({ Name, Value }))
        : undefined,
    };

    this.buffer.push(metric);

    // Flush if buffer is full
    if (this.buffer.length >= 20) {
      this.flush();
    }
  }

  private async flush() {
    if (this.buffer.length === 0) return;

    const metrics = this.buffer.splice(0, 20);

    try {
      await this.cloudwatch.send(
        new PutMetricDataCommand({
          Namespace: this.namespace,
          MetricData: metrics,
        }),
      );
    } catch (error) {
      this.logger.error('Failed to send metrics', { error: error.message });
      // Re-add metrics to buffer on failure
      this.buffer.unshift(...metrics);
    }
  }
}
```

### X-Ray Tracing

```typescript
// tracing/tracing.module.ts
import * as AWSXRay from 'aws-xray-sdk';
import { HttpModule } from '@nestjs/axios';

// Instrument AWS SDK
AWSXRay.captureAWS(require('aws-sdk'));

// Instrument HTTP
AWSXRay.captureHTTPsGlobal(require('http'));
AWSXRay.captureHTTPsGlobal(require('https'));

@Module({
  imports: [
    HttpModule.registerAsync({
      useFactory: () => ({
        // HTTP client will be automatically traced
      }),
    }),
  ],
})
export class TracingModule {}

// main.ts
import * as AWSXRay from 'aws-xray-sdk';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // X-Ray middleware
  app.use(AWSXRay.express.openSegment('ship-chandlery-api'));

  // ... other middleware

  // Close segment at end
  app.use(AWSXRay.express.closeSegment());

  await app.listen(3000);
}
```

### Custom Tracing Decorator

```typescript
// tracing/decorators/trace.decorator.ts
import * as AWSXRay from 'aws-xray-sdk';

export function Trace(name?: string): MethodDecorator {
  return function (
    target: any,
    propertyKey: string,
    descriptor: PropertyDescriptor,
  ) {
    const originalMethod = descriptor.value;
    const traceName = name || `${target.constructor.name}.${propertyKey}`;

    descriptor.value = async function (...args: any[]) {
      const segment = AWSXRay.getSegment();

      if (!segment) {
        return originalMethod.apply(this, args);
      }

      const subsegment = segment.addNewSubsegment(traceName);

      try {
        const result = await originalMethod.apply(this, args);
        subsegment.close();
        return result;
      } catch (error) {
        subsegment.addError(error);
        subsegment.close();
        throw error;
      }
    };

    return descriptor;
  };
}

// Usage
@Injectable()
export class OrderService {
  @Trace('OrderService.createOrder')
  async createOrder(dto: CreateOrderDto): Promise<Order> {
    // Method will be traced
  }
}
```

### Health Check Endpoints

```typescript
// health/health.controller.ts
import {
  HealthCheckService,
  HttpHealthIndicator,
  TypeOrmHealthIndicator,
  MemoryHealthIndicator,
  DiskHealthIndicator,
} from '@nestjs/terminus';

@Controller('health')
export class HealthController {
  constructor(
    private health: HealthCheckService,
    private db: TypeOrmHealthIndicator,
    private http: HttpHealthIndicator,
    private memory: MemoryHealthIndicator,
    private disk: DiskHealthIndicator,
    private redis: RedisHealthIndicator,
  ) {}

  @Get()
  @HealthCheck()
  check() {
    return this.health.check([
      // Database
      () => this.db.pingCheck('database'),

      // Redis
      () => this.redis.isHealthy('redis'),

      // Memory (heap < 500MB)
      () => this.memory.checkHeap('memory_heap', 500 * 1024 * 1024),

      // Disk (storage < 90%)
      () =>
        this.disk.checkStorage('storage', {
          thresholdPercent: 0.9,
          path: '/',
        }),
    ]);
  }

  @Get('live')
  liveness() {
    return { status: 'ok' };
  }

  @Get('ready')
  @HealthCheck()
  readiness() {
    return this.health.check([
      () => this.db.pingCheck('database'),
      () => this.redis.isHealthy('redis'),
    ]);
  }
}
```

### CloudWatch Alarms

```hcl
# terraform/modules/monitoring/alarms.tf

# API Error Rate
resource "aws_cloudwatch_metric_alarm" "api_errors" {
  alarm_name          = "ship-chandlery-api-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "5XXError"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "API 5XX errors exceeded threshold"

  dimensions = {
    LoadBalancer = aws_lb.api.arn_suffix
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

# API Latency
resource "aws_cloudwatch_metric_alarm" "api_latency" {
  alarm_name          = "ship-chandlery-api-latency-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  extended_statistic  = "p95"
  threshold           = 1  # 1 second
  alarm_description   = "API p95 latency exceeded 1 second"

  dimensions = {
    LoadBalancer = aws_lb.api.arn_suffix
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}

# Database CPU
resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "ship-chandlery-rds-cpu-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "RDS CPU utilization exceeded 80%"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}

# Job Queue Depth
resource "aws_cloudwatch_metric_alarm" "job_queue_depth" {
  alarm_name          = "ship-chandlery-job-queue-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "JobQueueDepth"
  namespace           = "ShipChandlery/${var.environment}"
  period              = 300
  statistic           = "Maximum"
  threshold           = 1000
  alarm_description   = "Job queue depth exceeded 1000"

  dimensions = {
    queue = "document-processing"
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Ship Chandlery Overview",
    "panels": [
      {
        "title": "API Request Rate",
        "type": "graph",
        "datasource": "CloudWatch",
        "targets": [
          {
            "namespace": "AWS/ApplicationELB",
            "metricName": "RequestCount",
            "statistics": ["Sum"],
            "period": "60"
          }
        ]
      },
      {
        "title": "API Latency (p50, p95, p99)",
        "type": "graph",
        "datasource": "CloudWatch",
        "targets": [
          {
            "namespace": "AWS/ApplicationELB",
            "metricName": "TargetResponseTime",
            "statistics": ["p50", "p95", "p99"],
            "period": "60"
          }
        ]
      },
      {
        "title": "Orders Created",
        "type": "stat",
        "datasource": "CloudWatch",
        "targets": [
          {
            "namespace": "ShipChandlery/production",
            "metricName": "OrdersCreated",
            "statistics": ["Sum"],
            "period": "3600"
          }
        ]
      },
      {
        "title": "Document Processing Queue",
        "type": "graph",
        "datasource": "CloudWatch",
        "targets": [
          {
            "namespace": "ShipChandlery/production",
            "metricName": "JobQueueDepth",
            "dimensions": { "queue": "document-processing" },
            "statistics": ["Average"],
            "period": "60"
          }
        ]
      }
    ]
  }
}
```

### Dependencies
- ADR-NF-011: Cloud Provider - AWS Mumbai
- ADR-NF-012: Container Orchestration
- ADR-NF-008: Async Processing (BullMQ)

### Migration Strategy
1. Configure CloudWatch Logs for ECS tasks
2. Set up X-Ray tracing
3. Implement structured logging
4. Create custom metrics service
5. Deploy Grafana (ECS or managed)
6. Create dashboards
7. Configure alerts
8. Create runbooks

---

## Operational Considerations

### Logging Standards

**Log Levels and Usage:**

| Level | When to Use | Example |
|-------|-------------|---------|
| ERROR | Unrecoverable errors, exceptions | Database connection failed, payment processing error |
| WARN | Recoverable issues, deprecation notices | Rate limit approaching, retry succeeded |
| INFO | Business events, state changes | Order created, user logged in, RFQ published |
| DEBUG | Detailed flow information | Request/response details, cache hits/misses |
| TRACE | Very detailed debugging | SQL queries, external API calls (dev only) |

**Structured Log Format:**

```typescript
interface LogEntry {
  // Required fields
  timestamp: string;        // ISO 8601 format
  level: 'ERROR' | 'WARN' | 'INFO' | 'DEBUG';
  message: string;
  service: string;          // e.g., "api", "worker", "scheduler"

  // Request context (when available)
  requestId?: string;
  correlationId?: string;
  traceId?: string;
  spanId?: string;

  // User context (when authenticated)
  userId?: string;
  organizationId?: string;

  // Error context (for ERROR level)
  error?: {
    name: string;
    message: string;
    stack?: string;
    code?: string;
  };

  // Business context
  action?: string;          // e.g., "order.created", "payment.failed"
  entityType?: string;      // e.g., "Order", "RFQ", "User"
  entityId?: string;

  // Performance
  duration?: number;        // milliseconds

  // Additional metadata
  metadata?: Record<string, any>;
}
```

**Log Examples:**

```json
// INFO - Business event
{
  "timestamp": "2025-01-20T10:30:45.123Z",
  "level": "INFO",
  "message": "Order created successfully",
  "service": "api",
  "requestId": "req-abc123",
  "correlationId": "corr-xyz789",
  "userId": "user-123",
  "organizationId": "org-456",
  "action": "order.created",
  "entityType": "Order",
  "entityId": "order-789",
  "metadata": {
    "total": 15000.00,
    "currency": "INR",
    "lineItemCount": 5
  }
}

// ERROR - Exception
{
  "timestamp": "2025-01-20T10:31:00.456Z",
  "level": "ERROR",
  "message": "Payment processing failed",
  "service": "api",
  "requestId": "req-def456",
  "userId": "user-123",
  "error": {
    "name": "PaymentError",
    "message": "Insufficient funds",
    "code": "INSUFFICIENT_FUNDS",
    "stack": "PaymentError: Insufficient funds\n    at PaymentService.charge..."
  },
  "action": "payment.failed",
  "entityType": "Order",
  "entityId": "order-789"
}
```

### Metrics Standards

**Metric Naming Convention:**

```
{namespace}/{service}/{metric_name}
Examples:
- ShipChandlery/api/request_count
- ShipChandlery/api/request_latency_ms
- ShipChandlery/worker/job_queue_depth
- ShipChandlery/business/orders_created
```

**Standard Metrics by Service:**

| Service | Metric | Type | Dimensions |
|---------|--------|------|------------|
| API | request_count | Counter | endpoint, method, status |
| API | request_latency_ms | Histogram | endpoint, method |
| API | error_count | Counter | endpoint, error_type |
| Worker | job_count | Counter | queue, status |
| Worker | job_duration_ms | Histogram | queue, job_type |
| Worker | queue_depth | Gauge | queue |
| Database | query_count | Counter | operation, table |
| Database | query_latency_ms | Histogram | operation |
| Database | connection_pool_size | Gauge | - |
| Cache | hit_count | Counter | cache_name |
| Cache | miss_count | Counter | cache_name |
| Cache | hit_rate | Gauge | cache_name |

**Business Metrics:**

| Metric | Description | Dimensions |
|--------|-------------|------------|
| orders_created | Number of orders created | organization_tier |
| orders_value | Total order value | currency |
| rfqs_published | Number of RFQs published | - |
| quotes_submitted | Number of quotes submitted | - |
| documents_processed | Documents through AI pipeline | document_type |
| active_users | DAU/MAU | organization_tier |

### Tracing Standards

**Trace Sampling Strategy:**

| Environment | Sample Rate | Head-Based | Tail-Based |
|-------------|-------------|------------|------------|
| Development | 100% | Yes | No |
| Staging | 100% | Yes | No |
| Production | 10% | Yes | Yes (errors) |

**Production Sampling Rules:**

```typescript
const samplingRules = [
  // Always trace errors
  { match: { status: '5xx' }, rate: 1.0 },
  { match: { status: '4xx' }, rate: 0.5 },

  // Always trace slow requests
  { match: { duration: '>1000ms' }, rate: 1.0 },

  // Sample high-value operations
  { match: { endpoint: '/api/v1/orders' }, rate: 0.5 },
  { match: { endpoint: '/api/v1/payments' }, rate: 1.0 },

  // Health checks - no tracing
  { match: { endpoint: '/health' }, rate: 0 },

  // Default sampling
  { match: { default: true }, rate: 0.1 },
];
```

**Required Span Attributes:**

| Attribute | Description | Example |
|-----------|-------------|---------|
| service.name | Service identifier | "ship-chandlery-api" |
| service.version | Application version | "1.2.3" |
| deployment.environment | Environment name | "production" |
| http.method | HTTP method | "POST" |
| http.url | Request URL | "/api/v1/orders" |
| http.status_code | Response status | 200 |
| db.system | Database type | "postgresql" |
| db.statement | Query (sanitized) | "SELECT * FROM orders WHERE..." |
| user.id | User identifier | "user-123" |
| organization.id | Tenant identifier | "org-456" |

### Alert Thresholds

**Critical Alerts (Page On-Call):**

| Alert | Condition | Duration | Action |
|-------|-----------|----------|--------|
| API Down | Health check failure | 2 min | Page immediately |
| Error Rate Spike | 5xx rate > 5% | 5 min | Page immediately |
| Database Down | Connection failures | 1 min | Page immediately |
| Payment Failures | > 10% failure rate | 5 min | Page immediately |
| Disk Space Critical | > 95% used | 5 min | Page immediately |

**Warning Alerts (Notify Team):**

| Alert | Condition | Duration | Action |
|-------|-----------|----------|--------|
| High Latency | p95 > 2s | 10 min | Slack notification |
| Elevated Error Rate | 5xx rate > 1% | 10 min | Slack notification |
| Queue Backlog | Depth > 1000 | 15 min | Slack notification |
| Memory Pressure | > 85% used | 10 min | Slack notification |
| CPU High | > 80% sustained | 15 min | Slack notification |
| Certificate Expiry | < 14 days | Daily | Email notification |

**CloudWatch Alarm Configuration:**

```hcl
resource "aws_cloudwatch_metric_alarm" "api_error_rate" {
  alarm_name          = "api-error-rate-critical"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 5

  metric_query {
    id          = "error_rate"
    expression  = "(errors / requests) * 100"
    label       = "Error Rate %"
    return_data = true
  }

  metric_query {
    id = "errors"
    metric {
      metric_name = "5XXError"
      namespace   = "AWS/ApplicationELB"
      period      = 300
      stat        = "Sum"
      dimensions  = { LoadBalancer = aws_lb.api.arn_suffix }
    }
  }

  metric_query {
    id = "requests"
    metric {
      metric_name = "RequestCount"
      namespace   = "AWS/ApplicationELB"
      period      = 300
      stat        = "Sum"
      dimensions  = { LoadBalancer = aws_lb.api.arn_suffix }
    }
  }

  alarm_actions = [aws_sns_topic.critical_alerts.arn]
  ok_actions    = [aws_sns_topic.critical_alerts.arn]
}
```

### Cost Controls

**Log Retention and Cost Optimization:**

| Log Group | Retention | Storage Class | Est. Monthly Cost |
|-----------|-----------|---------------|-------------------|
| /ecs/api | 30 days | Standard | $15-30 |
| /ecs/worker | 30 days | Standard | $5-10 |
| /lambda/* | 14 days | Standard | $2-5 |
| /rds/* | 7 days | Standard | $5-10 |
| Exported (S3) | 1 year | IA -> Glacier | $2-5 |

**Metrics Cost Optimization:**

- Use metric math instead of separate metrics where possible
- Set appropriate resolution (1-minute for critical, 5-minute for others)
- Use metric filters instead of custom metrics for log-derived data
- Implement dimension limits (max 10 per metric)

**Trace Cost Optimization:**

- Production sampling at 10% reduces costs by 90%
- Always-sample errors and slow requests for debugging
- Use X-Ray groups to filter storage
- Set trace retention to 30 days (default)

**Monthly Cost Estimate:**

| Component | Est. Cost |
|-----------|-----------|
| CloudWatch Logs | $40-60 |
| CloudWatch Metrics | $20-30 |
| CloudWatch Alarms | $5-10 |
| X-Ray Traces | $15-25 |
| Grafana (self-hosted) | $10 (ECS) |
| **Total** | **$90-135/month** |

### Open Questions - Answered

- **Q:** Which SLOs and dashboards are required for MVP?
  - **A:**

    **MVP SLOs:**

    | SLO | Target | Measurement Window | Error Budget |
    |----|--------|-------------------|--------------|
    | API Availability | 99.5% | Monthly | 3.6 hours downtime |
    | API Latency (p95) | < 500ms | Monthly | 5% of requests > 500ms |
    | Error Rate | < 1% | Weekly | 1% of requests return 5xx |
    | Order Processing | < 30s | Monthly | 95% complete in 30s |
    | Document Processing | < 5min | Monthly | 90% complete in 5min |

    **MVP Dashboards:**

    1. **Executive Overview**
       - Total active users (DAU/WAU/MAU)
       - Orders created (count and value)
       - RFQs published and quotes received
       - System health indicator (green/yellow/red)

    2. **API Health**
       - Request rate (requests/second)
       - Latency distribution (p50, p95, p99)
       - Error rate by endpoint
       - HTTP status code distribution

    3. **Infrastructure**
       - ECS task count and CPU/Memory utilization
       - RDS CPU, connections, and query latency
       - Redis memory usage and hit rate
       - S3 request count and bandwidth

    4. **Business Operations**
       - Order funnel (viewed -> carted -> ordered)
       - RFQ lifecycle (created -> published -> quoted -> awarded)
       - Document processing queue and success rate
       - Top errors by type and frequency

    **Dashboard JSON (Grafana):**

    ```json
    {
      "dashboard": {
        "title": "Ship Chandlery - MVP Overview",
        "rows": [
          {
            "title": "Key Metrics",
            "panels": [
              {
                "title": "API Availability (30d)",
                "type": "gauge",
                "targets": [{ "expr": "avg_over_time(up{job='api'}[30d]) * 100" }],
                "thresholds": [{ "value": 99.5, "color": "green" }, { "value": 99, "color": "yellow" }]
              },
              {
                "title": "P95 Latency",
                "type": "stat",
                "targets": [{ "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))" }]
              },
              {
                "title": "Error Rate",
                "type": "stat",
                "targets": [{ "expr": "sum(rate(http_requests_total{status=~'5..'}[5m])) / sum(rate(http_requests_total[5m])) * 100" }]
              },
              {
                "title": "Orders Today",
                "type": "stat",
                "targets": [{ "expr": "sum(increase(orders_created_total[24h]))" }]
              }
            ]
          }
        ]
      }
    }
    ```

---

## References
- [AWS CloudWatch Documentation](https://docs.aws.amazon.com/cloudwatch/)
- [AWS X-Ray Documentation](https://docs.aws.amazon.com/xray/)
- [Grafana CloudWatch Data Source](https://grafana.com/docs/grafana/latest/datasources/cloudwatch/)
- [Observability Best Practices](https://aws.amazon.com/blogs/mt/observability-best-practices/)
