# ADR-FN-023: Multi-Tenant User Model

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

The marketplace requires a multi-tenant user model supporting buyer organizations, supplier organizations, and platform administrators with role-based access control.

### Business Context
The platform serves multiple stakeholder types:
- **Buyer organizations**: Shipping companies, fleet managers with procurement teams
- **Supplier organizations**: Chandlers, distributors with sales and fulfillment teams
- **Platform team**: Administrators, operations, support staff

Each organization has multiple users with different roles and permissions. Users may belong to multiple organizations (e.g., consultant serving multiple buyers).

### Technical Context
- PostgreSQL for user and organization data (ADR-NF-001)
- JWT authentication (ADR-NF-015)
- Row-level security for data isolation (ADR-NF-018)
- Integration with supplier onboarding (ADR-FN-014)
- Support for SSO in future

### Assumptions
- Organizations are primary tenants for data isolation
- Users can belong to multiple organizations
- Roles are organization-scoped, not global
- Permissions are role-based, not individual

---

## Decision Drivers

- Clear data isolation between organizations
- Flexible role and permission management
- Support for multiple organization memberships
- Scalable to enterprise customers with complex hierarchies
- Audit trail for access and actions
- Foundation for SSO integration

---

## Considered Options

### Option 1: Flat User-Organization Model
**Description:** Users belong to one organization with global roles.

**Pros:**
- Simple implementation
- Clear ownership
- Easy to understand

**Cons:**
- No multi-organization support
- Inflexible for consultants/agents
- Limited role granularity

### Option 2: Organization-Scoped RBAC
**Description:** Users have memberships in organizations with role assignments per membership.

**Pros:**
- Multi-organization support
- Organization-scoped roles
- Flexible permissions
- Clear isolation

**Cons:**
- More complex queries
- Session management for org context
- UI complexity for multi-org users

### Option 3: Hierarchical Multi-Tenant
**Description:** Organizations form hierarchies (parent/child) with role inheritance.

**Pros:**
- Supports enterprise structures
- Role inheritance
- Delegated administration

**Cons:**
- High complexity
- Overkill for current needs
- Complex permission resolution

---

## Decision

**Chosen Option:** Organization-Scoped RBAC

We will implement a user model where users have memberships in organizations, with roles and permissions scoped to each organization membership.

### Rationale
Organization-scoped RBAC provides the flexibility needed for maritime commerce where users (agents, consultants) often work with multiple organizations while maintaining clear data isolation. This model supports both simple single-organization users and complex multi-organization scenarios.

---

## Consequences

### Positive
- Multi-organization support
- Clear data isolation per organization
- Flexible role management
- Foundation for enterprise features

### Negative
- Session requires organization context
- **Mitigation:** Organization selector, default organization preference
- Queries more complex
- **Mitigation:** Well-designed data access layer

### Risks
- Permission escalation across orgs: Strict role scoping, audit logging
- Confused users with multiple orgs: Clear UI context, organization switcher
- Complex permission resolution: Cache resolved permissions, clear hierarchy

---

## Implementation Notes

### Data Model

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USERS                                       │
│                                                                      │
│  id: uuid                                                            │
│  email: string (unique)                                              │
│  name: string                                                        │
│  phone: string                                                       │
│  avatar_url: string                                                  │
│  status: ACTIVE | SUSPENDED | PENDING                                │
│                                                                      │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            │ 1:N
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ORGANIZATION_MEMBERSHIPS                          │
│                                                                      │
│  user_id: uuid ──────────────────┐                                  │
│  organization_id: uuid ──────────┼───────┐                          │
│  role_id: uuid ──────────────────┼───────┼───────┐                  │
│  status: ACTIVE | INVITED        │       │       │                  │
│  invited_by: uuid                │       │       │                  │
│  joined_at: timestamp            │       │       │                  │
│                                  │       │       │                  │
└──────────────────────────────────┘       │       │                  │
                                           │       │                  │
                            ┌──────────────┘       │                  │
                            │                      │                  │
                            ▼                      ▼                  │
