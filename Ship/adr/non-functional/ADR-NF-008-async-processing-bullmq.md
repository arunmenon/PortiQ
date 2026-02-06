# ADR-NF-008: Async Processing (BullMQ)

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

The platform requires reliable asynchronous job processing for long-running tasks, background work, and event-driven operations.

### Business Context
Async processing needs:
- Document AI pipeline (parsing, extraction, matching)
- Email and notification delivery
- Report generation
- Data import/export operations
- Scheduled tasks (cleanup, sync, reminders)
- Webhook delivery with retries

### Technical Context
- NestJS backend with TypeScript
- Redis available for caching (ADR-NF-005)
- Need for job retries, priorities, and scheduling
- Worker scaling independent of API
- Job monitoring and visibility

### Assumptions
- Redis is the queue backend
- Job persistence needed for reliability
- Multiple worker instances possible
- Job monitoring UI helpful for operations

---

## Decision Drivers

- Reliability and durability
- TypeScript support
- NestJS integration
- Redis compatibility
- Job monitoring capabilities
- Scalability

---

## Considered Options

### Option 1: BullMQ
**Description:** Premium Redis-based queue with advanced features.

**Pros:**
- Built for Redis
- Excellent TypeScript support
- NestJS integration (@nestjs/bullmq)
- Advanced features (priorities, delays, retries)
- Rate limiting built-in
- Bull Board for monitoring

**Cons:**
- Redis dependency
- Memory usage for large queues

### Option 2: AWS SQS + Lambda
**Description:** Cloud-native serverless queue processing.

**Pros:**
- Fully managed
- Auto-scaling
- Pay per use
- High durability

**Cons:**
- AWS lock-in
- Cold starts
- Different programming model
- Limited to Lambda constraints

### Option 3: RabbitMQ
**Description:** Traditional message broker.

**Pros:**
- Mature and proven
- Complex routing patterns
- Multiple protocols
- Clustering

**Cons:**
- Additional infrastructure
- More complex operations
- Heavier than Redis-based solutions

### Option 4: Database-Backed Queue
**Description:** PostgreSQL table as job queue.

**Pros:**
- No additional infrastructure
- ACID guarantees
- Simple setup

**Cons:**
- Polling overhead
- Limited features
- Performance ceiling
- Not purpose-built

---

## Decision

**Chosen Option:** BullMQ

We will use BullMQ for asynchronous job processing, leveraging its TypeScript support, NestJS integration, and advanced queue features.

### Rationale
BullMQ is the natural choice given our existing Redis infrastructure (ADR-NF-005). Its first-class TypeScript support and official NestJS module provide excellent developer experience. Advanced features like job priorities, delays, retries, and rate limiting handle our complex processing needs without additional complexity.

---

## Consequences

### Positive
- Excellent TypeScript/NestJS integration
- Advanced queue features out of the box
- Unified with caching infrastructure
- Bull Board for monitoring
- Reliable job processing with retries

### Negative
- Redis memory usage for large queues
- **Mitigation:** Job data in database, only references in queue
- Single Redis dependency
- **Mitigation:** Redis Cluster for HA if needed

### Risks
- Redis failure loses queue: Redis persistence, HA configuration
- Job processing bottlenecks: Horizontal worker scaling
- Memory exhaustion: Job TTL, data externalization

---

## Implementation Notes

### Module Configuration

