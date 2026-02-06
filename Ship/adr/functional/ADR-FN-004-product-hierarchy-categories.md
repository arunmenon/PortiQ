# ADR-FN-004: Product Hierarchy & Categories

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Data

---

## Context

The platform requires a structured product hierarchy to organize 50,000+ maritime products for intuitive navigation, filtering, and reporting aligned with industry standards.

### Business Context
IMPA codes inherently contain category information in their first two digits, organizing products into 35 main categories covering all aspects of maritime supply. These categories are universally recognized in the industry: provisions (00), deck operations (21-37), engine room supplies (71-87), safety equipment (31-33), and consumables (45-55). Buyers expect to navigate the catalog using this familiar structure.

### Technical Context
- IMPA 6-digit codes: first 2 digits indicate main category
- Need to support multi-level hierarchy (category > subcategory > product group)
- Integration with search faceting (Meilisearch)
- Category-specific attribute schemas (JSONB validation)
- Performance considerations for tree traversal queries

### Assumptions
- IMPA category structure will remain stable
- Three levels of hierarchy sufficient for navigation
- Some products may belong to multiple logical categories (but have single IMPA category)
- Category-specific attributes vary significantly across categories

---

## Decision Drivers

- Alignment with industry-standard IMPA categorization
- Intuitive navigation for maritime procurement professionals
- Support for faceted search and filtering
- Enable category-specific attribute schemas
- Efficient query performance for tree structures
- Flexibility for platform-specific subcategories

---

## Considered Options

### Option 1: IMPA Code Prefix Derivation
**Description:** Derive categories directly from IMPA code prefixes without storing separate category entities.

**Pros:**
- Simple implementation
- Always consistent with product codes
- No synchronization needed

**Cons:**
- No support for category metadata
- Cannot add platform-specific subcategories
- Limited flexibility for custom hierarchies
- No category-specific configuration

### Option 2: Adjacency List Model
**Description:** Traditional parent-child relationship table with recursive queries.

**Pros:**
- Simple schema
- Easy to understand and maintain
- Flexible hierarchy modifications

**Cons:**
- Recursive queries expensive in PostgreSQL
- Multiple queries for full path retrieval
- Performance degrades with depth

### Option 3: Materialized Path with Closure Table
**Description:** Store full path as materialized string plus closure table for efficient ancestor/descendant queries.

**Pros:**
- Efficient tree traversal queries
- Fast ancestor/descendant lookups
- Single query for full subtree
- PostgreSQL ltree extension support

**Cons:**
- More complex schema
- Path updates require maintenance
- Additional storage for closure table

---

## Decision

**Chosen Option:** Materialized Path with Closure Table (using PostgreSQL ltree)

We will implement a hybrid approach using PostgreSQL's ltree extension for materialized paths combined with a denormalized closure table for efficient hierarchy queries.

### Rationale
The ltree extension provides powerful hierarchical query capabilities native to PostgreSQL, with operators for ancestor/descendant queries, pattern matching, and path operations. Combined with strategic denormalization, this enables efficient catalog navigation while maintaining flexibility for platform-specific subcategories beyond the IMPA standard.

---

## Consequences

### Positive
- Single-query subtree retrieval
- Efficient breadcrumb generation
- Native PostgreSQL indexing support
- Pattern matching for flexible queries
- Support for category-specific configurations

### Negative
- Path updates require cascade maintenance
- **Mitigation:** Categories rarely change; implement trigger-based maintenance
- Additional complexity in schema
- **Mitigation:** Encapsulate in repository layer with clear API

### Risks
- ltree extension availability: Available in all major PostgreSQL distributions and cloud providers
- Performance with deep hierarchies: Maritime categories are shallow (3 levels max)

---

## Implementation Notes

### Schema Design

