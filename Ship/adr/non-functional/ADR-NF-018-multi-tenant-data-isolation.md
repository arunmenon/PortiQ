# ADR-NF-018: Multi-Tenant Data Isolation

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Security

---

## Context

The platform serves multiple organizations (buyers, suppliers) that require strict data isolation to prevent cross-tenant data access.

### Business Context
Multi-tenancy requirements:
- Multiple buyer organizations
- Multiple supplier organizations
- Each organization's data must be isolated
- Some data is shared (product catalog, public RFQs)
- Compliance requirements for data segregation
- Support for organization hierarchies (parent/child)

### Technical Context
- PostgreSQL database (ADR-NF-001)
- NestJS modular monolith (ADR-NF-006)
- JWT authentication with organization context (ADR-NF-015)
- Single database deployment (shared schema)
- Potential for high tenant count (1000+)

### Assumptions
- Shared database with row-level isolation (not schema per tenant)
- Organization ID present in JWT claims
- All queries must be tenant-scoped
- Performance acceptable with RLS
- Admin access bypasses tenant isolation

---

## Decision Drivers

- Data security and isolation
- Compliance requirements
- Development simplicity
- Query performance
- Scalability
- Audit capability

---

## Considered Options

### Option 1: Application-Level Tenant Filtering
**Description:** Filter queries in application code using organization ID.

**Pros:**
- Full control in application
- No database-specific features
- Easy to understand
- Flexible exceptions

**Cons:**
- Risk of missing filters
- Relies on developer discipline
- Hard to audit
- Security through obscurity

### Option 2: PostgreSQL Row-Level Security (RLS)
**Description:** Database-enforced tenant isolation using RLS policies.

**Pros:**
- Database-enforced security
- Cannot be bypassed by application bugs
- Centralized policy definition
- Works with all queries
- Audit-friendly

**Cons:**
- PostgreSQL-specific
- Requires session context setup
- Slight performance overhead
- Complex policy definitions

### Option 3: Schema-Per-Tenant
**Description:** Separate PostgreSQL schema for each tenant.

**Pros:**
- Complete isolation
- Easy to backup/restore per tenant
- Clear physical separation

**Cons:**
- Doesn't scale to many tenants
- Migration complexity
- Cross-tenant queries difficult
- Schema management overhead

### Option 4: Separate Databases
**Description:** Each tenant gets own database instance.

**Pros:**
- Maximum isolation
- Independent scaling
- Complete data separation

**Cons:**
- High operational overhead
- Very expensive
- Complex deployment
- Connection management

---

## Decision

**Chosen Option:** PostgreSQL Row-Level Security (RLS) + Application-Level Filtering

We will use PostgreSQL RLS as the primary isolation mechanism with application-level filtering as defense in depth. All tenant-scoped tables will have RLS policies enforced by setting session context.

### Rationale
RLS provides database-enforced security that cannot be bypassed by application bugs. Combined with application-level filtering, this creates defense in depth. The shared schema approach scales well to thousands of tenants while maintaining query simplicity.

---

## Consequences

### Positive
- Database-enforced isolation
- Defense in depth
- Centralized security policies
- Audit-friendly
- Cannot bypass with SQL injection

### Negative
- PostgreSQL-specific
- **Mitigation:** Abstract in repository layer
- Session context setup required
- **Mitigation:** Middleware handles automatically
- Policy complexity
- **Mitigation:** Standard policy templates

### Risks
- Misconfigured policies: Automated testing, regular audits
- Performance degradation: Index optimization, query analysis
- Bypass for admin: Controlled superuser access, audit logging

---

## Implementation Notes

### Database Schema

```sql
-- migrations/001_tenant_isolation.sql

-- Ensure organization_id is never null on tenant-scoped tables
-- Standard columns for all tenant-scoped tables
CREATE OR REPLACE FUNCTION set_organization_id()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.organization_id IS NULL THEN
    NEW.organization_id := current_setting('app.current_organization_id', true);
  END IF;

  IF NEW.organization_id IS NULL THEN
    RAISE EXCEPTION 'organization_id cannot be null';
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Enable RLS on tenant-scoped tables
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE rfqs ENABLE ROW LEVEL SECURITY;
ALTER TABLE quotes ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_users ENABLE ROW LEVEL SECURITY;

-- Force RLS even for table owners
ALTER TABLE orders FORCE ROW LEVEL SECURITY;
ALTER TABLE rfqs FORCE ROW LEVEL SECURITY;
ALTER TABLE quotes FORCE ROW LEVEL SECURITY;
ALTER TABLE documents FORCE ROW LEVEL SECURITY;
ALTER TABLE invoices FORCE ROW LEVEL SECURITY;
```