```typescript
// queue/queue.module.ts
import { BullModule } from '@nestjs/bullmq';

@Module({
  imports: [
    BullModule.forRootAsync({
      imports: [ConfigModule],
      useFactory: async (configService: ConfigService) => ({
        connection: {
          host: configService.get('REDIS_HOST'),
          port: configService.get('REDIS_PORT'),
          password: configService.get('REDIS_PASSWORD')
        },
        defaultJobOptions: {
          attempts: 3,
          backoff: {
            type: 'exponential',
            delay: 1000
          },
          removeOnComplete: {
            count: 100,
            age: 24 * 3600  // 24 hours
          },
          removeOnFail: {
            count: 1000,
            age: 7 * 24 * 3600  // 7 days
          }
        }
      }),
      inject: [ConfigService]
    }),

    // Register queues
    BullModule.registerQueue(
      { name: QUEUES.DOCUMENT_PROCESSING },
      { name: QUEUES.EMAIL },
      { name: QUEUES.NOTIFICATIONS },
      { name: QUEUES.DATA_IMPORT },
      { name: QUEUES.REPORTS },
      { name: QUEUES.WEBHOOKS }
    )
  ],
  exports: [BullModule]
})
export class QueueModule {}

// Queue names constant
export const QUEUES = {
  DOCUMENT_PROCESSING: 'document-processing',
  EMAIL: 'email',
  NOTIFICATIONS: 'notifications',
  DATA_IMPORT: 'data-import',
  REPORTS: 'reports',
  WEBHOOKS: 'webhooks'
};
```

### Job Producer

```typescript
// document-ai/services/document-processor.service.ts
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';

@Injectable()
export class DocumentProcessorService {
  constructor(
    @InjectQueue(QUEUES.DOCUMENT_PROCESSING)
    private readonly documentQueue: Queue
  ) {}

  async processDocument(documentId: string, options: ProcessOptions = {}): Promise<string> {
    const job = await this.documentQueue.add(
      'parse-document',
      {
        documentId,
        options
      },
      {
        priority: options.urgent ? 1 : 5,
        delay: options.delayMs,
        jobId: `doc-${documentId}`,  // Deduplication
      }
    );

    return job.id;
  }

  async processDocumentBatch(documentIds: string[]): Promise<string[]> {
    const jobs = documentIds.map((id, index) => ({
      name: 'parse-document',
      data: { documentId: id },
      opts: {
        jobId: `doc-${id}`,
        priority: 5,
        delay: index * 100  // Stagger to prevent thundering herd
      }
    }));

    const results = await this.documentQueue.addBulk(jobs);
    return results.map(j => j.id);
  }

  async getJobStatus(jobId: string): Promise<JobStatus> {
    const job = await this.documentQueue.getJob(jobId);
    if (!job) return null;

    const state = await job.getState();
    return {
      id: job.id,
      state,
      progress: job.progress,
      attemptsMade: job.attemptsMade,
      failedReason: job.failedReason,
      processedOn: job.processedOn,
      finishedOn: job.finishedOn
    };
  }
}
```

### Job Consumer (Worker)

```typescript
// document-ai/processors/document.processor.ts
import { Processor, WorkerHost, OnWorkerEvent } from '@nestjs/bullmq';
import { Job } from 'bullmq';

@Processor(QUEUES.DOCUMENT_PROCESSING, {
  concurrency: 5,
  limiter: {
    max: 10,
    duration: 1000  // 10 jobs per second
  }
})
export class DocumentProcessor extends WorkerHost {
  private readonly logger = new Logger(DocumentProcessor.name);

  constructor(
    private readonly parsingService: DocumentParsingService,
    private readonly extractionService: ExtractionService,
    private readonly matchingService: SkuMatchingService
  ) {
    super();
  }

  async process(job: Job<DocumentJobData>): Promise<ProcessingResult> {
    const { documentId, options } = job.data;

    this.logger.log(`Processing document ${documentId}`);

    try {
      // Step 1: Parse document
      await job.updateProgress(10);
      const parsed = await this.parsingService.parse(documentId);

      // Step 2: Extract line items
      await job.updateProgress(40);
      const extracted = await this.extractionService.extract(parsed);

      // Step 3: Match to SKUs
      await job.updateProgress(70);
      const matched = await this.matchingService.match(extracted);

      // Step 4: Save results
      await job.updateProgress(90);
      await this.saveResults(documentId, matched);

      await job.updateProgress(100);

      return {
        documentId,
        lineItemsExtracted: extracted.length,
        matchedItems: matched.filter(m => m.confidence > 0.8).length,
        requiresReview: matched.filter(m => m.confidence <= 0.8).length
      };

    } catch (error) {
      this.logger.error(`Failed to process document ${documentId}`, error.stack);
      throw error;  // BullMQ will retry based on configuration
    }
  }

  @OnWorkerEvent('completed')
  onCompleted(job: Job) {
    this.logger.log(`Job ${job.id} completed`);
  }

  @OnWorkerEvent('failed')
  onFailed(job: Job, error: Error) {
    this.logger.error(`Job ${job.id} failed: ${error.message}`);

    // Notify if final failure
    if (job.attemptsMade >= job.opts.attempts) {
      this.notificationService.notifyJobFailure(job);
    }
  }

  @OnWorkerEvent('progress')
  onProgress(job: Job, progress: number) {
    this.logger.debug(`Job ${job.id} progress: ${progress}%`);
  }
}

interface DocumentJobData {
  documentId: string;
  options?: ProcessOptions;
}
```

