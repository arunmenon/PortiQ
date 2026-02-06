# ADR-FN-005: Catalog Extensibility (JSONB)

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Data

---

## Context

The platform's product catalog must accommodate highly variable attributes across 35 IMPA categories, from provisions (nutritional info, expiry) to technical equipment (specifications, certifications, compatibility matrices).

### Business Context
Maritime product attributes vary dramatically by category:
- Provisions: nutritional information, allergens, shelf life, storage requirements
- Paints: color codes, coverage rates, VOC content, application methods
- Safety equipment: certifications (SOLAS, MED), inspection intervals, capacity ratings
- Engine parts: dimensions, materials, pressure ratings, compatibility lists
- Tools: power requirements, torque specifications, accessory compatibility

A rigid schema cannot efficiently accommodate this diversity while maintaining queryability.

### Technical Context
- PostgreSQL 16+ with native JSONB support (ADR-NF-001)
- GIN indexing for JSONB enables efficient queries
- JSON Schema validation available at application layer
- Category-specific attribute schemas defined (ADR-FN-004)
- Need to support faceted filtering in Meilisearch

### Assumptions
- Attribute requirements will evolve as new product types are added
- Most queries filter on a subset of common attributes
- Full-text search within JSONB attributes is occasionally needed
- Category-specific validation rules can be maintained

---

## Decision Drivers

- Schema flexibility for diverse product categories
- Query performance for filtering and faceting
- Validation capabilities for data quality
- Evolution without schema migrations
- Integration with search systems
- Developer experience and maintainability

---

## Considered Options

### Option 1: Entity-Attribute-Value (EAV)
**Description:** Store attributes as rows in a separate table with name-value pairs.

**Pros:**
- Maximum flexibility
- Easy to add new attributes
- Can store attribute metadata

**Cons:**
- Complex queries requiring pivoting
- Poor query performance
- Difficult to validate
- No type safety

### Option 2: Wide Table with Nullable Columns
**Description:** Add all possible attribute columns to products table, most being NULL.

**Pros:**
- Simple queries
- Type safety per column
- Standard SQL indexing

**Cons:**
- Hundreds of sparse columns
- Frequent schema migrations
- Wasted storage
- Inflexible for new attributes

### Option 3: JSONB with Schema Validation
**Description:** Store extensible attributes in JSONB columns with JSON Schema validation at application layer.

**Pros:**
- Flexible structure per category
- Efficient GIN indexing
- Native PostgreSQL support
- JSON Schema validation
- No schema migrations for new attributes
- Queryable with SQL operators

**Cons:**
- Validation at application layer
- No foreign key constraints within JSON
- Requires discipline in schema management

---

## Decision

**Chosen Option:** JSONB with Schema Validation

We will use PostgreSQL JSONB columns for extensible product attributes, with JSON Schema definitions per category enforced at the application layer.

### Rationale
JSONB provides the optimal balance of flexibility and queryability for maritime product catalogs. PostgreSQL's GIN indexing enables efficient filtering, while JSON Schema validation ensures data quality without database-level constraints. This approach aligns with our unified PostgreSQL strategy and supports the diverse attribute requirements across 35 IMPA categories.

---

## Consequences

### Positive
- Add new attributes without database migrations
- Category-specific schemas with validation
- Efficient queries with GIN indexes
- Native JSON operations in PostgreSQL
- Easy serialization to/from APIs

### Negative
- No database-level referential integrity for JSONB
- **Mitigation:** Implement validation service with JSON Schema
- Potential for schema drift across records
- **Mitigation:** Schema versioning and migration tooling

### Risks
- Inconsistent data over time: Automated validation, periodic audits
- Complex nested queries: Define common query patterns, create expression indexes

---

## Implementation Notes

### Schema Structure

```sql
-- Products table with JSONB specifications
CREATE TABLE products (
    id UUID PRIMARY KEY,
    impa_code CHAR(6) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category_id UUID REFERENCES categories(id),

    -- Structured core attributes
    unit_of_measure VARCHAR(20) NOT NULL,
    ihm_relevant BOOLEAN DEFAULT FALSE,

    -- Extensible specifications (category-specific)
    specifications JSONB DEFAULT '{}',

    -- Supplier-provided additional info
    extended_attributes JSONB DEFAULT '{}'
);

-- GIN indexes for JSONB queries
CREATE INDEX idx_products_specs ON products USING GIN(specifications);
CREATE INDEX idx_products_extended ON products USING GIN(extended_attributes);

-- Expression index for common filters
CREATE INDEX idx_products_brand ON products ((specifications->>'brand'));
CREATE INDEX idx_products_material ON products ((specifications->>'material'));
```

