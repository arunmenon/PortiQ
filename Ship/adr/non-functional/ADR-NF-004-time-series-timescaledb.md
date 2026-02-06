# ADR-NF-004: Time Series with TimescaleDB

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Data

---

## Context

Future platform capabilities (IoT sensors, vessel tracking, price history) will generate time-series data requiring efficient storage and querying.

### Business Context
Potential time-series use cases:
- **Vessel position tracking**: Historical AIS data for route analysis
- **IoT sensors**: Container temperatures, equipment monitoring
- **Price history**: Historical pricing for trend analysis
- **Audit logs**: Time-based event tracking
- **Performance metrics**: Platform usage analytics

### Technical Context
- PostgreSQL as primary database (ADR-NF-001)
- TimescaleDB is a PostgreSQL extension
- Time-series data has unique access patterns (mostly inserts, range queries)
- Data retention and compression important for cost
- Integration with existing PostgreSQL queries

### Assumptions
- Time-series workloads are not needed for MVP
- IoT integration is Phase 4+ (months 13-18)
- Standard PostgreSQL tables can handle initial audit logging
- Extension can be enabled when needed

---

## Decision Drivers

- Future-proofing for IoT and analytics
- Integration with existing PostgreSQL
- Efficient time-series storage and queries
- Data retention and compression
- Operational simplicity

---

## Considered Options

### Option 1: TimescaleDB Extension
**Description:** PostgreSQL extension optimized for time-series data with hypertables.

**Pros:**
- Native PostgreSQL extension
- Standard SQL queries
- Automatic time partitioning
- Built-in compression
- Continuous aggregates
- No additional infrastructure

**Cons:**
- Extension dependency
- Adds complexity to schema
- Not needed for MVP

### Option 2: InfluxDB
**Description:** Purpose-built time-series database.

**Pros:**
- Optimized for time-series
- High write throughput
- InfluxQL/Flux languages

**Cons:**
- Separate system to manage
- Different query language
- Data synchronization needed
- Additional infrastructure

### Option 3: Amazon Timestream
**Description:** AWS managed time-series service.

**Pros:**
- Fully managed
- Auto-scaling
- Built-in analytics

**Cons:**
- Vendor lock-in
- Separate from PostgreSQL
- Complex integration
- Cost unpredictability

### Option 4: Standard PostgreSQL Tables
**Description:** Use regular PostgreSQL tables with proper indexing.

**Pros:**
- No additional setup
- Familiar patterns
- Works for MVP scale

**Cons:**
- Manual partitioning
- No compression
- Slower at scale
- More maintenance

---

## Decision

**Chosen Option:** TimescaleDB Extension (Deferred Implementation)

We will plan for TimescaleDB as the time-series solution, but defer implementation until time-series workloads materialize (Phase 4+). Standard PostgreSQL tables will handle initial audit logging and simple time-based queries.

### Rationale
TimescaleDB's PostgreSQL integration makes it the natural choice when time-series needs arise. Deferring implementation avoids premature complexity while maintaining a clear upgrade path. The extension can be enabled on existing PostgreSQL without migration.

---

## Consequences

### Positive
- Clean upgrade path when needed
- No premature complexity
- Stays within PostgreSQL ecosystem
- Standard SQL for queries

### Negative
- Not immediately available for time-series
- **Mitigation:** Standard tables handle MVP needs
- Planning required before implementation
- **Mitigation:** Architecture prepared for extension

### Risks
- Underestimating time-series needs: Monitor query patterns, enable earlier if needed
- Schema migration complexity: Design with TimescaleDB compatibility in mind

---

## Implementation Notes

### Future Schema Design (When Implemented)