┌─────────────────────────────────────┐  ┌─────────────────────────┐ │
│          ORGANIZATIONS              │  │        ROLES            │ │
│                                     │  │                         │ │
│  id: uuid                           │  │  id: uuid               │ │
│  type: BUYER | SUPPLIER | PLATFORM  │  │  name: string           │◀┘
│  name: string                       │  │  organization_type: enum│
│  legal_name: string                 │  │  permissions: jsonb     │
│  status: ACTIVE | SUSPENDED         │  │  is_system: boolean     │
│                                     │  │                         │
│  buyer_profile / supplier_profile   │  └─────────────────────────┘
│                                     │
└─────────────────────────────────────┘
```

### Database Schema

```sql
-- Users (authentication identity)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),  -- Null for SSO users
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    avatar_url VARCHAR(500),

    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    email_verified BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMPTZ,

    -- Preferences
    default_organization_id UUID,
    locale VARCHAR(10) DEFAULT 'en',
    timezone VARCHAR(50) DEFAULT 'UTC',

    -- Security
    last_login_at TIMESTAMPTZ,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Organizations (tenants)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(20) NOT NULL,  -- BUYER, SUPPLIER, PLATFORM
    name VARCHAR(255) NOT NULL,
    legal_name VARCHAR(255),
    slug VARCHAR(100) UNIQUE,

    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',

    -- Contact
    primary_email VARCHAR(255),
    primary_phone VARCHAR(20),
    website VARCHAR(255),

    -- Address
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(2),

    -- Settings
    settings JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Roles (organization-type scoped)
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    organization_type VARCHAR(20) NOT NULL,  -- Which org type this role applies to
    permissions JSONB NOT NULL DEFAULT '[]',
    is_system BOOLEAN DEFAULT FALSE,  -- System roles can't be deleted

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(name, organization_type)
);

-- Organization memberships
CREATE TABLE organization_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id),

    status VARCHAR(20) NOT NULL DEFAULT 'INVITED',
    invited_by UUID REFERENCES users(id),
    invited_at TIMESTAMPTZ DEFAULT NOW(),
    joined_at TIMESTAMPTZ,

    -- Membership-specific settings
    job_title VARCHAR(100),
    department VARCHAR(100),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, organization_id)
);

-- Row-level security policies
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_memberships ENABLE ROW LEVEL SECURITY;

-- Users can see orgs they belong to
CREATE POLICY org_member_select ON organizations
    FOR SELECT
    USING (
        id IN (
            SELECT organization_id FROM organization_memberships
            WHERE user_id = current_setting('app.current_user_id')::uuid
            AND status = 'ACTIVE'
        )
    );
```

### System Roles

```typescript
// user/constants/system-roles.ts
export const SYSTEM_ROLES = {
  BUYER: [
    {
      name: 'buyer_admin',
      displayName: 'Buyer Admin',
      description: 'Full access to buyer organization',
      permissions: [
        'organization.manage',
        'users.manage',
        'rfq.create', 'rfq.manage',
        'orders.create', 'orders.manage',
        'invoices.view', 'invoices.approve',
        'reports.view'
      ]
    },
    {
      name: 'procurement_manager',
      displayName: 'Procurement Manager',
      description: 'Manage RFQs and orders',
      permissions: [
        'rfq.create', 'rfq.manage',
        'orders.create', 'orders.manage',
        'invoices.view',
        'reports.view'
      ]
    },
    {
      name: 'procurement_officer',
      displayName: 'Procurement Officer',
      description: 'Create RFQs and view orders',
      permissions: [
        'rfq.create', 'rfq.view',
        'orders.view',
        'invoices.view'
      ]
    },
    {
      name: 'viewer',
      displayName: 'Viewer',
      description: 'View-only access',
      permissions: [
        'rfq.view',
        'orders.view',
        'reports.view'
      ]
    }
  ],

  SUPPLIER: [
    {
      name: 'supplier_admin',
      displayName: 'Supplier Admin',
      description: 'Full access to supplier organization',
      permissions: [
        'organization.manage',
        'users.manage',
        'quotes.create', 'quotes.manage',
        'orders.manage', 'orders.fulfill',
        'inventory.manage',
        'finance.view',
        'reports.view'
      ]
    },
    {
      name: 'sales_manager',
      displayName: 'Sales Manager',
      description: 'Manage quotes and customer relations',
      permissions: [
        'quotes.create', 'quotes.manage',
        'orders.view',
        'customers.view',
        'reports.view'
      ]
    },
    {
      name: 'fulfillment_manager',
      displayName: 'Fulfillment Manager',
      description: 'Manage order fulfillment',
      permissions: [
        'orders.view', 'orders.fulfill',
        'inventory.view',
        'shipping.manage'
      ]
    },
    {
      name: 'sales_rep',
      displayName: 'Sales Representative',
      description: 'Create and manage quotes',
      permissions: [
        'quotes.create', 'quotes.view',
        'orders.view'
      ]
    }
  ],

  PLATFORM: [
    {
      name: 'super_admin',
      displayName: 'Super Admin',
      description: 'Full platform access',
      permissions: ['*']
    },
    {
      name: 'operations_admin',
      displayName: 'Operations Admin',
      description: 'Manage platform operations',
      permissions: [
        'organizations.view', 'organizations.manage',
        'users.view', 'users.manage',
        'orders.view',
        'disputes.manage',
        'reports.view'
      ]
    },
    {
      name: 'support_agent',
      displayName: 'Support Agent',
      description: 'Customer support access',
      permissions: [
        'organizations.view',
        'users.view',
        'orders.view',
        'disputes.view', 'disputes.respond'
      ]
    }
  ]
};
```

### User Service

```typescript
// user/services/user.service.ts
@Injectable()
export class UserService {
  constructor(
    private readonly userRepository: UserRepository,
    private readonly membershipRepository: MembershipRepository,
    private readonly roleRepository: RoleRepository,
    private readonly eventEmitter: EventEmitter2
  ) {}