### RLS Policies

```sql
-- migrations/002_rls_policies.sql

-- Orders: Access for buyer or supplier
CREATE POLICY orders_isolation ON orders
  USING (
    organization_id = current_setting('app.current_organization_id', true)::uuid
    OR
    supplier_id = current_setting('app.current_organization_id', true)::uuid
  );

-- RFQs: Buyers see their own, suppliers see if invited
CREATE POLICY rfqs_isolation ON rfqs
  USING (
    -- Buyer org can see their own RFQs
    buyer_organization_id = current_setting('app.current_organization_id', true)::uuid
    OR
    -- Suppliers can see RFQs they're invited to
    (
      status IN ('PUBLISHED', 'BIDDING', 'AWARDED', 'COMPLETED')
      AND EXISTS (
        SELECT 1 FROM rfq_invitations ri
        WHERE ri.rfq_id = rfqs.id
        AND ri.supplier_id = current_setting('app.current_organization_id', true)::uuid
      )
    )
    OR
    -- Public RFQs visible to all suppliers
    (
      visibility = 'PUBLIC'
      AND status IN ('PUBLISHED', 'BIDDING')
      AND current_setting('app.current_organization_type', true) = 'SUPPLIER'
    )
  );

-- Quotes: Supplier sees own, buyer sees quotes for their RFQs
CREATE POLICY quotes_isolation ON quotes
  USING (
    -- Supplier sees their own quotes
    supplier_id = current_setting('app.current_organization_id', true)::uuid
    OR
    -- Buyer sees quotes on their RFQs
    EXISTS (
      SELECT 1 FROM rfqs r
      WHERE r.id = quotes.rfq_id
      AND r.buyer_organization_id = current_setting('app.current_organization_id', true)::uuid
    )
  );

-- Documents: Organization-owned documents
CREATE POLICY documents_isolation ON documents
  USING (
    organization_id = current_setting('app.current_organization_id', true)::uuid
  );

-- Separate INSERT policies (may differ from SELECT)
CREATE POLICY orders_insert ON orders
  FOR INSERT
  WITH CHECK (
    organization_id = current_setting('app.current_organization_id', true)::uuid
  );

CREATE POLICY documents_insert ON documents
  FOR INSERT
  WITH CHECK (
    organization_id = current_setting('app.current_organization_id', true)::uuid
  );
```

### Tenant Context Middleware

```typescript
// tenancy/middleware/tenant-context.middleware.ts
import { Injectable, NestMiddleware } from '@nestjs/common';
import { DataSource } from 'typeorm';

@Injectable()
export class TenantContextMiddleware implements NestMiddleware {
  constructor(private readonly dataSource: DataSource) {}

  async use(req: Request, res: Response, next: NextFunction) {
    const user = req['user'];

    if (user?.organizationId) {
      // Set PostgreSQL session variables for RLS
      await this.dataSource.query(
        `SELECT set_config('app.current_organization_id', $1, true)`,
        [user.organizationId]
      );

      await this.dataSource.query(
        `SELECT set_config('app.current_organization_type', $1, true)`,
        [user.organizationType]
      );

      await this.dataSource.query(
        `SELECT set_config('app.current_user_id', $1, true)`,
        [user.id]
      );
    }

    next();
  }
}
```

### Repository with Tenant Scope