```sql
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Vessel positions hypertable
CREATE TABLE vessel_positions (
    time        TIMESTAMPTZ NOT NULL,
    vessel_imo  VARCHAR(10) NOT NULL,
    mmsi        VARCHAR(10),
    latitude    DECIMAL(9, 6) NOT NULL,
    longitude   DECIMAL(9, 6) NOT NULL,
    speed       DECIMAL(5, 2),
    course      DECIMAL(5, 2),
    heading     DECIMAL(5, 2),
    status      VARCHAR(20),
    destination VARCHAR(100),
    source      VARCHAR(20)
);

-- Convert to hypertable with automatic partitioning
SELECT create_hypertable('vessel_positions', 'time',
    chunk_time_interval => INTERVAL '1 day'
);

-- Create composite index for common queries
CREATE INDEX idx_vessel_positions_vessel_time
ON vessel_positions (vessel_imo, time DESC);

-- Enable compression after 7 days
ALTER TABLE vessel_positions SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'time DESC',
    timescaledb.compress_segmentby = 'vessel_imo'
);

SELECT add_compression_policy('vessel_positions', INTERVAL '7 days');

-- Data retention: drop chunks older than 1 year
SELECT add_retention_policy('vessel_positions', INTERVAL '1 year');
```

### IoT Sensor Data (Future)

```sql
-- Equipment sensor readings
CREATE TABLE sensor_readings (
    time          TIMESTAMPTZ NOT NULL,
    device_id     UUID NOT NULL,
    vessel_imo    VARCHAR(10) NOT NULL,
    sensor_type   VARCHAR(50) NOT NULL,
    value         DOUBLE PRECISION NOT NULL,
    unit          VARCHAR(20),
    quality       VARCHAR(20)
);

SELECT create_hypertable('sensor_readings', 'time',
    chunk_time_interval => INTERVAL '1 hour'
);

-- Continuous aggregate for hourly stats
CREATE MATERIALIZED VIEW sensor_hourly_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) as bucket,
    device_id,
    sensor_type,
    avg(value) as avg_value,
    min(value) as min_value,
    max(value) as max_value,
    count(*) as sample_count
FROM sensor_readings
GROUP BY bucket, device_id, sensor_type
WITH NO DATA;

-- Refresh policy
SELECT add_continuous_aggregate_policy('sensor_hourly_stats',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);
```

### Price History (Future)

```sql
-- Product price history
CREATE TABLE price_history (
    time          TIMESTAMPTZ NOT NULL,
    product_id    UUID NOT NULL,
    supplier_id   UUID NOT NULL,
    price         DECIMAL(12, 2) NOT NULL,
    currency      VARCHAR(3) NOT NULL,
    price_type    VARCHAR(20)
);

SELECT create_hypertable('price_history', 'time',
    chunk_time_interval => INTERVAL '1 month'
);

-- Query: 30-day price trend
SELECT
    time_bucket('1 day', time) as day,
    product_id,
    avg(price) as avg_price,
    min(price) as min_price,
    max(price) as max_price
FROM price_history
WHERE product_id = $1
  AND time > NOW() - INTERVAL '30 days'
GROUP BY day, product_id
ORDER BY day;
```

### Service Integration (Future)

```typescript
// timeseries/services/vessel-tracking.service.ts
@Injectable()
export class VesselTrackingService {
  constructor(private readonly dataSource: DataSource) {}

  async recordPosition(position: VesselPosition): Promise<void> {
    await this.dataSource.query(`
      INSERT INTO vessel_positions
        (time, vessel_imo, mmsi, latitude, longitude, speed, course, heading, destination, source)
      VALUES
        (NOW(), $1, $2, $3, $4, $5, $6, $7, $8, $9)
    `, [
      position.vesselImo,
      position.mmsi,
      position.latitude,
      position.longitude,
      position.speed,
      position.course,
      position.heading,
      position.destination,
      position.source
    ]);
  }

  async getVesselTrack(
    vesselImo: string,
    startTime: Date,
    endTime: Date
  ): Promise<TrackPoint[]> {
    return this.dataSource.query(`
      SELECT
        time,
        latitude,
        longitude,
        speed,
        course
      FROM vessel_positions
      WHERE vessel_imo = $1
        AND time BETWEEN $2 AND $3
      ORDER BY time
    `, [vesselImo, startTime, endTime]);
  }

  async getVesselStats(
    vesselImo: string,
    days: number
  ): Promise<VesselStats> {
    const result = await this.dataSource.query(`
      SELECT
        COUNT(*) as position_count,
        AVG(speed) as avg_speed,
        MAX(speed) as max_speed,
        COUNT(DISTINCT DATE(time)) as days_tracked
      FROM vessel_positions
      WHERE vessel_imo = $1
        AND time > NOW() - INTERVAL '${days} days'
    `, [vesselImo]);

    return result[0];
  }
}
```