```sql
-- Enable ltree extension
CREATE EXTENSION IF NOT EXISTS ltree;

CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(10) UNIQUE NOT NULL,  -- e.g., "21", "21.01", "21.01.001"
    impa_prefix CHAR(2),               -- IMPA category prefix
    name VARCHAR(100) NOT NULL,
    description TEXT,
    path ltree NOT NULL,               -- e.g., "deck.ropes.synthetic"
    level INTEGER NOT NULL,            -- 1=main, 2=sub, 3=group

    -- Category-specific configuration
    attribute_schema JSONB,            -- JSON Schema for category attributes
    ihm_category BOOLEAN DEFAULT FALSE,

    -- Display
    icon VARCHAR(50),
    display_order INTEGER DEFAULT 0,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for hierarchy queries
CREATE INDEX idx_categories_path ON categories USING GIST(path);
CREATE INDEX idx_categories_impa ON categories(impa_prefix);
CREATE INDEX idx_categories_level ON categories(level);

-- Closure table for efficient queries
CREATE TABLE category_closure (
    ancestor_id UUID REFERENCES categories(id),
    descendant_id UUID REFERENCES categories(id),
    depth INTEGER NOT NULL,
    PRIMARY KEY (ancestor_id, descendant_id)
);
```

### IMPA Category Mapping

```typescript
const IMPA_CATEGORIES = {
  '00': { name: 'Provisions', path: 'provisions' },
  '11': { name: 'Bonded Stores', path: 'provisions.bonded' },
  '17': { name: 'Tableware', path: 'provisions.tableware' },
  '21': { name: 'Ropes & Hawsers', path: 'deck.ropes' },
  '23': { name: 'Rigging Equipment', path: 'deck.rigging' },
  '25': { name: 'Marine Paint', path: 'deck.paint' },
  '31': { name: 'Protective Gear', path: 'safety.protective' },
  '33': { name: 'Safety Equipment', path: 'safety.equipment' },
  '37': { name: 'Nautical Equipment', path: 'deck.nautical' },
  '39': { name: 'Medicine', path: 'safety.medicine' },
  '45': { name: 'Petroleum Products', path: 'consumables.petroleum' },
  '55': { name: 'Cleaning Chemicals', path: 'consumables.cleaning' },
  '59': { name: 'Pneumatic & Electrical Tools', path: 'tools.power' },
  '61': { name: 'Hand Tools', path: 'tools.hand' },
  '63': { name: 'Cutting Tools', path: 'tools.cutting' },
  '65': { name: 'Measuring Tools', path: 'tools.measuring' },
  '71': { name: 'Pipes & Tubes', path: 'engine.pipes' },
  '75': { name: 'Valves & Cocks', path: 'engine.valves' },
  '77': { name: 'Bearings', path: 'engine.bearings' },
  '85': { name: 'Welding Equipment', path: 'tools.welding' },
  '87': { name: 'Machinery Equipment', path: 'engine.machinery' },
};
```

### Query Examples

```sql
-- Get all descendants of a category
SELECT * FROM categories
WHERE path <@ 'deck.ropes';

-- Get breadcrumb path
SELECT * FROM categories
WHERE path @> 'deck.ropes.synthetic'
ORDER BY level;

-- Get immediate children
SELECT * FROM categories
WHERE path ~ 'deck.*{1}';

-- Count products per category (with subtree)
SELECT c.name, COUNT(p.id)
FROM categories c
JOIN products p ON p.category_id IN (
    SELECT id FROM categories WHERE path <@ c.path
)
GROUP BY c.id;
```

### Dependencies
- ADR-FN-001: IMPA/ISSA Code as Primary Identifier
- ADR-FN-002: Product Master Data Model
- ADR-FN-005: Catalog Extensibility (JSONB)
- ADR-NF-001: PostgreSQL as Unified Data Store

### Migration Strategy
1. Create categories table with ltree support
2. Import IMPA main categories (35 categories)
3. Add platform-specific subcategories
4. Populate closure table
5. Link products to categories
6. Create Meilisearch facet configuration

---

## Operational Considerations

### IMPA/ISSA Hierarchy Mapping

The platform maintains explicit, audited mappings between industry-standard codes and internal categories:

| Standard | Code Format | Hierarchy Depth | Mapping Approach |
|----------|-------------|-----------------|------------------|
| IMPA | 6-digit (XX.XX.XX) | 3 levels | First 2 digits = main category, next 2 = subcategory |
| ISSA | 2-letter prefix + 4 digits | 2 levels | Letter prefix = category group |
| Platform Internal | UUID + ltree path | 3 levels | Normalized superset of both standards |

