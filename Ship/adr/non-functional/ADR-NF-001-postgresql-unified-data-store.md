# ADR-NF-001: PostgreSQL as Unified Data Store

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Data

---

## Context

The platform requires a primary database capable of handling transactional workloads, complex queries, JSON documents, vector embeddings, and time-series data.

### Business Context
A B2B maritime procurement platform handles diverse data:
- Transactional data: orders, payments, invoices requiring ACID guarantees
- Catalog data: 50K+ products with complex attributes
- User data: multi-tenant organizations with RBAC
- Analytics: reporting, aggregations, business intelligence
- Search: product matching, semantic similarity

Operational simplicity and cost efficiency favor minimizing database infrastructure while meeting all requirements.

### Technical Context
- NestJS backend (TypeScript/Node.js)
- Need for ACID transactions (financial data)
- Vector search for document AI matching
- Time-series potential for IoT (future)
- Multi-tenant row-level security
- JSON/JSONB for flexible schemas

### Assumptions
- PostgreSQL extensions are mature and production-ready
- Cloud-managed PostgreSQL available (AWS RDS, Aurora)
- Team has PostgreSQL expertise
- Horizontal scaling not required initially

---

## Decision Drivers

- ACID compliance for financial transactions
- Extension ecosystem (pgvector, TimescaleDB)
- Multi-tenant isolation capabilities
- Operational simplicity
- Cost efficiency
- Team expertise

---

## Considered Options

### Option 1: PostgreSQL with Extensions
**Description:** PostgreSQL 16+ as unified database with pgvector, JSONB, and optionally TimescaleDB.

**Pros:**
- Single database to operate
- ACID compliance
- Rich extension ecosystem
- Native JSONB with indexing
- Row-level security for multi-tenancy
- Excellent SQL support
- Strong TypeScript/Node.js support

**Cons:**
- Single point of failure
- Vertical scaling limits
- Not specialized for any workload

### Option 2: Polyglot Persistence
**Description:** PostgreSQL for transactions, MongoDB for documents, Elasticsearch for search, InfluxDB for time-series.

**Pros:**
- Specialized databases per workload
- Potentially better performance per use case
- Horizontal scaling options

**Cons:**
- Operational complexity
- Multiple systems to manage
- Data synchronization overhead
- Higher infrastructure costs
- Distributed transaction complexity

### Option 3: Cloud-Native (DynamoDB + OpenSearch)
**Description:** AWS-native services for managed, scalable infrastructure.

**Pros:**
- Fully managed
- Auto-scaling
- AWS integration

**Cons:**
- Vendor lock-in
- Limited query capabilities
- Higher costs at scale
- No ACID across services

---

## Decision

**Chosen Option:** PostgreSQL 16+ with Extensions

We will use PostgreSQL 16+ as the unified data store, leveraging extensions for specialized capabilities: pgvector for vector search, native JSONB for flexible documents, and optionally TimescaleDB for time-series data.

### Rationale
PostgreSQL's extension ecosystem has matured to handle diverse data types and query patterns effectively. Using a single database dramatically simplifies operations, reduces infrastructure costs, and eliminates distributed transaction complexity. The platform's scale (not hyperscale) doesn't require specialized databases. Row-level security enables clean multi-tenant isolation.

---

## Consequences

### Positive
- Single database simplifies operations
- ACID transactions across all data
- Rich querying with SQL
- Native multi-tenant isolation
- Lower infrastructure costs
- Strong TypeScript ecosystem support

### Negative
- Not optimized for any specific workload
- **Mitigation:** Extensions close the gap; optimize through indexing
- Vertical scaling limits
- **Mitigation:** AWS RDS supports 128 vCPUs, 1TB RAM; read replicas for scale

### Risks
- Performance bottlenecks: Connection pooling, query optimization, caching
- Extension compatibility: Use well-maintained extensions, test upgrades
- Single point of failure: Multi-AZ deployment, automated backups

---

## Implementation Notes

### Version and Extensions