### MVP Interim Solution

```sql
-- Simple audit log (MVP, before TimescaleDB)
CREATE TABLE audit_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id     UUID,
    org_id      UUID,
    action      VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id   UUID,
    old_value   JSONB,
    new_value   JSONB,
    ip_address  INET,
    user_agent  TEXT
);

CREATE INDEX idx_audit_log_timestamp ON audit_log (timestamp DESC);
CREATE INDEX idx_audit_log_entity ON audit_log (entity_type, entity_id);

-- Partition by month (manual for MVP)
-- Can migrate to TimescaleDB hypertable later
```

### Dependencies
- ADR-NF-001: PostgreSQL as Unified Data Store
- ADR-FN-019: AIS Data Integration (future)

### Migration Strategy (When Implementing)
1. Enable TimescaleDB extension
2. Create hypertables for new time-series data
3. Migrate existing time-series data to hypertables
4. Configure compression policies
5. Set up data retention policies
6. Create continuous aggregates for common queries
7. Update services to use TimescaleDB features

---

## Operational Considerations

### Retention and Compression Policies

| Data Type | Raw Retention | Compressed Retention | Total Retention | Compression Ratio |
|-----------|---------------|---------------------|-----------------|-------------------|
| Vessel Positions (AIS) | 7 days | 90 days | 1 year | ~10:1 |
| IoT Sensor Readings | 24 hours | 30 days | 6 months | ~15:1 |
| Price History | 30 days | 1 year | 7 years | ~8:1 |
| Audit Logs | 90 days | 1 year | 7 years | ~5:1 |
| Platform Metrics | 7 days | 30 days | 1 year | ~12:1 |

**Compression Policy Configuration:**

```sql
-- Vessel positions: compress after 7 days, optimize for vessel_imo queries
ALTER TABLE vessel_positions SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'time DESC',
    timescaledb.compress_segmentby = 'vessel_imo'
);
SELECT add_compression_policy('vessel_positions', INTERVAL '7 days');

-- Sensor readings: compress after 24 hours, segment by device
ALTER TABLE sensor_readings SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'time DESC',
    timescaledb.compress_segmentby = 'device_id, sensor_type'
);
SELECT add_compression_policy('sensor_readings', INTERVAL '1 day');

-- Price history: compress after 30 days, segment by product
ALTER TABLE price_history SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'time DESC',
    timescaledb.compress_segmentby = 'product_id'
);
SELECT add_compression_policy('price_history', INTERVAL '30 days');
```

**Retention Policy Configuration:**

```sql
-- Automatic chunk dropping based on retention periods
SELECT add_retention_policy('vessel_positions', INTERVAL '1 year');
SELECT add_retention_policy('sensor_readings', INTERVAL '6 months');
SELECT add_retention_policy('price_history', INTERVAL '7 years');
SELECT add_retention_policy('platform_metrics', INTERVAL '1 year');
```

### Capacity Planning

**Ingest Rate Projections:**

| Data Type | Phase 1 (MVP) | Phase 2 | Phase 3 | Phase 4 (IoT) |
|-----------|---------------|---------|---------|---------------|
| Vessel Positions | N/A | 100/min | 1,000/min | 5,000/min |
| Sensor Readings | N/A | N/A | N/A | 50,000/min |
| Price Updates | 10/min | 100/min | 500/min | 1,000/min |
| Audit Events | 50/min | 200/min | 500/min | 1,000/min |

**Storage Projections (Monthly, Uncompressed):**