  async createUser(data: CreateUserDto): Promise<User> {
    const user = await this.userRepository.create({
      email: data.email.toLowerCase(),
      name: data.name,
      phone: data.phone,
      status: 'PENDING'
    });

    this.eventEmitter.emit('user.created', { user });

    return user;
  }

  async inviteToOrganization(
    userId: string,
    organizationId: string,
    roleId: string,
    invitedBy: string
  ): Promise<OrganizationMembership> {
    const organization = await this.organizationRepository.findById(organizationId);
    const role = await this.roleRepository.findById(roleId);

    // Validate role is appropriate for organization type
    if (role.organizationType !== organization.type) {
      throw new BadRequestException(
        `Role ${role.name} is not valid for ${organization.type} organizations`
      );
    }

    const membership = await this.membershipRepository.create({
      userId,
      organizationId,
      roleId,
      status: 'INVITED',
      invitedBy,
      invitedAt: new Date()
    });

    this.eventEmitter.emit('membership.invited', {
      membership,
      organization,
      role
    });

    return membership;
  }

  async acceptInvitation(
    userId: string,
    organizationId: string
  ): Promise<OrganizationMembership> {
    const membership = await this.membershipRepository.findByUserAndOrg(
      userId,
      organizationId
    );

    if (!membership || membership.status !== 'INVITED') {
      throw new BadRequestException('No pending invitation found');
    }

    await this.membershipRepository.update(membership.id, {
      status: 'ACTIVE',
      joinedAt: new Date()
    });

    // Set as default org if user has no default
    const user = await this.userRepository.findById(userId);
    if (!user.defaultOrganizationId) {
      await this.userRepository.update(userId, {
        defaultOrganizationId: organizationId
      });
    }

    return this.membershipRepository.findById(membership.id);
  }

  async getUserOrganizations(userId: string): Promise<OrganizationWithRole[]> {
    const memberships = await this.membershipRepository.findByUser(userId);

    return Promise.all(
      memberships
        .filter(m => m.status === 'ACTIVE')
        .map(async (m) => ({
          organization: await this.organizationRepository.findById(m.organizationId),
          role: await this.roleRepository.findById(m.roleId),
          membership: m
        }))
    );
  }

  async checkPermission(
    userId: string,
    organizationId: string,
    permission: string
  ): Promise<boolean> {
    const membership = await this.membershipRepository.findByUserAndOrg(
      userId,
      organizationId
    );

    if (!membership || membership.status !== 'ACTIVE') {
      return false;
    }

    const role = await this.roleRepository.findById(membership.roleId);

    // Check for wildcard permission
    if (role.permissions.includes('*')) {
      return true;
    }

    // Check specific permission
    return role.permissions.includes(permission);
  }
}
```

### Auth Context Service

```typescript
// auth/services/auth-context.service.ts
@Injectable()
export class AuthContextService {
  constructor(
    private readonly userService: UserService,
    private readonly request: Request
  ) {}