### Email Queue

```typescript
// notifications/processors/email.processor.ts
@Processor(QUEUES.EMAIL, { concurrency: 10 })
export class EmailProcessor extends WorkerHost {
  constructor(
    private readonly emailService: EmailService,
    private readonly templateService: TemplateService
  ) {
    super();
  }

  async process(job: Job<EmailJobData>): Promise<void> {
    const { to, template, data, attachments } = job.data;

    // Render template
    const { subject, html, text } = await this.templateService.render(
      template,
      data
    );

    // Send email
    await this.emailService.send({
      to,
      subject,
      html,
      text,
      attachments
    });
  }
}

// Usage
@Injectable()
export class NotificationService {
  constructor(
    @InjectQueue(QUEUES.EMAIL)
    private readonly emailQueue: Queue
  ) {}

  async sendOrderConfirmation(order: Order): Promise<void> {
    await this.emailQueue.add('send-email', {
      to: order.buyer.email,
      template: 'order-confirmation',
      data: {
        orderNumber: order.orderNumber,
        items: order.lineItems,
        total: order.total
      }
    });
  }

  async sendBulkNotification(
    emails: string[],
    template: string,
    data: Record<string, any>
  ): Promise<void> {
    const jobs = emails.map(email => ({
      name: 'send-email',
      data: { to: email, template, data },
      opts: { priority: 10 }  // Lower priority for bulk
    }));

    await this.emailQueue.addBulk(jobs);
  }
}
```

### Scheduled Jobs

```typescript
// scheduler/services/scheduler.service.ts
@Injectable()
export class SchedulerService {
  constructor(
    @InjectQueue(QUEUES.DATA_IMPORT)
    private readonly importQueue: Queue
  ) {}

  async onModuleInit(): Promise<void> {
    // Schedule recurring jobs
    await this.importQueue.add(
      'sync-impa-catalog',
      {},
      {
        repeat: {
          pattern: '0 2 * * *'  // Daily at 2 AM
        },
        jobId: 'impa-sync'  // Prevent duplicates
      }
    );

    await this.importQueue.add(
      'cleanup-expired-sessions',
      {},
      {
        repeat: {
          every: 3600000  // Every hour
        },
        jobId: 'session-cleanup'
      }
    );
  }

  async pauseScheduledJob(jobId: string): Promise<void> {
    const repeatableJobs = await this.importQueue.getRepeatableJobs();
    const job = repeatableJobs.find(j => j.id === jobId);

    if (job) {
      await this.importQueue.removeRepeatableByKey(job.key);
    }
  }
}
```

### Bull Board Dashboard

```typescript
// queue/queue-dashboard.module.ts
import { BullBoardModule } from '@bull-board/nestjs';
import { BullMQAdapter } from '@bull-board/api/bullMQAdapter';

@Module({
  imports: [
    BullBoardModule.forRoot({
      route: '/admin/queues',
      adapter: BullMQAdapter
    }),
    BullBoardModule.forFeature({
      name: QUEUES.DOCUMENT_PROCESSING,
      adapter: BullMQAdapter
    }),
    BullBoardModule.forFeature({
      name: QUEUES.EMAIL,
      adapter: BullMQAdapter
    }),
    // ... other queues
  ]
})
export class QueueDashboardModule {}
```