### Category-Specific JSON Schemas

```typescript
// schemas/paint-specifications.json
const paintSchema = {
  $schema: "http://json-schema.org/draft-07/schema#",
  type: "object",
  properties: {
    color_code: { type: "string", pattern: "^#[0-9A-Fa-f]{6}$" },
    finish: { enum: ["gloss", "semi-gloss", "matte", "satin"] },
    coverage_sqm_per_liter: { type: "number", minimum: 0 },
    voc_content_gpl: { type: "number", minimum: 0 },
    drying_time_hours: { type: "number", minimum: 0 },
    application_method: {
      type: "array",
      items: { enum: ["brush", "roller", "spray", "airless"] }
    },
    suitable_surfaces: { type: "array", items: { type: "string" } }
  },
  required: ["color_code", "finish"]
};

// schemas/safety-equipment-specifications.json
const safetyEquipmentSchema = {
  $schema: "http://json-schema.org/draft-07/schema#",
  type: "object",
  properties: {
    certifications: {
      type: "array",
      items: { enum: ["SOLAS", "MED", "USCG", "DNV", "Lloyd's"] }
    },
    capacity: { type: "string" },
    inspection_interval_months: { type: "integer", minimum: 1 },
    expiry_years: { type: "integer", minimum: 1 },
    service_requirements: { type: "string" }
  },
  required: ["certifications"]
};

// schemas/engine-parts-specifications.json
const enginePartsSchema = {
  $schema: "http://json-schema.org/draft-07/schema#",
  type: "object",
  properties: {
    dimensions: {
      type: "object",
      properties: {
        length_mm: { type: "number" },
        width_mm: { type: "number" },
        height_mm: { type: "number" },
        weight_kg: { type: "number" }
      }
    },
    material: { type: "string" },
    pressure_rating_bar: { type: "number" },
    temperature_range: {
      type: "object",
      properties: {
        min_celsius: { type: "number" },
        max_celsius: { type: "number" }
      }
    },
    compatible_models: { type: "array", items: { type: "string" } }
  }
};
```

### Validation Service

```typescript
import Ajv from 'ajv';

class SpecificationValidator {
  private ajv: Ajv;
  private schemas: Map<string, object>;

  constructor() {
    this.ajv = new Ajv({ allErrors: true });
    this.schemas = new Map();
  }

  registerCategorySchema(categoryId: string, schema: object): void {
    this.schemas.set(categoryId, schema);
    this.ajv.addSchema(schema, categoryId);
  }

  validate(categoryId: string, specifications: object): ValidationResult {
    const validate = this.ajv.getSchema(categoryId);
    if (!validate) {
      return { valid: true, errors: [] }; // No schema = no validation
    }

    const valid = validate(specifications);
    return {
      valid: valid as boolean,
      errors: validate.errors || []
    };
  }
}
```

### Query Patterns

```sql
-- Filter by specification attribute
SELECT * FROM products
WHERE specifications->>'brand' = 'International';

-- Filter by nested value
SELECT * FROM products
WHERE (specifications->'dimensions'->>'length_mm')::numeric > 100;

-- Check array contains value
SELECT * FROM products
WHERE specifications->'certifications' ? 'SOLAS';

-- Full-text search in specifications
SELECT * FROM products
WHERE specifications::text ILIKE '%stainless%';

-- Aggregate by specification value
SELECT specifications->>'material' as material, COUNT(*)
FROM products
GROUP BY specifications->>'material';
```

### Dependencies
- ADR-FN-002: Product Master Data Model
- ADR-FN-004: Product Hierarchy & Categories
- ADR-NF-001: PostgreSQL as Unified Data Store

### Migration Strategy
1. Define JSON Schemas for all 35 IMPA categories
2. Implement validation service with schema registry
3. Create GIN indexes on specifications column
4. Add expression indexes for common filter attributes
5. Build admin UI for schema management

---

## Operational Considerations

### JSONB Schema Governance

A formal governance process ensures JSONB schemas remain maintainable, queryable, and consistent:

**Schema Registry Architecture:**

| Component | Purpose | Storage |
|-----------|---------|---------|
| Schema Definitions | JSON Schema files per category | Git repository + database |
| Schema Versions | Version history with migration paths | `category_schemas` table |
| Validation Service | Runtime enforcement | Application layer (AJV) |
| Schema Admin UI | CRUD for schemas by data stewards | Admin portal |