```typescript
// tenancy/repositories/tenant-scoped.repository.ts
import { Repository, SelectQueryBuilder } from 'typeorm';

export abstract class TenantScopedRepository<T> extends Repository<T> {
  protected organizationId: string;

  setOrganizationContext(organizationId: string): this {
    this.organizationId = organizationId;
    return this;
  }

  createQueryBuilder(alias?: string): SelectQueryBuilder<T> {
    const qb = super.createQueryBuilder(alias);

    // Add organization filter (defense in depth - RLS is primary)
    if (this.organizationId && this.hasOrganizationColumn()) {
      qb.andWhere(`${alias}.organization_id = :orgId`, {
        orgId: this.organizationId,
      });
    }

    return qb;
  }

  private hasOrganizationColumn(): boolean {
    const metadata = this.metadata;
    return metadata.columns.some(col => col.propertyName === 'organizationId');
  }
}

// Example usage
@Injectable()
export class OrdersRepository extends TenantScopedRepository<Order> {
  async findByStatus(status: OrderStatus): Promise<Order[]> {
    return this.createQueryBuilder('order')
      .where('order.status = :status', { status })
      .orderBy('order.createdAt', 'DESC')
      .getMany();
    // RLS automatically filters by organization
    // Application filter adds defense in depth
  }
}
```

### Tenant Interceptor

```typescript
// tenancy/interceptors/tenant.interceptor.ts
import { Injectable, NestInterceptor, ExecutionContext, CallHandler } from '@nestjs/common';
import { Observable } from 'rxjs';
import { DataSource } from 'typeorm';

@Injectable()
export class TenantInterceptor implements NestInterceptor {
  constructor(private readonly dataSource: DataSource) {}

  async intercept(
    context: ExecutionContext,
    next: CallHandler,
  ): Promise<Observable<any>> {
    const request = context.switchToHttp().getRequest();
    const user = request.user;

    if (user?.organizationId) {
      // Use transaction to ensure session variables are set
      const queryRunner = this.dataSource.createQueryRunner();
      await queryRunner.connect();

      try {
        await queryRunner.query(
          `SELECT set_config('app.current_organization_id', $1, false)`,
          [user.organizationId]
        );
        await queryRunner.query(
          `SELECT set_config('app.current_organization_type', $1, false)`,
          [user.organizationType]
        );

        // Store query runner in request for use in services
        request.queryRunner = queryRunner;

        return next.handle();
      } finally {
        await queryRunner.release();
      }
    }

    return next.handle();
  }
}
```

### Admin Bypass (Controlled)

```typescript
// tenancy/services/admin-context.service.ts
@Injectable()
export class AdminContextService {
  constructor(private readonly dataSource: DataSource) {}

  async runWithoutRLS<T>(
    operation: () => Promise<T>,
    auditContext: AuditContext
  ): Promise<T> {
    // Log admin bypass
    await this.auditService.logAdminBypass(auditContext);

    const queryRunner = this.dataSource.createQueryRunner();
    await queryRunner.connect();

    try {
      // Set admin mode
      await queryRunner.query(
        `SET LOCAL app.admin_bypass = 'true'`
      );

      return await operation();
    } finally {
      await queryRunner.release();
    }
  }
}

-- SQL: Policy that allows admin bypass
CREATE POLICY orders_admin_bypass ON orders
  USING (
    current_setting('app.admin_bypass', true) = 'true'
    OR organization_id = current_setting('app.current_organization_id', true)::uuid
  );
```

### Cross-Tenant Queries (Controlled)

```typescript
// tenancy/decorators/cross-tenant.decorator.ts
import { SetMetadata } from '@nestjs/common';

export const CROSS_TENANT_KEY = 'cross_tenant';

/**
 * Allows service method to query across tenants.
 * Requires explicit justification and audit logging.
 */
export const CrossTenant = (reason: string) =>
  SetMetadata(CROSS_TENANT_KEY, reason);

// Usage
@Injectable()
export class AnalyticsService {
  @CrossTenant('Platform-wide analytics aggregation')
  async getPlatformStats(): Promise<PlatformStats> {
    // This method can query across all tenants
    // Context: runs with admin privileges, fully audited
  }
}
```

### Tenant-Aware Caching

