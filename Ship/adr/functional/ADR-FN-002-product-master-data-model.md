# ADR-FN-002: Product Master Data Model

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Data

---

## Context

The platform requires a robust product master data model to manage 50,000+ maritime products with complex attributes, hazardous material flags, supplier variants, and support for document AI matching.

### Business Context
Maritime procurement involves diverse product categories from provisions (food, welfare items) to technical equipment (valves, bearings, safety gear). Each product may have multiple suppliers offering variants with different specifications. The Inventory of Hazardous Materials (IHM) compliance under EU Ship Recycling Regulation requires tracking hazardous material content. Products must support multi-language descriptions for international operations.

### Technical Context
- PostgreSQL 16+ as primary database (ADR-NF-001)
- pgvector for semantic search embeddings (ADR-NF-002)
- IMPA codes as primary identifier (ADR-FN-001)
- JSONB for extensible attributes (ADR-FN-005)
- Integration with document AI pipeline for SKU matching

### Assumptions
- Product catalog will grow to 100K+ items over 3 years
- Multiple suppliers can offer the same IMPA-coded product
- IHM compliance tracking is mandatory for EU-flagged vessels
- Product descriptions need vector embeddings for semantic search

---

## Decision Drivers

- Support for 50K+ products with complex attributes
- Multi-supplier variant management
- IHM/hazardous material compliance tracking
- Semantic search capability for document AI
- Extensibility for category-specific attributes
- Performance at scale for catalog browsing and search

---

## Considered Options

### Option 1: Normalized Relational Model
**Description:** Fully normalized schema with separate tables for products, attributes, suppliers, variants, and compliance flags.

**Pros:**
- Strong data integrity
- Efficient storage without duplication
- Clear relationships between entities
- Easy to maintain and update individual attributes

**Cons:**
- Complex queries requiring multiple joins
- Slower read performance for product listings
- Rigid structure harder to extend

### Option 2: Hybrid Structured + JSONB Model
**Description:** Core attributes in typed columns with JSONB for category-specific and extensible attributes.

**Pros:**
- Best of both worlds: integrity for core data, flexibility for extensions
- PostgreSQL JSONB is indexed and queryable
- Simpler queries for common operations
- Easy to add new attributes without schema changes
- Supports category-specific attribute schemas

**Cons:**
- JSONB attributes lack foreign key constraints
- Requires application-level validation for JSONB fields
- Slightly more complex indexing strategy

### Option 3: Document-Oriented (MongoDB)
**Description:** Store products as documents in MongoDB with flexible schema.

**Pros:**
- Maximum flexibility in product structure
- Native JSON storage
- Horizontal scaling

**Cons:**
- Loss of ACID guarantees for transactions
- Additional infrastructure to manage
- No native vector search (requires separate system)
- Inconsistent with unified PostgreSQL strategy

---

## Decision

**Chosen Option:** Hybrid Structured + JSONB Model

We will implement a hybrid schema with typed columns for core product attributes and JSONB for category-specific extensible attributes.

### Rationale
The hybrid approach provides data integrity for critical fields (IMPA code, pricing, compliance flags) while allowing flexibility for the diverse attribute requirements across 35 IMPA categories. PostgreSQL's JSONB support with GIN indexing enables efficient querying of extended attributes without sacrificing the benefits of a relational database.

---

## Consequences

### Positive
- Strong typing and constraints for critical business data
- Flexible extension without schema migrations
- Single database technology simplifies operations
- Native support for vector embeddings via pgvector
- Efficient indexing on both structured and JSONB fields

### Negative
- JSONB validation must be handled at application layer
- **Mitigation:** Implement JSON Schema validation in API layer
- Complex JSONB queries can be harder to optimize
- **Mitigation:** Define common query patterns and create appropriate indexes

### Risks
- JSONB data becomes inconsistent over time: Implement strict API validation and periodic data quality audits
- Performance degradation with complex JSONB queries: Monitor query performance, create targeted indexes