```sql
-- Explicit mapping tables for industry standards
CREATE TABLE impa_category_mapping (
    impa_prefix CHAR(2) PRIMARY KEY,
    impa_category_name VARCHAR(100) NOT NULL,
    internal_category_id UUID REFERENCES categories(id) NOT NULL,
    mapping_confidence VARCHAR(10) DEFAULT 'EXACT',  -- EXACT, PARTIAL, MANUAL
    notes TEXT,
    last_verified DATE DEFAULT CURRENT_DATE,
    verified_by UUID REFERENCES users(id)
);

CREATE TABLE issa_category_mapping (
    issa_prefix CHAR(2) PRIMARY KEY,
    issa_category_name VARCHAR(100) NOT NULL,
    internal_category_id UUID REFERENCES categories(id) NOT NULL,
    impa_equivalent CHAR(2) REFERENCES impa_category_mapping(impa_prefix),
    mapping_confidence VARCHAR(10) DEFAULT 'EXACT',
    notes TEXT,
    last_verified DATE DEFAULT CURRENT_DATE
);

-- Cross-reference view for unified lookup
CREATE VIEW unified_category_mapping AS
SELECT
    'IMPA' as standard,
    impa_prefix as code,
    impa_category_name as standard_name,
    c.id as internal_id,
    c.name as internal_name,
    c.path as internal_path
FROM impa_category_mapping m
JOIN categories c ON m.internal_category_id = c.id
UNION ALL
SELECT
    'ISSA' as standard,
    issa_prefix as code,
    issa_category_name as standard_name,
    c.id as internal_id,
    c.name as internal_name,
    c.path as internal_path
FROM issa_category_mapping m
JOIN categories c ON m.internal_category_id = c.id;
```

**Complete IMPA-to-Internal Mapping:**

| IMPA Prefix | IMPA Category | Internal Path | Notes |
|-------------|---------------|---------------|-------|
| 00-09 | Provisions & Stores | `provisions` | Food, beverages, welfare |
| 10-19 | Bonded Stores | `provisions.bonded` | Tobacco, alcohol, duty-free |
| 17-19 | Tableware & Galley | `provisions.galley` | Kitchen equipment |
| 21-29 | Deck Supplies | `deck` | Ropes, rigging, paint |
| 31-39 | Safety & Medical | `safety` | PPE, lifesaving, medicine |
| 45-59 | Consumables | `consumables` | Petroleum, chemicals, cleaning |
| 59-69 | Tools | `tools` | Power, hand, measuring tools |
| 71-89 | Engine Room | `engine` | Pipes, valves, machinery |

**ISSA Cross-Reference:**

| ISSA Code | ISSA Category | IMPA Equivalent | Internal Path |
|-----------|---------------|-----------------|---------------|
| BN | Bonded Stores | 11-16 | `provisions.bonded` |
| CH | Chemicals | 55 | `consumables.chemicals` |
| DE | Deck Equipment | 21-37 | `deck` |
| EL | Electrical | 87 | `engine.electrical` |
| EN | Engine Room | 71-87 | `engine` |
| PR | Provisions | 00-09 | `provisions` |
| SA | Safety | 31-33 | `safety` |
| TO | Tools | 59-65 | `tools` |

```typescript
// Category resolution service
class CategoryMappingService {
  async resolveCategory(code: string, standard: 'IMPA' | 'ISSA'): Promise<Category> {
    const prefix = standard === 'IMPA' ? code.substring(0, 2) : code.substring(0, 2);

    const mapping = await this.db.query(`
      SELECT internal_category_id
      FROM ${standard === 'IMPA' ? 'impa_category_mapping' : 'issa_category_mapping'}
      WHERE ${standard === 'IMPA' ? 'impa_prefix' : 'issa_prefix'} = $1
    `, [prefix]);

    if (!mapping) {
      // Log unmapped code for review
      await this.auditService.logUnmappedCode(code, standard);
      return this.getDefaultCategory();
    }

    return this.categoryRepo.findById(mapping.internal_category_id);
  }

  // Periodic verification job
  async verifyMappings(): Promise<MappingVerificationReport> {
    const unmappedImpa = await this.findUnmappedImpaCodes();
    const unmappedIssa = await this.findUnmappedIssaCodes();
    const staleVerifications = await this.findStaleMappings(90); // Not verified in 90 days

    return { unmappedImpa, unmappedIssa, staleVerifications };
  }
}
```

### Multi-Category Tagging

Products maintain a primary category (derived from IMPA code) plus optional secondary tags for cross-category discovery:

```sql
-- Primary category via foreign key (mandatory, derived from IMPA)
-- products.category_id UUID REFERENCES categories(id)

-- Secondary category tags (optional, for cross-category discovery)
CREATE TABLE product_category_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) NOT NULL,
    category_id UUID REFERENCES categories(id) NOT NULL,
    tag_type VARCHAR(20) NOT NULL,  -- 'RELATED', 'ALSO_IN', 'SUBSTITUTE', 'ACCESSORY'
    confidence DECIMAL(3,2) DEFAULT 1.0,  -- ML-assigned tags have confidence < 1.0
    created_by VARCHAR(20) NOT NULL,  -- 'MANUAL', 'ML_MODEL', 'IMPA_MAPPING'
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(product_id, category_id, tag_type)
);

CREATE INDEX idx_product_tags_category ON product_category_tags(category_id);
CREATE INDEX idx_product_tags_product ON product_category_tags(product_id);
```

| Tag Type | Use Case | Example |
|----------|----------|---------|
| `RELATED` | Product appears in searches for this category | Safety harness tagged with `tools.rigging` |
| `ALSO_IN` | Product legitimately belongs to multiple categories | Cleaning chemical also in `safety.hazmat` |
| `SUBSTITUTE` | Alternative product category | Generic paint substitute for branded |
| `ACCESSORY` | Complementary product category | Brush accessories tagged with `deck.paint` |

```typescript
// Multi-category query support
async function searchProducts(query: ProductSearchQuery): Promise<Product[]> {
  return this.db.query(`
    SELECT DISTINCT p.*
    FROM products p
    LEFT JOIN product_category_tags pct ON p.id = pct.product_id
    WHERE
      -- Primary category match
      p.category_id IN (SELECT id FROM categories WHERE path <@ $1)
      OR
      -- Secondary tag match
      pct.category_id IN (SELECT id FROM categories WHERE path <@ $1)
    ORDER BY
      CASE WHEN p.category_id IN (SELECT id FROM categories WHERE path <@ $1)
           THEN 0 ELSE 1 END,  -- Primary matches first
      p.name
  `, [query.categoryPath]);
}
```

### Category Expansion Without Breaking Changes

The system supports category hierarchy modifications through a controlled migration process:

| Change Type | Impact | Migration Process |
|-------------|--------|-------------------|
| Add new subcategory | None | Insert category, populate closure table |
| Rename category | Display only | Update name, no structural change |
| Move category | Path updates | Cascade path updates via trigger |
| Split category | Products reassignment | New category + batch product migration |
| Merge categories | Products reassignment | Merge into target + update references |
| Deprecate category | Soft delete | Mark inactive, migrate products first |

```sql
-- Category state for expansion management
ALTER TABLE categories ADD COLUMN status VARCHAR(20) DEFAULT 'ACTIVE';
-- Status: ACTIVE, DEPRECATED, PENDING_MIGRATION, ARCHIVED

-- Trigger for cascading path updates
CREATE OR REPLACE FUNCTION update_category_paths() RETURNS TRIGGER AS $$
BEGIN
    IF OLD.path IS DISTINCT FROM NEW.path THEN
        -- Update all descendant paths
        UPDATE categories
        SET path = NEW.path || subpath(path, nlevel(OLD.path))
        WHERE path <@ OLD.path AND id != NEW.id;

        -- Update closure table
        DELETE FROM category_closure WHERE ancestor_id = NEW.id OR descendant_id = NEW.id;
        INSERT INTO category_closure (ancestor_id, descendant_id, depth)
        SELECT NEW.id, c.id, nlevel(c.path) - nlevel(NEW.path)
        FROM categories c WHERE c.path <@ NEW.path;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Safe category addition (no disruption)
CREATE OR REPLACE FUNCTION add_subcategory(
    parent_path ltree,
    new_code VARCHAR(10),
    new_name VARCHAR(100)
) RETURNS UUID AS $$
DECLARE
    new_id UUID;
    new_path ltree;
    parent_level INTEGER;
BEGIN
    SELECT nlevel(path) INTO parent_level FROM categories WHERE path = parent_path;
    new_path := parent_path || new_code;

    INSERT INTO categories (code, name, path, level, status)
    VALUES (new_code, new_name, new_path, parent_level + 1, 'ACTIVE')
    RETURNING id INTO new_id;

    -- Update closure table
    INSERT INTO category_closure (ancestor_id, descendant_id, depth)
    SELECT c.id, new_id, nlevel(new_path) - nlevel(c.path)
    FROM categories c WHERE new_path <@ c.path;

    -- Self-reference
    INSERT INTO category_closure (ancestor_id, descendant_id, depth)
    VALUES (new_id, new_id, 0);

    RETURN new_id;
END;
$$ LANGUAGE plpgsql;
```