```typescript
// tenancy/services/tenant-cache.service.ts
@Injectable()
export class TenantCacheService {
  constructor(
    @Inject('REDIS_CLIENT')
    private readonly redis: Redis,
  ) {}

  private buildKey(organizationId: string, key: string): string {
    return `tenant:${organizationId}:${key}`;
  }

  async get<T>(organizationId: string, key: string): Promise<T | null> {
    const value = await this.redis.get(this.buildKey(organizationId, key));
    return value ? JSON.parse(value) : null;
  }

  async set(
    organizationId: string,
    key: string,
    value: any,
    ttl?: number
  ): Promise<void> {
    const fullKey = this.buildKey(organizationId, key);

    if (ttl) {
      await this.redis.setex(fullKey, ttl, JSON.stringify(value));
    } else {
      await this.redis.set(fullKey, JSON.stringify(value));
    }
  }

  async invalidateForTenant(organizationId: string): Promise<void> {
    const pattern = `tenant:${organizationId}:*`;
    const keys = await this.redis.keys(pattern);

    if (keys.length > 0) {
      await this.redis.del(...keys);
    }
  }
}
```

### Testing Tenant Isolation

```typescript
// tenancy/tests/tenant-isolation.spec.ts
describe('Tenant Isolation', () => {
  let dataSource: DataSource;
  let org1Id: string;
  let org2Id: string;

  beforeEach(async () => {
    // Create two test organizations
    org1Id = await createTestOrganization('Org 1');
    org2Id = await createTestOrganization('Org 2');
  });

  it('should prevent cross-tenant data access', async () => {
    // Create order for org1
    await setTenantContext(org1Id);
    const order = await ordersRepository.save({
      organizationId: org1Id,
      // ... order data
    });

    // Try to access from org2 context
    await setTenantContext(org2Id);
    const foundOrder = await ordersRepository.findOne({
      where: { id: order.id },
    });

    expect(foundOrder).toBeNull();
  });

  it('should allow same-tenant data access', async () => {
    await setTenantContext(org1Id);
    const order = await ordersRepository.save({
      organizationId: org1Id,
      // ... order data
    });

    // Access from same org context
    const foundOrder = await ordersRepository.findOne({
      where: { id: order.id },
    });

    expect(foundOrder).not.toBeNull();
    expect(foundOrder.id).toBe(order.id);
  });

  it('should prevent SQL injection bypass of RLS', async () => {
    await setTenantContext(org1Id);
    const order = await ordersRepository.save({
      organizationId: org1Id,
    });

    // Try SQL injection
    await setTenantContext(org2Id);
    const result = await dataSource.query(
      `SELECT * FROM orders WHERE id = $1 OR 1=1`,
      [order.id]
    );

    // Should still be filtered by RLS
    expect(result.length).toBe(0);
  });
});
```

### Audit Logging

```typescript
// tenancy/subscribers/tenant-audit.subscriber.ts
@EventSubscriber()
export class TenantAuditSubscriber implements EntitySubscriberInterface {
  afterLoad(entity: any) {
    // Log cross-tenant access attempts
    if (entity.organizationId) {
      const currentOrg = getCurrentOrganizationId();
      if (currentOrg && entity.organizationId !== currentOrg) {
        logger.warn('Potential cross-tenant access', {
          entityType: entity.constructor.name,
          entityId: entity.id,
          entityOrg: entity.organizationId,
          requestOrg: currentOrg,
        });
      }
    }
  }
}
```

### Dependencies
- ADR-NF-001: PostgreSQL as Unified Data Store
- ADR-NF-015: Authentication Strategy
- ADR-FN-023: Multi-Tenant User Model

### Migration Strategy
1. Add organization_id to all tenant-scoped tables
2. Create RLS policies for each table
3. Implement tenant context middleware
4. Add application-level filtering (defense in depth)
5. Create comprehensive test suite
6. Audit existing data for proper tenant assignment
7. Enable RLS on production
8. Monitor for policy violations

---

## Operational Considerations

### Isolation Model Specification

The platform uses **Row-Level Security (RLS)** as the primary isolation mechanism with the following layered controls.

#### Isolation Architecture Summary