---

## Implementation Notes

### Core Schema

```sql
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    impa_code CHAR(6) UNIQUE NOT NULL,
    issa_code VARCHAR(10),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category_id UUID REFERENCES categories(id),
    unit_of_measure VARCHAR(20) NOT NULL,

    -- IHM Compliance
    ihm_relevant BOOLEAN DEFAULT FALSE,
    hazmat_class VARCHAR(10),

    -- Extensible attributes
    specifications JSONB DEFAULT '{}',

    -- Vector embedding for semantic search
    embedding vector(1536),

    -- Audit fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE supplier_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id),
    supplier_id UUID REFERENCES suppliers(id),
    supplier_sku VARCHAR(50),
    manufacturer VARCHAR(100),
    part_number VARCHAR(50),
    lead_time_days INTEGER,
    min_order_quantity INTEGER DEFAULT 1,
    specifications JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,

    UNIQUE(product_id, supplier_id, supplier_sku)
);

-- Indexes
CREATE INDEX idx_products_impa ON products(impa_code);
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_ihm ON products(ihm_relevant) WHERE ihm_relevant = TRUE;
CREATE INDEX idx_products_specs ON products USING GIN(specifications);
CREATE INDEX idx_products_embedding ON products USING hnsw(embedding vector_cosine_ops);
```

### Dependencies
- ADR-FN-001: IMPA/ISSA Code as Primary Identifier
- ADR-FN-004: Product Hierarchy & Categories
- ADR-FN-005: Catalog Extensibility (JSONB)
- ADR-NF-001: PostgreSQL as Unified Data Store
- ADR-NF-002: Vector Search with pgvector

### Migration Strategy
1. Create base schema with core tables
2. Import IMPA catalog as seed data
3. Generate vector embeddings for all products
4. Onboard supplier catalogs with variant mapping
5. Implement IHM flag population from compliance data

---

## Operational Considerations

### Multi-Supplier Variant Support

The data model separates canonical product data from supplier-specific variants to avoid duplication:

| Layer | Table | Purpose | Example Fields |
|-------|-------|---------|----------------|
| Canonical | `products` | Single source of truth for IMPA-coded products | `impa_code`, `name`, `unit_of_measure`, `ihm_relevant` |
| Variants | `supplier_products` | Supplier-specific offerings linked to canonical product | `supplier_sku`, `manufacturer`, `lead_time_days`, `specifications` |
| Pricing | `supplier_product_prices` | Time-bound pricing per supplier variant | `price`, `currency`, `valid_from`, `valid_to`, `min_qty` |

```sql
-- Supplier variant with extended attributes (no duplication of core product)
CREATE TABLE supplier_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) NOT NULL,
    supplier_id UUID REFERENCES suppliers(id) NOT NULL,
    supplier_sku VARCHAR(50),
    manufacturer VARCHAR(100),
    brand VARCHAR(100),
    part_number VARCHAR(50),
    lead_time_days INTEGER,
    min_order_quantity INTEGER DEFAULT 1,
    pack_size INTEGER DEFAULT 1,
    specifications JSONB DEFAULT '{}',  -- Supplier-specific specs
    is_active BOOLEAN DEFAULT TRUE,

    UNIQUE(product_id, supplier_id, supplier_sku)
);

-- Price history with validity windows
CREATE TABLE supplier_product_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_product_id UUID REFERENCES supplier_products(id),
    price DECIMAL(12,4) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    min_quantity INTEGER DEFAULT 1,
    valid_from DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_to DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Unit Conversion System

Unit conversions are handled through a dedicated conversion table supporting both standard and category-specific conversions:

| Conversion Type | Example | Notes |
|-----------------|---------|-------|
| Standard | 1 CASE = 24 EACH | Applies across categories |
| Category-specific | 1 LTR = 0.001 M3 (for liquids) | Category context required |
| Product-specific | 1 DRUM = 200 LTR (for specific oil product) | Overrides at product level |

```sql
CREATE TABLE unit_conversions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_unit VARCHAR(20) NOT NULL,
    to_unit VARCHAR(20) NOT NULL,
    conversion_factor DECIMAL(18,8) NOT NULL,
    category_id UUID REFERENCES categories(id),  -- NULL = universal
    product_id UUID REFERENCES products(id),      -- NULL = category-wide

    UNIQUE(from_unit, to_unit, category_id, product_id)
);