```sql
-- PostgreSQL 16+ for latest features
-- Required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- Encryption functions
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- Trigram similarity (search)
CREATE EXTENSION IF NOT EXISTS "btree_gin";  -- GIN index support

-- Vector search (ADR-NF-002)
CREATE EXTENSION IF NOT EXISTS "vector";     -- pgvector

-- Hierarchical data (ADR-FN-004)
CREATE EXTENSION IF NOT EXISTS "ltree";

-- Time series (ADR-NF-004, optional)
-- CREATE EXTENSION IF NOT EXISTS "timescaledb";
```

### Connection Configuration

```typescript
// database/config/database.config.ts
export const databaseConfig: TypeOrmModuleOptions = {
  type: 'postgres',
  host: process.env.DB_HOST,
  port: parseInt(process.env.DB_PORT, 10) || 5432,
  username: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,

  // Connection pool
  extra: {
    max: 20,              // Max connections per instance
    min: 5,               // Min connections
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 10000
  },

  // SSL for production
  ssl: process.env.NODE_ENV === 'production' ? {
    rejectUnauthorized: true,
    ca: process.env.DB_CA_CERT
  } : false,

  // Logging
  logging: process.env.NODE_ENV === 'development' ? ['query', 'error'] : ['error'],

  // Schema
  schema: 'public',
  synchronize: false,  // Never in production
  migrationsRun: true
};
```

### Row-Level Security Setup

```sql
-- Enable RLS on tenant-scoped tables
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE rfqs ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

-- Create policy for organization isolation
CREATE POLICY org_isolation ON orders
    USING (buyer_org_id = current_setting('app.current_org_id')::uuid
           OR seller_org_id = current_setting('app.current_org_id')::uuid);

-- Set context in application
-- In NestJS middleware:
-- await this.dataSource.query(`SET app.current_org_id = '${orgId}'`);
```

### Indexing Strategy

```sql
-- Primary key indexes (automatic)
-- Foreign key indexes
CREATE INDEX idx_orders_buyer_org ON orders(buyer_org_id);
CREATE INDEX idx_orders_rfq ON orders(rfq_id);
CREATE INDEX idx_rfqs_buyer_org ON rfqs(buyer_org_id);

-- Search indexes
CREATE INDEX idx_products_name_trgm ON products USING GIN(name gin_trgm_ops);
CREATE INDEX idx_products_impa ON products(impa_code);

-- JSONB indexes
CREATE INDEX idx_products_specs ON products USING GIN(specifications);

-- Partial indexes for common queries
CREATE INDEX idx_orders_active ON orders(created_at DESC)
    WHERE status NOT IN ('COMPLETED', 'CANCELLED');

-- Vector index (see ADR-NF-002)
CREATE INDEX idx_products_embedding ON products
    USING hnsw(embedding vector_cosine_ops);
```

### AWS RDS Configuration

```yaml
# terraform/modules/database/main.tf
resource "aws_db_instance" "main" {
  identifier        = "ship-chandlery-prod"
  engine            = "postgres"
  engine_version    = "16.1"
  instance_class    = "db.r6g.xlarge"  # 4 vCPU, 32 GB RAM

  allocated_storage     = 100
  max_allocated_storage = 1000  # Auto-scaling

  multi_az             = true  # High availability
  storage_encrypted    = true
  deletion_protection  = true

  # Backup
  backup_retention_period = 30
  backup_window           = "03:00-04:00"

  # Maintenance
  maintenance_window = "Mon:04:00-Mon:05:00"

  # Performance
  performance_insights_enabled = true
  monitoring_interval          = 60

  # Parameter group with extensions
  parameter_group_name = aws_db_parameter_group.postgres.name
}

resource "aws_db_parameter_group" "postgres" {
  family = "postgres16"
  name   = "ship-chandlery-params"

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements,pgvector"
  }

  parameter {
    name  = "max_connections"
    value = "200"
  }
}
```

### Dependencies
- ADR-NF-002: Vector Search with pgvector
- ADR-NF-004: Time Series with TimescaleDB
- ADR-NF-018: Multi-Tenant Data Isolation

### Migration Strategy
1. Set up PostgreSQL 16 on AWS RDS
2. Enable required extensions
3. Create base schema with migrations
4. Configure connection pooling (PgBouncer if needed)
5. Set up row-level security policies
6. Configure monitoring and alerting
7. Establish backup and recovery procedures

---

## Scaling Strategy