```sql
-- Schema registry table
CREATE TABLE category_schemas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID REFERENCES categories(id) NOT NULL,
    version INTEGER NOT NULL,
    schema_json JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'DRAFT',  -- DRAFT, ACTIVE, DEPRECATED
    migration_from_version INTEGER,
    migration_script TEXT,  -- JS function for data migration
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    activated_at TIMESTAMPTZ,

    UNIQUE(category_id, version)
);

CREATE INDEX idx_category_schemas_active ON category_schemas(category_id)
    WHERE status = 'ACTIVE';

-- Track which schema version each product uses
ALTER TABLE products ADD COLUMN specification_schema_version INTEGER DEFAULT 1;
```

**Governance Rules:**

| Rule | Enforcement | Consequence |
|------|-------------|-------------|
| All JSONB fields must have a schema | CI/CD check | Deployment blocked |
| Schema changes require review | PR approval from data steward | Manual gate |
| Breaking changes require migration | Migration script mandatory | Version bump required |
| Max nesting depth: 3 levels | Schema validator | Schema rejected |
| Max array length: 100 items | Runtime validation | Truncation + warning |
| Max JSONB document size: 64KB | Database constraint | Insert rejected |

```typescript
// Schema governance service
class SchemaGovernanceService {
  async proposeSchemaChange(
    categoryId: string,
    newSchema: JSONSchema,
    changeDescription: string
  ): Promise<SchemaChangeProposal> {
    const currentSchema = await this.getActiveSchema(categoryId);

    // Validate schema structure
    await this.validateSchemaRules(newSchema);

    // Detect breaking changes
    const breakingChanges = this.detectBreakingChanges(currentSchema, newSchema);

    // Create proposal
    const proposal = await this.createProposal({
      categoryId,
      currentVersion: currentSchema.version,
      proposedVersion: currentSchema.version + 1,
      schema: newSchema,
      breakingChanges,
      changeDescription,
      requiresMigration: breakingChanges.length > 0
    });

    // Notify data stewards
    await this.notifyReviewers(proposal);

    return proposal;
  }

  private detectBreakingChanges(
    oldSchema: JSONSchema,
    newSchema: JSONSchema
  ): BreakingChange[] {
    const changes: BreakingChange[] = [];

    // Removed required fields
    const oldRequired = new Set(oldSchema.required || []);
    const newRequired = new Set(newSchema.required || []);
    for (const field of oldRequired) {
      if (!newRequired.has(field)) {
        changes.push({ type: 'REQUIRED_FIELD_REMOVED', field });
      }
    }

    // Type changes
    for (const [field, oldDef] of Object.entries(oldSchema.properties || {})) {
      const newDef = newSchema.properties?.[field];
      if (newDef && oldDef.type !== newDef.type) {
        changes.push({ type: 'TYPE_CHANGED', field, from: oldDef.type, to: newDef.type });
      }
    }

    return changes;
  }
}
```

### Indexing Strategy

JSONB indexes are carefully managed to balance query performance with write overhead:

**Index Types and Use Cases:**

| Index Type | Syntax | Best For | Overhead |
|------------|--------|----------|----------|
| GIN (default) | `USING GIN(specifications)` | Existence checks, containment | High write, low read |
| GIN (jsonb_path_ops) | `USING GIN(specifications jsonb_path_ops)` | Deep path queries | Lower write, limited ops |
| Expression (B-tree) | `ON ((specifications->>'field'))` | Equality/range on specific field | Low overhead |
| Partial | `WHERE category_id = X` | Category-specific attributes | Minimal overhead |

**Index Inventory:**

```sql
-- Global GIN index for containment queries (applies to all products)
CREATE INDEX idx_products_specs_gin ON products USING GIN(specifications jsonb_path_ops);

-- Expression indexes for high-cardinality filter fields
CREATE INDEX idx_specs_brand ON products ((specifications->>'brand'))
    WHERE specifications ? 'brand';
CREATE INDEX idx_specs_manufacturer ON products ((specifications->>'manufacturer'))
    WHERE specifications ? 'manufacturer';
CREATE INDEX idx_specs_material ON products ((specifications->>'material'))
    WHERE specifications ? 'material';

-- Category-specific indexes for common query patterns
-- Paint category (IMPA 25-27)
CREATE INDEX idx_specs_paint_finish ON products ((specifications->>'finish'))
    WHERE category_id IN (SELECT id FROM categories WHERE path <@ 'deck.paint');
CREATE INDEX idx_specs_paint_color ON products ((specifications->>'color_code'))
    WHERE category_id IN (SELECT id FROM categories WHERE path <@ 'deck.paint');

-- Safety equipment (IMPA 31-33)
CREATE INDEX idx_specs_safety_cert ON products USING GIN((specifications->'certifications'))
    WHERE category_id IN (SELECT id FROM categories WHERE path <@ 'safety');

-- Engine parts (IMPA 71-87)
CREATE INDEX idx_specs_engine_pressure ON products (((specifications->'pressure_rating_bar')::numeric))
    WHERE category_id IN (SELECT id FROM categories WHERE path <@ 'engine');
```