-- Standard unit definitions
CREATE TABLE units_of_measure (
    code VARCHAR(20) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    unit_type VARCHAR(20) NOT NULL,  -- QUANTITY, VOLUME, WEIGHT, LENGTH
    base_unit VARCHAR(20),           -- Reference unit for conversions
    display_order INTEGER DEFAULT 0
);

-- Example conversions
INSERT INTO unit_conversions (from_unit, to_unit, conversion_factor) VALUES
    ('CASE', 'EACH', 24),
    ('DOZEN', 'EACH', 12),
    ('KG', 'G', 1000),
    ('LTR', 'ML', 1000),
    ('M', 'CM', 100);
```

**Conversion Service Pattern:**
```typescript
class UnitConversionService {
  async convert(
    value: number,
    fromUnit: string,
    toUnit: string,
    context?: { categoryId?: string; productId?: string }
  ): Promise<number> {
    // 1. Check product-specific conversion
    // 2. Fall back to category-specific conversion
    // 3. Fall back to universal conversion
    // 4. Attempt transitive conversion via base unit
  }
}
```

### Localization Strategy

Multi-language support without duplicating product records:

```sql
CREATE TABLE product_translations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) NOT NULL,
    locale CHAR(5) NOT NULL,  -- e.g., 'en-US', 'zh-CN', 'ar-AE'
    name VARCHAR(255) NOT NULL,
    description TEXT,
    search_keywords TEXT[],   -- Locale-specific search terms

    UNIQUE(product_id, locale)
);

CREATE INDEX idx_product_translations_locale ON product_translations(locale);
CREATE INDEX idx_product_translations_search ON product_translations USING GIN(search_keywords);
```

| Supported Locales | Primary Markets |
|-------------------|-----------------|
| `en-US` | Default, International |
| `zh-CN` | China, Singapore |
| `ar-AE` | UAE, Middle East |
| `de-DE` | Germany, Northern Europe |
| `ja-JP` | Japan |

### Versioning and Audit Strategy

All product master data changes are tracked through an event-sourced audit log enabling downstream service synchronization:

```sql
-- Audit log for all product changes
CREATE TABLE product_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL,  -- 'product', 'supplier_product', 'price'
    entity_id UUID NOT NULL,
    operation VARCHAR(10) NOT NULL,    -- 'INSERT', 'UPDATE', 'DELETE'
    changed_fields JSONB,              -- Only changed fields with old/new values
    changed_by UUID REFERENCES users(id),
    change_reason VARCHAR(255),
    version INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_entity ON product_audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_timestamp ON product_audit_log(created_at);

-- Version column on products for optimistic locking
ALTER TABLE products ADD COLUMN version INTEGER DEFAULT 1;
ALTER TABLE supplier_products ADD COLUMN version INTEGER DEFAULT 1;