| Aspect | Model | Rationale |
|--------|-------|-----------|
| Database | Shared database, shared schema | Operational simplicity, cost efficiency for 1000+ tenants |
| Data Isolation | Row-Level Security (RLS) | Database-enforced, cannot be bypassed by application bugs |
| Application Layer | Defense-in-depth filtering | Additional safety layer in repository pattern |
| Cache | Tenant-prefixed keys | Prevent cache pollution across tenants |
| Files | Tenant-scoped S3 prefixes | Logical separation with IAM policies |
| Search Index | Tenant-filtered queries | Meilisearch with mandatory tenant filter |

#### RLS Policy Categories

| Table Category | Policy Type | Example Tables |
|----------------|-------------|----------------|
| Tenant-Owned | Single organization match | orders, rfqs, documents, invoices |
| Relationship-Based | Owner OR counterparty | quotes (supplier sees own, buyer sees for their RFQ) |
| Shared Reference | No RLS, public data | products, ports, impa_codes |
| Platform-Only | Admin role check | audit_logs, system_config |

#### Operational Controls Matrix

| Control | Implementation | Monitoring |
|---------|---------------|------------|
| RLS Policy Enforcement | `ALTER TABLE ... FORCE ROW LEVEL SECURITY` | Policy violation alerts |
| Session Context | `set_config('app.current_organization_id', ...)` | Missing context errors |
| Application Filtering | Repository base class with org filter | Query plan analysis |
| Admin Bypass | Explicit `app.admin_bypass` flag | Separate audit stream |
| Cross-Tenant Queries | `@CrossTenant` decorator with justification | Required audit logging |

### Tenant Data Export Workflow

#### Export Request Process

```typescript
// Data export request structure
interface TenantDataExportRequest {
  organizationId: string;
  requestedBy: string;
  requestType: 'full_export' | 'gdpr_request' | 'legal_discovery' | 'migration';
  scope: ExportScope;
  format: 'json' | 'csv' | 'parquet';
  encryption: {
    enabled: boolean;
    publicKey?: string; // For client-side encryption
  };
  deliveryMethod: 'download_link' | 's3_transfer' | 'sftp';
  retention: number; // Hours to retain export file
}

interface ExportScope {
  tables: 'all' | string[];
  dateRange?: { from: Date; to: Date };
  includeAuditLogs: boolean;
  includeDocuments: boolean;
  anonymizeUsers: boolean;
}
```

#### Export Execution Steps

| Step | Action | SLA | Verification |
|------|--------|-----|--------------|
| 1 | Validate request authorization | Immediate | Role check + MFA |
| 2 | Create export job record | Immediate | Job ID assigned |
| 3 | Generate export manifest | 5 min | Table list, row counts |
| 4 | Extract data per table | Varies by size | Checksum per table |
| 5 | Package with metadata | 10 min | Manifest included |
| 6 | Encrypt if requested | 5 min | Encryption verified |
| 7 | Upload to secure location | 10 min | Upload confirmed |
| 8 | Generate access credentials | Immediate | Time-limited URL/creds |
| 9 | Notify requester | Immediate | Email + in-app |
| 10 | Schedule cleanup | Per retention | Auto-delete job |

#### Export Data Categories

| Category | Tables Included | Special Handling |
|----------|-----------------|------------------|
| Core Business | organizations, users, memberships | Hash passwords, mask tokens |
| Transactions | orders, rfqs, quotes, invoices | Include line items |
| Documents | documents, supplier_documents | Include S3 file references |
| Communication | notifications, messages | Mask external emails |
| Audit | audit_logs | Full export, no masking |
| Analytics | aggregated_metrics | Pre-computed only |

### Tenant Data Deletion Workflow

#### Deletion Request Types

| Type | Trigger | Scope | Retention Override |
|------|---------|-------|-------------------|
| Account Closure | Customer request | Full tenant deletion | Legal retention applies |
| GDPR Right to Erasure | Data subject request | Individual user data | 30-day verification period |
| Data Retention Expiry | Automated policy | Aged data per category | None |
| Legal Hold Release | Legal team approval | Held data deletion | Requires explicit release |

#### Deletion Process for Full Tenant