  async getCurrentUser(): Promise<User> {
    const userId = this.request['user']?.id;
    if (!userId) throw new UnauthorizedException();

    return this.userService.findById(userId);
  }

  async getCurrentOrganization(): Promise<Organization> {
    const orgId = this.request.headers['x-organization-id'] as string;
    const userId = this.request['user']?.id;

    if (!orgId || !userId) {
      throw new BadRequestException('Organization context required');
    }

    // Verify user has access to organization
    const membership = await this.membershipRepository.findByUserAndOrg(
      userId,
      orgId
    );

    if (!membership || membership.status !== 'ACTIVE') {
      throw new ForbiddenException('Not a member of this organization');
    }

    return this.organizationRepository.findById(orgId);
  }

  async requirePermission(permission: string): Promise<void> {
    const userId = this.request['user']?.id;
    const orgId = this.request.headers['x-organization-id'] as string;

    const hasPermission = await this.userService.checkPermission(
      userId,
      orgId,
      permission
    );

    if (!hasPermission) {
      throw new ForbiddenException(`Missing permission: ${permission}`);
    }
  }
}
```

### Dependencies
- ADR-FN-014: Supplier Onboarding & KYC
- ADR-NF-015: Authentication Strategy
- ADR-NF-018: Multi-Tenant Data Isolation

### Migration Strategy
1. Create user, organization, role tables
2. Seed system roles
3. Implement user registration and invitation
4. Add organization context to JWT
5. Implement permission checking guards
6. Create organization management UI
7. Add row-level security policies

---

## Operational Considerations

### Isolation Model and Access Control Strategy

The platform implements a **Hybrid RBAC/ABAC model** combining role-based permissions with attribute-based policies for fine-grained access control.

#### Isolation Model Specification

| Layer | Isolation Mechanism | Enforcement Point |
|-------|---------------------|-------------------|
| Data | Row-Level Security (RLS) | PostgreSQL |
| API | Organization Context Header | NestJS Guards |
| Session | JWT Claims | Authentication Middleware |
| Cache | Tenant-prefixed Keys | Redis |
| Files | Organization-scoped Buckets | S3 |

#### RBAC Foundation

```typescript
// Core permission structure
interface Permission {
  resource: string;    // e.g., 'rfq', 'order', 'invoice'
  action: string;      // e.g., 'create', 'read', 'update', 'delete', 'approve'
  scope: 'own' | 'team' | 'organization';
}

// Role-to-permission mapping
const ROLE_PERMISSIONS: Record<string, Permission[]> = {
  'procurement_manager': [
    { resource: 'rfq', action: 'create', scope: 'organization' },
    { resource: 'rfq', action: 'approve', scope: 'organization' },
    { resource: 'order', action: 'create', scope: 'organization' },
    { resource: 'invoice', action: 'approve', scope: 'team' }
  ],
  'procurement_officer': [
    { resource: 'rfq', action: 'create', scope: 'own' },
    { resource: 'rfq', action: 'read', scope: 'team' },
    { resource: 'order', action: 'read', scope: 'team' }
  ]
};
```

#### ABAC Extensions for Dynamic Policies

| Attribute Type | Example Attributes | Policy Use Case |
|----------------|-------------------|-----------------|
| User | department, seniority, location | Limit RFQ creation by department budget |
| Resource | amount, status, category | Require approval for orders > $10,000 |
| Environment | time, IP, device | Restrict access outside business hours |
| Context | relationship, history | Allow access to related supplier data |

```typescript
// ABAC policy evaluation
interface ABACPolicy {
  id: string;
  effect: 'allow' | 'deny';
  conditions: PolicyCondition[];
}