### Search and Analytics Index Propagation

Category changes automatically propagate to downstream systems through an event-driven architecture:

| System | Update Method | Latency | Consistency |
|--------|---------------|---------|-------------|
| Meilisearch | Event-driven reindex | < 30 seconds | Eventually consistent |
| Analytics DW | CDC pipeline | < 5 minutes | Eventually consistent |
| Product Cache | Cache invalidation | Immediate | Strongly consistent |
| Embedding Index | Batch recompute | < 1 hour | Eventually consistent |

```typescript
// Category change event handler
@OnEvent('category.*')
class CategoryChangeHandler {
  @OnEvent('category.created')
  async handleCategoryCreated(event: CategoryCreatedEvent) {
    // Update Meilisearch facets
    await this.searchService.updateFacetConfiguration();

    // Notify analytics pipeline
    await this.analyticsService.syncCategoryDimension(event.categoryId);
  }

  @OnEvent('category.updated')
  async handleCategoryUpdated(event: CategoryUpdatedEvent) {
    if (event.changedFields.includes('path') || event.changedFields.includes('name')) {
      // Reindex all products in this category tree
      const productIds = await this.productRepo.findIdsByCategoryPath(event.oldPath);
      await this.searchService.bulkReindex(productIds);

      // Invalidate category cache
      await this.cacheService.invalidatePattern(`category:${event.categoryId}:*`);
    }
  }

  @OnEvent('category.deprecated')
  async handleCategoryDeprecated(event: CategoryDeprecatedEvent) {
    // Alert if products still assigned
    const productCount = await this.productRepo.countByCategory(event.categoryId);
    if (productCount > 0) {
      await this.alertService.warn({
        message: `Category ${event.categoryId} deprecated with ${productCount} products assigned`,
        action: 'MIGRATION_REQUIRED'
      });
    }

    // Hide from navigation but keep in search for historical queries
    await this.searchService.updateCategoryVisibility(event.categoryId, false);
  }
}
```

**Meilisearch Facet Configuration Update:**

```typescript
// Automatic facet reconfiguration on category changes
async function updateSearchFacets(): Promise<void> {
  const activeCategories = await this.categoryRepo.findActive();

  const filterableAttributes = [
    'category_id',
    'category_path',
    'category_tags',
    'ihm_relevant',
    'supplier_ids'
  ];

  const facetedAttributes = activeCategories
    .filter(c => c.level <= 2)  // Only top 2 levels as facets
    .map(c => `category_${c.code}`);

  await this.meiliClient.index('products').updateSettings({
    filterableAttributes,
    facetedAttributes
  });
}
```

### Open Questions (Resolved)

- **Q:** How will category changes propagate to analytics and search indexes?
  - **A:** Category changes propagate through an event-driven system:
    1. **Immediate**: Category CRUD operations emit domain events (`category.created`, `category.updated`, `category.deprecated`).
    2. **Search Index**: The `CategoryChangeHandler` listens for events and triggers Meilisearch reindexing for affected products. Facet configurations are automatically updated when categories are added or removed. Latency is typically < 30 seconds.
    3. **Analytics**: A CDC (Change Data Capture) pipeline streams category dimension changes to the analytics data warehouse. The `unified_category_mapping` view ensures consistent category hierarchies across reporting. Latency is typically < 5 minutes.
    4. **Cache**: Product and category caches are invalidated immediately on path or name changes to ensure UI consistency.

    The system maintains eventual consistency with monitoring alerts if propagation latency exceeds thresholds (30 seconds for search, 5 minutes for analytics).

---

## References
- [PostgreSQL ltree Extension](https://www.postgresql.org/docs/current/ltree.html)
- [IMPA Category Structure](https://www.impa.net/marine-stores-guide/)
- [Hierarchical Data in PostgreSQL](https://www.postgresqltutorial.com/postgresql-tutorial/postgresql-ltree/)