```typescript
// Tenant deletion execution plan
interface TenantDeletionPlan {
  organizationId: string;
  requestedBy: string;
  approvedBy: string; // Requires Platform Admin
  reason: string;
  deletionType: 'soft_delete' | 'hard_delete' | 'anonymize';
  retentionOverrides: {
    auditLogs: number; // Days to retain (regulatory minimum)
    financialRecords: number; // Days (tax compliance)
    legalHolds: string[]; // Hold IDs that block deletion
  };
  preDeleteActions: PreDeleteAction[];
  postDeleteActions: PostDeleteAction[];
}

type PreDeleteAction =
  | { type: 'export_backup', destination: string }
  | { type: 'notify_users', template: string }
  | { type: 'terminate_integrations' }
  | { type: 'revoke_api_keys' }
  | { type: 'cancel_pending_orders' };

type PostDeleteAction =
  | { type: 'notify_counterparties' }
  | { type: 'update_search_index' }
  | { type: 'invalidate_caches' }
  | { type: 'archive_audit_summary' };
```

#### Deletion Execution Sequence

| Phase | Step | Action | Reversible |
|-------|------|--------|------------|
| Pre-Delete | 1 | Verify no active legal holds | N/A |
| Pre-Delete | 2 | Export full backup to cold storage | N/A |
| Pre-Delete | 3 | Notify all users (14-day warning) | Yes |
| Pre-Delete | 4 | Disable new transactions | Yes |
| Pre-Delete | 5 | Cancel pending orders, refund as needed | Partial |
| Pre-Delete | 6 | Revoke all API keys and sessions | Yes |
| Execute | 7 | Soft-delete user records | Yes (30 days) |
| Execute | 8 | Anonymize PII in audit logs | No |
| Execute | 9 | Delete documents from S3 | No |
| Execute | 10 | Delete database records (cascade) | No |
| Execute | 11 | Update search indices | N/A |
| Execute | 12 | Invalidate all caches | N/A |
| Post-Delete | 13 | Archive deletion audit record | N/A |
| Post-Delete | 14 | Notify counterparty suppliers | N/A |

#### Data Retention by Category

| Data Category | Active Retention | Archive Retention | Deletion Method |
|---------------|------------------|-------------------|-----------------|
| User profiles | Account lifetime | 30 days post-close | Hard delete |
| Transaction data | 7 years | +3 years archived | Anonymize then delete |
| Audit logs | 2 years online | 5 years cold storage | Archive then delete |
| Documents | Account lifetime | 90 days post-close | Hard delete |
| Financial records | 7 years (tax) | +3 years archived | Anonymize then delete |
| Communication logs | 1 year | None | Hard delete |

### Tenant Isolation Testing and Validation

#### Automated Test Suite

```typescript
// Isolation test categories
describe('Tenant Isolation Tests', () => {
  describe('RLS Policy Tests', () => {
    it('should prevent cross-tenant SELECT', async () => {
      // Create data for org1
      await setTenantContext(org1Id);
      const order = await createOrder({ amount: 1000 });

      // Attempt access from org2
      await setTenantContext(org2Id);
      const result = await orderRepository.findOne({ where: { id: order.id } });

      expect(result).toBeNull();
    });

    it('should prevent cross-tenant UPDATE', async () => {
      await setTenantContext(org1Id);
      const order = await createOrder({ amount: 1000 });

      await setTenantContext(org2Id);
      await expect(
        orderRepository.update(order.id, { amount: 2000 })
      ).rejects.toThrow();
    });

    it('should prevent cross-tenant DELETE', async () => {
      await setTenantContext(org1Id);
      const order = await createOrder({ amount: 1000 });

      await setTenantContext(org2Id);
      await expect(
        orderRepository.delete(order.id)
      ).rejects.toThrow();
    });

    it('should block SQL injection bypass attempts', async () => {
      await setTenantContext(org1Id);
      const order = await createOrder({ amount: 1000 });

      await setTenantContext(org2Id);
      // Direct SQL with injection attempt
      const result = await dataSource.query(
        `SELECT * FROM orders WHERE id = $1 OR '1'='1'`,
        [order.id]
      );

      // RLS should still filter
      expect(result.length).toBe(0);
    });
  });

  describe('Application Layer Tests', () => {
    it('should require organization context for tenant APIs', async () => {
      const response = await request(app)
        .get('/api/orders')
        .set('Authorization', `Bearer ${validToken}`)
        // Missing X-Organization-Id header
        .expect(400);

      expect(response.body.message).toContain('Organization context required');
    });

    it('should reject invalid organization context', async () => {
      const response = await request(app)
        .get('/api/orders')
        .set('Authorization', `Bearer ${validToken}`)
        .set('X-Organization-Id', 'non-member-org-id')
        .expect(403);
    });
  });

  describe('Cache Isolation Tests', () => {
    it('should isolate cached data by tenant', async () => {
      await setTenantContext(org1Id);
      await cacheService.set('user_prefs', { theme: 'dark' });

      await setTenantContext(org2Id);
      const result = await cacheService.get('user_prefs');

      expect(result).toBeNull();
    });
  });
});
```