const HIGH_VALUE_ORDER_POLICY: ABACPolicy = {
  id: 'require-approval-high-value',
  effect: 'deny',
  conditions: [
    { attribute: 'resource.amount', operator: 'gt', value: 10000 },
    { attribute: 'user.role', operator: 'not_in', value: ['buyer_admin', 'procurement_manager'] }
  ]
};
```

### Audit Logging Specification

| Event Category | Data Captured | Retention | Storage |
|----------------|---------------|-----------|---------|
| Authentication | user_id, ip, device, success/fail, mfa_used | 2 years | TimescaleDB |
| Authorization | user_id, resource, action, decision, policy_id | 2 years | TimescaleDB |
| Data Access | user_id, org_id, table, record_ids, query_type | 1 year | TimescaleDB |
| Data Mutation | user_id, org_id, table, before/after, change_type | 7 years | TimescaleDB + S3 |
| Admin Actions | admin_id, target_user/org, action, justification | 7 years | Immutable S3 |

```sql
-- Audit log table structure
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type VARCHAR(50) NOT NULL,
    user_id UUID REFERENCES users(id),
    organization_id UUID REFERENCES organizations(id),
    resource_type VARCHAR(50),
    resource_id UUID,
    action VARCHAR(50) NOT NULL,
    outcome VARCHAR(20) NOT NULL, -- 'success', 'denied', 'error'
    request_id UUID,
    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}',
    before_state JSONB,
    after_state JSONB
);

-- Hypertable for time-series optimization
SELECT create_hypertable('audit_logs', 'timestamp');

-- Indexes for common queries
CREATE INDEX idx_audit_user ON audit_logs (user_id, timestamp DESC);
CREATE INDEX idx_audit_org ON audit_logs (organization_id, timestamp DESC);
CREATE INDEX idx_audit_resource ON audit_logs (resource_type, resource_id, timestamp DESC);
```

### Cross-Tenant Roles and Permissions

#### Cross-Tenant Role Definitions

| Role | Scope | Use Case | Permissions |
|------|-------|----------|-------------|
| Platform Super Admin | All tenants | Platform operations | Full access, audit bypass logging |
| Platform Support | All tenants (read) | Customer support | Read-only, masked PII |
| Broker Agent | Multiple buyer orgs | Procurement consultant | Delegated buyer permissions per org |
| Supplier Account Manager | Supplier + related buyers | Relationship management | View orders, quotes across relationship |
| Auditor | Assigned tenants | Compliance audit | Read-only, full data access, no masking |

#### Cross-Tenant Permission Model

```typescript
// Cross-tenant role assignment
interface CrossTenantRole {
  userId: string;
  roleId: string;
  scope: CrossTenantScope;
  restrictions: CrossTenantRestriction[];
  validFrom: Date;
  validUntil?: Date;
  approvedBy: string;
  approvalReason: string;
}

type CrossTenantScope =
  | { type: 'all_tenants' }
  | { type: 'tenant_list', organizationIds: string[] }
  | { type: 'tenant_type', types: ('BUYER' | 'SUPPLIER')[] }
  | { type: 'relationship_based', relationshipType: string };

interface CrossTenantRestriction {
  type: 'time_window' | 'ip_whitelist' | 'mfa_required' | 'read_only' | 'pii_masked';
  config: Record<string, any>;
}

// Example: Broker with access to specific buyer organizations
const brokerAssignment: CrossTenantRole = {
  userId: 'broker-user-123',
  roleId: 'broker_agent',
  scope: {
    type: 'tenant_list',
    organizationIds: ['buyer-org-1', 'buyer-org-2', 'buyer-org-3']
  },
  restrictions: [
    { type: 'mfa_required', config: {} },
    { type: 'time_window', config: { startHour: 6, endHour: 22, timezone: 'Asia/Kolkata' } }
  ],
  validFrom: new Date('2025-01-01'),
  validUntil: new Date('2025-12-31'),
  approvedBy: 'platform-admin-456',
  approvalReason: 'Annual broker contract renewal'
};
```

#### Cross-Tenant Access Controls

| Control | Implementation | Audit Requirement |
|---------|---------------|-------------------|
| Explicit Assignment | Database record with approval chain | Log assignment, approver, reason |
| Time-Bounded | ValidFrom/ValidUntil with auto-expiry | Alert on expiry, log renewal |
| Activity Logging | Enhanced logging for cross-tenant access | Separate audit stream |
| Revocation | Immediate effect, cached sessions invalidated | Log revocation with reason |
| Escalation | Require MFA for sensitive operations | Step-up authentication logged |

### Tenant Merger and Split Procedures

#### Tenant Merger Workflow

```typescript
// Merger execution plan
interface TenantMergerPlan {
  sourceOrganizationId: string;
  targetOrganizationId: string;
  mergeStrategy: 'absorb' | 'consolidate';
  dataHandling: {
    users: 'migrate' | 'deactivate' | 'merge_by_email';
    orders: 'reassign' | 'archive';
    documents: 'migrate' | 'link';
    audit_logs: 'preserve_source_ref' | 'migrate';
  };
  conflictResolution: {
    duplicate_users: 'keep_target' | 'keep_source' | 'manual_review';
    role_conflicts: 'elevate' | 'demote' | 'manual_review';
  };
  rollbackWindow: number; // hours
}