**Index Maintenance Schedule:**

| Task | Frequency | Method |
|------|-----------|--------|
| REINDEX for bloat | Weekly (Sunday 03:00 UTC) | `REINDEX INDEX CONCURRENTLY` |
| Unused index detection | Monthly | `pg_stat_user_indexes` analysis |
| New index deployment | On demand | `CREATE INDEX CONCURRENTLY` |
| Query plan monitoring | Continuous | `pg_stat_statements` + alerts |

```typescript
// Index usage monitoring
async function analyzeIndexUsage(): Promise<IndexUsageReport> {
  const unusedIndexes = await this.db.query(`
    SELECT indexrelname, idx_scan, idx_tup_read, pg_size_pretty(pg_relation_size(indexrelid))
    FROM pg_stat_user_indexes
    WHERE schemaname = 'public'
      AND indexrelname LIKE 'idx_specs_%'
      AND idx_scan < 100  -- Less than 100 scans
    ORDER BY pg_relation_size(indexrelid) DESC
  `);

  const slowQueries = await this.db.query(`
    SELECT query, calls, mean_time, rows
    FROM pg_stat_statements
    WHERE query LIKE '%specifications%'
      AND mean_time > 100  -- Over 100ms average
    ORDER BY total_time DESC
    LIMIT 20
  `);

  return { unusedIndexes, slowQueries };
}
```

### Query Guardrails

To prevent unbounded, slow JSONB queries:

| Guardrail | Implementation | Limit |
|-----------|----------------|-------|
| Query timeout | `statement_timeout` | 5 seconds for user queries |
| Result limit | Mandatory `LIMIT` clause | 1000 rows max |
| Deep path restriction | Query parser | Max 3 levels deep |
| Full scan prevention | Query analyzer | Block `specifications::text LIKE` on large tables |

```typescript
// Query analyzer middleware
class JsonbQueryGuard {
  analyzeQuery(query: ProductSearchQuery): QueryAnalysis {
    const warnings: string[] = [];
    const blocked: string[] = [];

    // Check for unbounded text search
    if (query.filters.some(f => f.operator === 'TEXT_CONTAINS' && !f.field.startsWith('specifications.'))) {
      blocked.push('Full-text search on entire JSONB document is not allowed. Use specific field paths.');
    }

    // Check nesting depth
    const maxDepth = Math.max(...query.filters.map(f => f.field.split('.').length));
    if (maxDepth > 4) {
      blocked.push(`Query path depth ${maxDepth} exceeds maximum of 4 levels.`);
    }

    // Warn about missing indexes
    for (const filter of query.filters) {
      if (!this.hasIndex(filter.field)) {
        warnings.push(`No index exists for field '${filter.field}'. Query may be slow.`);
      }
    }

    return { warnings, blocked, canExecute: blocked.length === 0 };
  }
}
```

### Fields That Must Stay Relational

The following fields are explicitly kept as typed columns for performance-critical operations:

| Field | Type | Table | Rationale |
|-------|------|-------|-----------|
| `impa_code` | CHAR(6) | products | Primary identifier, indexed, foreign key target |
| `issa_code` | VARCHAR(10) | products | Secondary identifier, indexed for lookups |
| `name` | VARCHAR(255) | products | Full-text search, sorting, display |
| `category_id` | UUID | products | Foreign key, faceted filtering, joins |
| `unit_of_measure` | VARCHAR(20) | products | Standardized values, reporting aggregation |
| `ihm_relevant` | BOOLEAN | products | Compliance filtering, regulatory reporting |
| `hazmat_class` | VARCHAR(10) | products | Compliance filtering, safety queries |
| `supplier_id` | UUID | supplier_products | Foreign key, join performance |
| `price` | DECIMAL | supplier_product_prices | Sorting, range queries, aggregation |
| `lead_time_days` | INTEGER | supplier_products | Filtering, sorting, availability logic |
| `is_active` | BOOLEAN | supplier_products | Filtering active offerings |