### Job Flow (Multi-Step Processing)

```typescript
// document-ai/flows/document-processing.flow.ts
import { FlowProducer } from 'bullmq';

@Injectable()
export class DocumentProcessingFlow {
  private flowProducer: FlowProducer;

  constructor(
    @Inject('REDIS_CONNECTION')
    private readonly redis: Redis
  ) {
    this.flowProducer = new FlowProducer({ connection: redis });
  }

  async createProcessingFlow(documentId: string): Promise<string> {
    const flow = await this.flowProducer.add({
      name: 'complete-processing',
      queueName: QUEUES.DOCUMENT_PROCESSING,
      data: { documentId },
      children: [
        {
          name: 'match-skus',
          queueName: QUEUES.DOCUMENT_PROCESSING,
          data: { documentId },
          children: [
            {
              name: 'extract-items',
              queueName: QUEUES.DOCUMENT_PROCESSING,
              data: { documentId },
              children: [
                {
                  name: 'parse-document',
                  queueName: QUEUES.DOCUMENT_PROCESSING,
                  data: { documentId }
                }
              ]
            }
          ]
        }
      ]
    });

    return flow.job.id;
  }
}
```

### Dependencies
- ADR-NF-005: Caching Strategy (Redis)
- ADR-FN-006: Document AI Pipeline Architecture
- ADR-NF-009: Event-Driven Communication

### Migration Strategy
1. Set up BullMQ module in NestJS
2. Create queue configurations
3. Implement document processing queue
4. Add email/notification queues
5. Set up scheduled jobs
6. Deploy Bull Board for monitoring
7. Scale workers as needed

---

## Retry and Error Handling

### Retry Policy by Job Type

| Queue | Max Retries | Backoff | Initial Delay | Max Delay |
|-------|-------------|---------|---------------|-----------|
| document-processing | 5 | Exponential | 30s | 10min |
| email-delivery | 3 | Exponential | 60s | 15min |
| webhook-delivery | 5 | Exponential | 10s | 5min |
| data-export | 2 | Fixed | 5min | 5min |
| scheduled-tasks | 1 | None | - | - |

```typescript
// Queue configuration with retry policy
@Module({
  imports: [
    BullModule.registerQueue({
      name: 'document-processing',
      defaultJobOptions: {
        attempts: 5,
        backoff: {
          type: 'exponential',
          delay: 30000, // 30 seconds initial
        },
        removeOnComplete: 100, // Keep last 100 completed
        removeOnFail: 500,     // Keep last 500 failed for analysis
      },
    }),
  ],
})
```

### Dead Letter Queue (DLQ) Handling

```typescript
// DLQ processor for failed jobs
@Processor('dead-letter')
export class DeadLetterProcessor {
  @Process()
  async handleDeadLetter(job: Job<FailedJobData>) {
    // 1. Log detailed failure info
    this.logger.error('Job permanently failed', {
      originalQueue: job.data.originalQueue,
      jobId: job.data.originalJobId,
      error: job.data.error,
      attempts: job.data.attempts,
    });

    // 2. Alert on critical job failures
    if (job.data.severity === 'critical') {
      await this.alertService.sendPagerDuty({
        title: `Critical job failed: ${job.data.originalQueue}`,
        details: job.data.error,
      });
    }

    // 3. Store for manual review
    await this.failedJobRepository.save({
      queue: job.data.originalQueue,
      payload: job.data.originalPayload,
      error: job.data.error,
      failedAt: new Date(),
    });
  }
}

// Move to DLQ after max retries
@OnQueueFailed()
async handleFailed(job: Job, error: Error) {
  if (job.attemptsMade >= job.opts.attempts) {
    await this.deadLetterQueue.add('failed-job', {
      originalQueue: 'document-processing',
      originalJobId: job.id,
      originalPayload: job.data,
      error: error.message,
      attempts: job.attemptsMade,
      severity: this.determineSeverity(job),
    });
  }
}
```

### Job Idempotency