// Merger execution steps
const MERGER_STEPS = [
  { step: 1, action: 'create_merger_audit_record', reversible: true },
  { step: 2, action: 'snapshot_source_organization', reversible: true },
  { step: 3, action: 'disable_source_org_logins', reversible: true },
  { step: 4, action: 'migrate_users_with_role_mapping', reversible: true },
  { step: 5, action: 'reassign_orders_and_rfqs', reversible: true },
  { step: 6, action: 'migrate_documents_update_refs', reversible: true },
  { step: 7, action: 'update_supplier_relationships', reversible: true },
  { step: 8, action: 'archive_source_organization', reversible: false },
  { step: 9, action: 'notify_affected_users', reversible: false },
  { step: 10, action: 'complete_merger_audit_record', reversible: false }
];
```

#### Tenant Split Workflow

```typescript
// Split execution plan
interface TenantSplitPlan {
  sourceOrganizationId: string;
  newOrganizations: {
    name: string;
    type: 'BUYER' | 'SUPPLIER';
    userFilter: UserFilterCriteria;
    dataFilter: DataFilterCriteria;
  }[];
  sharedDataHandling: 'copy_to_all' | 'assign_to_primary' | 'manual_assignment';
  historyHandling: 'copy_full' | 'copy_relevant' | 'reference_only';
}

interface UserFilterCriteria {
  departments?: string[];
  roles?: string[];
  userIds?: string[];
  emailDomains?: string[];
}

interface DataFilterCriteria {
  orderDateRange?: { from: Date; to: Date };
  vesselIds?: string[];
  productCategories?: string[];
  supplierIds?: string[];
}

// Split execution with data lineage
const executeSplit = async (plan: TenantSplitPlan): Promise<SplitResult> => {
  // 1. Validate split plan completeness
  // 2. Create new organizations with provisional status
  // 3. Clone shared configuration (roles, settings)
  // 4. Migrate users based on filters
  // 5. Copy/assign historical data with source references
  // 6. Update external relationships (suppliers, integrations)
  // 7. Activate new organizations
  // 8. Archive or update source organization
  // 9. Generate split audit report
};
```

#### Merger/Split Audit Requirements

| Audit Item | Retention | Access |
|------------|-----------|--------|
| Pre-operation snapshot | 7 years | Admin + Legal |
| Operation execution log | 7 years | Admin + Legal |
| Data lineage mapping | Permanent | Admin + Compliance |
| User notification records | 2 years | Admin |
| Rollback records (if any) | 7 years | Admin + Legal |

### Open Questions - Resolved

- **Q:** How will tenant mergers or splits be handled in the model?
  - **A:** Tenant mergers follow an 10-step workflow with rollback capability for the first 7 steps. The process includes user migration with role mapping, data reassignment with audit trail preservation, and document migration with reference updates. Splits use filter-based data partitioning with full lineage tracking. Both operations require Platform Admin approval, generate comprehensive audit trails, and support a configurable rollback window (default 72 hours for mergers). All operations preserve audit log integrity by maintaining source organization references in historical records.

---

## References
- [RBAC Best Practices](https://auth0.com/docs/manage-users/access-control/rbac)
- [Multi-Tenant Architecture](https://docs.microsoft.com/en-us/azure/architecture/guide/multitenant/overview)
- [PostgreSQL Row Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