-- Trigger for automatic audit logging
CREATE OR REPLACE FUNCTION audit_product_changes() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO product_audit_log (entity_type, entity_id, operation, changed_fields, version)
    VALUES (
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        TG_OP,
        jsonb_build_object(
            'old', to_jsonb(OLD),
            'new', to_jsonb(NEW)
        ),
        COALESCE(NEW.version, OLD.version)
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER products_audit_trigger
AFTER INSERT OR UPDATE OR DELETE ON products
FOR EACH ROW EXECUTE FUNCTION audit_product_changes();
```

**Downstream Sync Patterns:**

| Consumer | Sync Method | Frequency | Data Needed |
|----------|-------------|-----------|-------------|
| Search Index (Meilisearch) | CDC via audit log | Real-time | All product fields |
| Analytics Data Warehouse | Batch export | Daily | Full snapshot |
| External ERP Integration | Webhook notifications | On change | Changed fields only |
| Vector Embedding Service | Queue-based | Async batch | Name, description changes |

```typescript
// Event emission for downstream consumers
@OnEvent('product.updated')
async handleProductUpdate(event: ProductUpdatedEvent) {
  // Update search index
  await this.searchService.indexProduct(event.productId);

  // Regenerate embeddings if text changed
  if (event.changedFields.includes('name') || event.changedFields.includes('description')) {
    await this.embeddingQueue.add('regenerate', { productId: event.productId });
  }

  // Notify subscribed ERPs
  await this.erpIntegrationService.notifyProductChange(event);
}
```

### Conflict Resolution: Supplier vs Master Data

When supplier-provided attributes conflict with canonical master data, the following resolution hierarchy applies:

| Field Category | Authority | Resolution Rule |
|----------------|-----------|-----------------|
| IMPA Code | Master | Canonical, never overwritten |
| Product Name | Master | Supplier can provide alternate name in `supplier_products.specifications.alternate_name` |
| Unit of Measure | Master | Supplier pack sizes stored separately in `supplier_products.pack_size` |
| Technical Specs | Merge | Supplier specs stored in `supplier_products.specifications`, queryable alongside master specs |
| IHM/Hazmat Flags | Master | Compliance flags never overridden by supplier data |
| Pricing | Supplier | Supplier owns pricing; master has no pricing data |
| Lead Time | Supplier | Supplier-specific operational data |

```typescript
// Conflict detection and resolution during ingestion
interface ConflictResolution {
  field: string;
  masterValue: any;
  supplierValue: any;
  resolution: 'USE_MASTER' | 'USE_SUPPLIER' | 'MERGE' | 'FLAG_FOR_REVIEW';
  reason: string;
}

async function resolveSupplierConflicts(
  product: Product,
  supplierData: SupplierProductInput
): Promise<ConflictResolution[]> {
  const conflicts: ConflictResolution[] = [];

  // Name mismatch - store supplier variant
  if (supplierData.name && supplierData.name !== product.name) {
    conflicts.push({
      field: 'name',
      masterValue: product.name,
      supplierValue: supplierData.name,
      resolution: 'MERGE',
      reason: 'Supplier alternate name stored in specifications'
    });
  }

  // Unit mismatch - flag for review
  if (supplierData.unit && supplierData.unit !== product.unit_of_measure) {
    conflicts.push({
      field: 'unit_of_measure',
      masterValue: product.unit_of_measure,
      supplierValue: supplierData.unit,
      resolution: 'FLAG_FOR_REVIEW',
      reason: 'Unit conversion may be required'
    });
  }

  return conflicts;
}
```

### Open Questions (Resolved)

- **Q:** How will conflicts between supplier attributes and master data be resolved?
  - **A:** A hierarchical conflict resolution strategy is implemented where canonical fields (IMPA code, name, IHM flags) are owned by master data and never overwritten. Supplier-specific attributes are stored in the `supplier_products.specifications` JSONB field, enabling parallel storage without conflict. The ingestion pipeline detects conflicts and either auto-resolves based on field category or flags for manual review. See "Conflict Resolution" table above for field-by-field rules.

---

## References
- [PostgreSQL JSONB Documentation](https://www.postgresql.org/docs/current/datatype-json.html)
- [pgvector Extension](https://github.com/pgvector/pgvector)
- [EU Ship Recycling Regulation - IHM Requirements](https://eur-lex.europa.eu/eli/reg/2013/1257/oj)
- IMPA Marine Stores Guide Data Structure