| Data Type | Row Size | Rows/Month | Storage/Month |
|-----------|----------|------------|---------------|
| Vessel Positions | ~200 bytes | 216M | ~43 GB |
| Sensor Readings | ~150 bytes | 2.16B | ~324 GB |
| Price History | ~100 bytes | 43M | ~4 GB |
| Audit Logs | ~500 bytes | 43M | ~21 GB |

**With Compression (at stated ratios):**

| Data Type | Compressed Storage/Month | Annual Storage |
|-----------|-------------------------|----------------|
| Vessel Positions | ~4.3 GB | ~52 GB |
| Sensor Readings | ~22 GB | ~264 GB |
| Price History | ~0.5 GB | ~6 GB |
| Audit Logs | ~4.2 GB | ~50 GB |

**Query Performance Targets:**

| Query Type | Target Latency | Index Strategy |
|------------|----------------|----------------|
| Last known position (single vessel) | < 10ms | BRIN on time, B-tree on vessel_imo |
| Historical track (7 days, single vessel) | < 100ms | Composite (vessel_imo, time DESC) |
| All vessels in region (current) | < 500ms | Spatial index on lat/lon + time filter |
| Price trend (30 days, single product) | < 50ms | Composite (product_id, time DESC) |
| Aggregations (daily/hourly) | < 200ms | Continuous aggregates |

**Infrastructure Sizing:**

| Environment | Instance Type | Storage | Memory | Expected Load |
|-------------|---------------|---------|--------|---------------|
| Development | db.t3.medium | 100 GB | 4 GB | < 100 writes/min |
| Staging | db.r6g.large | 500 GB | 16 GB | < 1,000 writes/min |
| Production (Phase 1-3) | db.r6g.xlarge | 2 TB | 32 GB | < 10,000 writes/min |
| Production (Phase 4) | db.r6g.2xlarge | 5 TB | 64 GB | < 100,000 writes/min |

### Continuous Aggregates for Common Queries

```sql
-- Hourly vessel statistics
CREATE MATERIALIZED VIEW vessel_hourly_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) as bucket,
    vessel_imo,
    avg(speed) as avg_speed,
    max(speed) as max_speed,
    count(*) as position_count,
    ST_MakeLine(ST_Point(longitude, latitude) ORDER BY time) as track
FROM vessel_positions
GROUP BY bucket, vessel_imo
WITH NO DATA;

SELECT add_continuous_aggregate_policy('vessel_hourly_stats',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);

-- Daily price aggregates
CREATE MATERIALIZED VIEW price_daily_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) as bucket,
    product_id,
    supplier_id,
    avg(price) as avg_price,
    min(price) as min_price,
    max(price) as max_price,
    last(price, time) as closing_price,
    first(price, time) as opening_price
FROM price_history
GROUP BY bucket, product_id, supplier_id
WITH NO DATA;

SELECT add_continuous_aggregate_policy('price_daily_stats',
    start_offset => INTERVAL '2 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day'
);
```

### Open Questions - Answered

- **Q:** Which use cases require Timescale instead of base Postgres?
  - **A:** TimescaleDB is required for the following use cases:
    1. **Vessel Position Tracking (AIS)**: High-frequency position updates (potentially thousands per minute) with time-partitioned queries for route analysis
    2. **IoT Sensor Data**: Container temperature monitoring, equipment telemetry requiring sub-second precision and efficient time-range queries
    3. **Price History Analytics**: Long-term price trend analysis with efficient aggregation over months/years of data
    4. **Audit Logs at Scale**: When audit event volume exceeds 1M events/day, requiring efficient time-based retention

    **Use Standard PostgreSQL for:**
    - Audit logs during MVP (< 100K events/day)
    - Simple event tracking with low volume
    - Data without time-based access patterns

---

## References
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [Hypertables Guide](https://docs.timescale.com/use-timescale/latest/hypertables/)
- [Continuous Aggregates](https://docs.timescale.com/use-timescale/latest/continuous-aggregates/)
- [Compression](https://docs.timescale.com/use-timescale/latest/compression/)