**Decision Matrix for Field Placement:**

| Criterion | Relational Column | JSONB Field |
|-----------|-------------------|-------------|
| Used in WHERE clause > 1000x/day | Required | Avoid |
| Used in JOIN conditions | Required | Never |
| Used in ORDER BY | Strongly preferred | With expression index only |
| Used in GROUP BY / aggregations | Required | Avoid |
| Foreign key relationship | Required | Never |
| Compliance/regulatory reporting | Required | Never |
| Varies by category | Avoid | Preferred |
| Frequently null (> 80% of records) | Avoid | Preferred |
| Schema changes expected | Avoid | Preferred |

### Core Query Patterns

The following query patterns must execute efficiently (< 100ms p95):

| Pattern | Query Type | Index Strategy | Target Latency |
|---------|------------|----------------|----------------|
| Category browse | Filter by category_id + pagination | B-tree on category_id | < 50ms |
| Keyword search | Full-text on name + description | GIN tsvector | < 100ms |
| Faceted filter | Category + multiple JSONB attributes | Composite partial indexes | < 100ms |
| Supplier lookup | Filter by supplier_id | B-tree on supplier_id | < 20ms |
| Price range | Range query on price + category | B-tree composite | < 50ms |
| Compliance filter | IHM flag + hazmat class | Partial index on boolean | < 30ms |
| Specification match | Exact match on JSONB field | Expression index | < 50ms |
| Certification check | Array containment in JSONB | GIN on JSONB array | < 80ms |

```sql
-- Example optimized queries for each pattern

-- 1. Category browse with pagination
SELECT p.*, sp.supplier_id, sp.lead_time_days
FROM products p
LEFT JOIN supplier_products sp ON p.id = sp.product_id AND sp.is_active = true
WHERE p.category_id = $1
ORDER BY p.name
LIMIT 50 OFFSET $2;

-- 2. Faceted filter (paint products with specific finish and certifications)
SELECT p.*
FROM products p
WHERE p.category_id IN (SELECT id FROM categories WHERE path <@ 'deck.paint')
  AND p.specifications->>'finish' = 'gloss'
  AND p.specifications->'certifications' ? 'IMO'
ORDER BY p.name
LIMIT 50;

-- 3. Compliance filter (IHM-relevant products with specific hazmat class)
SELECT p.*, c.name as category_name
FROM products p
JOIN categories c ON p.category_id = c.id
WHERE p.ihm_relevant = true
  AND p.hazmat_class IN ('3', '6.1', '8')
ORDER BY c.path, p.name;

-- 4. Specification match with price range
SELECT p.*, MIN(spp.price) as min_price
FROM products p
JOIN supplier_products sp ON p.id = sp.product_id
JOIN supplier_product_prices spp ON sp.id = spp.supplier_product_id
WHERE p.specifications->>'material' = 'stainless steel'
  AND spp.price BETWEEN $1 AND $2
  AND spp.valid_to IS NULL OR spp.valid_to > CURRENT_DATE
GROUP BY p.id
ORDER BY min_price;
```

### Open Questions (Resolved)

- **Q:** What are the core query patterns that must be supported efficiently?
  - **A:** Eight core query patterns have been identified and optimized:
    1. **Category browsing**: B-tree index on `category_id`, < 50ms
    2. **Keyword search**: GIN index on tsvector for name/description, < 100ms
    3. **Faceted filtering**: Composite partial indexes combining category + JSONB attributes, < 100ms
    4. **Supplier lookup**: B-tree on `supplier_id`, < 20ms
    5. **Price range queries**: Composite B-tree on (category, price), < 50ms
    6. **Compliance filtering**: Partial index on `ihm_relevant = true`, < 30ms
    7. **Specification exact match**: Expression indexes on common JSONB fields, < 50ms
    8. **Certification containment**: GIN index on JSONB arrays, < 80ms

    All patterns are validated through query plan analysis with `EXPLAIN ANALYZE`, and monitored via `pg_stat_statements` with alerting when p95 latency exceeds thresholds.

---

## References
- [PostgreSQL JSONB Documentation](https://www.postgresql.org/docs/current/datatype-json.html)
- [JSON Schema Specification](https://json-schema.org/)
- [AJV JSON Schema Validator](https://ajv.js.org/)
- [PostgreSQL GIN Index Guide](https://www.postgresql.org/docs/current/gin-intro.html)