### Scaling Limits and Thresholds

| Metric | Initial Capacity | Scale-Up Trigger | Maximum |
|--------|------------------|------------------|---------|
| Database Size | 100 GB | 500 GB | 1 TB |
| Connections | 200 | 150 concurrent | 400 (with PgBouncer) |
| CPU Utilization | db.r6g.xlarge | >70% sustained | db.r6g.4xlarge |
| IOPS | 3,000 | >80% sustained | 16,000 (io1) |
| Query Latency (p99) | <100ms | >200ms | Investigate |

### Partitioning Strategy

Large tables will use PostgreSQL native partitioning:

```sql
-- Orders partitioned by month (time-based)
CREATE TABLE orders (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    -- other columns
) PARTITION BY RANGE (created_at);

-- Create monthly partitions
CREATE TABLE orders_2025_01 PARTITION OF orders
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- Audit logs partitioned by month with automatic cleanup
CREATE TABLE audit_logs (
    id UUID,
    created_at TIMESTAMPTZ NOT NULL,
    -- other columns
) PARTITION BY RANGE (created_at);
```

**Partition candidates:**
- `orders` - partition by `created_at` (monthly)
- `audit_logs` - partition by `created_at` (monthly, retain 12 months)
- `rfq_events` - partition by `created_at` (monthly)
- `vessel_positions` - partition by `timestamp` (daily, if using TimescaleDB)

### Read Replica Strategy

```
┌─────────────────┐     ┌─────────────────┐
│  Primary (RW)   │────▶│  Replica (RO)   │
│  Transactional  │     │  Analytics/     │
│  Workloads      │     │  Reporting      │
└─────────────────┘     └─────────────────┘
        │                       │
        ▼                       ▼
  API Services            BI Tools
  Order Processing        Dashboards
  Real-time Ops           Exports
```

**Configuration:**
- 1 read replica in same AZ for analytics queries
- Replica lag monitoring with alert at >30 seconds
- Connection routing via application-level read/write splitting

## Workload Isolation

### Transactional vs Analytics Separation

| Workload Type | Connection Pool | Timeout | Replica |
|---------------|-----------------|---------|---------|
| Transactional (API) | 20 connections | 30s | Primary |
| Analytics (Reports) | 10 connections | 300s | Read Replica |
| Background Jobs | 5 connections | 120s | Primary |
| Admin/Migrations | 2 connections | 600s | Primary |

```typescript
// Separate data sources for workload isolation
export const transactionalDataSource = new DataSource({
  // ... config
  extra: { max: 20, statement_timeout: '30000' }
});

export const analyticsDataSource = new DataSource({
  // ... config pointing to read replica
  extra: { max: 10, statement_timeout: '300000' }
});
```

### Query Governance
- `statement_timeout` enforced per connection pool
- Long-running analytics queries routed to replica
- `pg_stat_statements` monitoring for slow query detection
- Query cost limits via `plan_cache_mode` settings

## Evolution Triggers

### Criteria for Adding Secondary Stores

| Trigger | Threshold | Action |
|---------|-----------|--------|
| Full-text search latency | p99 > 500ms at scale | Evaluate Meilisearch (ADR-NF-003) |
| Vector search dataset | >10M embeddings | Consider dedicated vector DB |
| Time-series ingest rate | >10K points/sec | Enable TimescaleDB (ADR-NF-004) |
| Database size | >1 TB | Evaluate table archival or sharding |
| Read replica lag | Sustained >60s | Add additional replicas |

### Criteria for Sharding
Sharding is **not planned** for MVP. Triggers that would force reconsideration:
- Single-tenant data exceeds 100 GB
- Write throughput exceeds 50K TPS
- Multi-region latency requirements emerge

**Preferred alternatives before sharding:**
1. Vertical scaling (larger instance)
2. Read replicas for read scaling
3. Table partitioning for large tables
4. Archival of historical data
5. Caching layer (Redis) for hot data

---

## References
- [PostgreSQL 16 Documentation](https://www.postgresql.org/docs/16/)
- [AWS RDS PostgreSQL](https://aws.amazon.com/rds/postgresql/)
- [PostgreSQL Extension Network](https://pgxn.org/)
- [Row Level Security Guide](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