| Job Type | Idempotency Key | Duplicate Window |
|----------|-----------------|------------------|
| Document processing | `doc:${documentId}` | 1 hour |
| Email delivery | `email:${userId}:${templateId}:${hash}` | 24 hours |
| Webhook delivery | `webhook:${eventId}` | 1 hour |
| Report generation | `report:${reportId}:${params}` | 5 minutes |

```typescript
// Idempotent job creation
async queueDocumentProcessing(documentId: string) {
  const jobId = `doc:${documentId}`;

  // Check if job already exists or completed recently
  const existing = await this.queue.getJob(jobId);
  if (existing) {
    const state = await existing.getState();
    if (['waiting', 'active', 'delayed'].includes(state)) {
      return existing; // Job already queued
    }
  }

  return this.queue.add(
    'process-document',
    { documentId },
    { jobId, deduplication: { id: jobId, ttl: 3600000 } }
  );
}
```

## Redis High Availability

### Redis Cluster Configuration

```
┌─────────────────────────────────────────────────────────────┐
│                     Redis Cluster (AWS ElastiCache)          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐                │
│   │ Primary │    │ Primary │    │ Primary │                │
│   │ (Shard1)│    │ (Shard2)│    │ (Shard3)│                │
│   └────┬────┘    └────┬────┘    └────┬────┘                │
│        │              │              │                      │
│   ┌────┴────┐    ┌────┴────┐    ┌────┴────┐                │
│   │ Replica │    │ Replica │    │ Replica │                │
│   └─────────┘    └─────────┘    └─────────┘                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Failover Behavior

| Scenario | Detection | Recovery | Data Loss |
|----------|-----------|----------|-----------|
| Replica failure | Auto (<30s) | Promote standby | None |
| Primary failure | Auto (<30s) | Promote replica | <30s jobs |
| Network partition | Auto | Reconnect | Jobs retry |
| Full cluster failure | Alert | Manual recovery | Recover from AOF |

### BullMQ Failover Configuration

```typescript
const redisConnection = new Redis({
  host: process.env.REDIS_HOST,
  port: 6379,
  maxRetriesPerRequest: 3,
  retryStrategy: (times) => {
    if (times > 10) return null; // Stop retrying
    return Math.min(times * 200, 5000); // Exponential backoff
  },
  reconnectOnError: (err) => {
    return err.message.includes('READONLY'); // Reconnect on failover
  },
});

// Worker with graceful shutdown
const worker = new Worker('queue', processor, {
  connection: redisConnection,
  lockDuration: 60000,     // 60s lock
  stalledInterval: 30000,  // Check stalled every 30s
  maxStalledCount: 2,      // Retry stalled jobs twice
});
```

## Job Latency Requirements

### Maximum Acceptable Latency by Job Type

| Job Type | Queue Latency | Processing Time | End-to-End SLA |
|----------|---------------|-----------------|----------------|
| **Critical (document AI)** | <5s | <60s | <2 min |
| **Standard (notifications)** | <30s | <10s | <1 min |
| **Background (reports)** | <5min | <30min | <1 hour |
| **Scheduled (cleanup)** | N/A | <10min | Window-based |

### Latency Monitoring

```typescript
// Track job latency metrics
@OnQueueCompleted()
async handleCompleted(job: Job) {
  const waitTime = job.processedOn - job.timestamp;
  const processTime = Date.now() - job.processedOn;

  await this.metricsService.recordHistogram('job_wait_time', waitTime, {
    queue: job.queueName,
    jobType: job.name,
  });

  await this.metricsService.recordHistogram('job_process_time', processTime, {
    queue: job.queueName,
    jobType: job.name,
  });

  // Alert if SLA breached
  const sla = this.getSLA(job.queueName);
  if (waitTime + processTime > sla) {
    this.logger.warn('Job SLA breached', {
      jobId: job.id,
      queue: job.queueName,
      totalTime: waitTime + processTime,
      sla,
    });
  }
}
```

---

## References
- [BullMQ Documentation](https://docs.bullmq.io/)
- [NestJS BullMQ Integration](https://docs.nestjs.com/techniques/queues)
- [Bull Board](https://github.com/felixmosh/bull-board)