#### Audit and Compliance Validation

| Validation Type | Frequency | Method | Evidence |
|-----------------|-----------|--------|----------|
| RLS Policy Coverage | Daily (CI) | Automated test suite | Test reports |
| Cross-Tenant Query Detection | Real-time | Query log analysis | Alert logs |
| Missing Org Context | Real-time | Middleware monitoring | Error metrics |
| Admin Bypass Usage | Real-time | Audit log analysis | Bypass reports |
| Data Leak Scanning | Weekly | Automated scripts | Scan reports |

#### Penetration Testing Protocol

| Test Category | Scope | Frequency | Performed By |
|---------------|-------|-----------|--------------|
| RLS Bypass Attempts | All tenant tables | Quarterly | External security firm |
| Session Hijacking | Auth + context | Quarterly | External security firm |
| API Fuzzing | All endpoints | Monthly | Automated + manual |
| Privilege Escalation | Cross-tenant roles | Quarterly | External security firm |

#### Compliance Audit Artifacts

```typescript
// Audit report generation
interface IsolationAuditReport {
  reportId: string;
  generatedAt: Date;
  period: { from: Date; to: Date };
  sections: {
    rlsPolicyCoverage: {
      tablesWithRls: string[];
      tablesWithoutRls: string[];
      policyCompleteness: number; // percentage
    };
    crossTenantAttempts: {
      blockedByRls: number;
      blockedByApplication: number;
      adminBypasses: AdminBypassRecord[];
    };
    testResults: {
      automated: TestSuiteResult;
      penetration: PenTestResult;
    };
    incidents: SecurityIncident[];
    recommendations: string[];
  };
}

// Generate monthly compliance report
async function generateIsolationAuditReport(period: DateRange): Promise<IsolationAuditReport> {
  return {
    reportId: generateUUID(),
    generatedAt: new Date(),
    period,
    sections: {
      rlsPolicyCoverage: await analyzeRlsCoverage(),
      crossTenantAttempts: await analyzeCrossTenantAttempts(period),
      testResults: await getTestResults(period),
      incidents: await getSecurityIncidents(period),
      recommendations: await generateRecommendations()
    }
  };
}
```

### Open Questions - Resolved

- **Q:** How will isolation be validated in tests and audits?
  - **A:** Isolation validation uses a multi-layered approach:
    1. **Automated CI Tests**: Comprehensive test suite runs on every deployment covering RLS policies, application-layer filtering, and cache isolation. Tests include positive cases (same-tenant access), negative cases (cross-tenant blocked), and injection bypass attempts.
    2. **Real-time Monitoring**: Query logs are analyzed for cross-tenant access patterns. Missing organization context triggers immediate alerts. Admin bypass usage is logged to a separate audit stream with mandatory justification.
    3. **Periodic Audits**: Weekly automated scans check for data that might have leaked across tenants. Monthly API fuzzing tests boundary conditions. Quarterly external penetration tests focus specifically on tenant isolation bypass attempts.
    4. **Compliance Reporting**: Monthly audit reports document RLS coverage, blocked attempts, admin bypass usage, and any security incidents. These reports are retained for 7 years and available for regulatory review.

---

## References
- [PostgreSQL Row Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Multi-Tenant Data Architecture](https://docs.microsoft.com/en-us/azure/sql-database/saas-tenancy-app-design-patterns)
- [Defense in Depth](https://en.wikipedia.org/wiki/Defense_in_depth_(computing))
