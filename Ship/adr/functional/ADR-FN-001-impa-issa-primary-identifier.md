# ADR-FN-001: IMPA/ISSA Code as Primary Identifier

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Data

---

## Context

The maritime ship chandlery platform requires a standardized product identification system to enable seamless ordering, catalog management, and interoperability with existing maritime procurement systems worldwide.

### Business Context
The International Marine Purchasing Association's Marine Stores Guide (MSG) has been the de facto global standard for maritime procurement for 40+ years. The system comprises 50,000+ six-digit unique codes organized into 35 main categories. These codes have remained consistent, enabling seamless ordering across language barriers worldwide. Competitors like ShipServ, ShipsKart, and Source2Sea all use IMPA codes as their primary identifier, making it essential for market compatibility.

### Technical Context
The platform must integrate with:
- IMPA MSG Data Licence (CSV/Excel format with bi-annual updates)
- MSG API (launched 2022) for live cloud-based data feeds
- ISSA Ship Stores Catalogue (60,000+ items used by suppliers)
- Existing fleet management systems (AMOS, SERTICA) that use IMPA codes
- Document AI pipeline that extracts product references from requisitions

### Assumptions
- IMPA codes will remain stable and continue as industry standard
- Licensing costs for IMPA data are acceptable (varies by company size)
- Most suppliers can map their inventory to IMPA codes

---

## Decision Drivers

- Industry standardization and compatibility with existing systems
- Cross-language ordering capability for international operations
- Integration requirements with fleet management ERPs
- Supplier adoption and familiarity with coding system
- Support for document AI extraction and matching

---

## Considered Options

### Option 1: IMPA Code as Primary Identifier
**Description:** Use IMPA 6-digit codes as the canonical SKU for all products, with ISSA codes as secondary cross-reference.

**Pros:**
- Industry standard used by 40+ years
- Universal recognition across maritime procurement
- Direct integration with MSG API and data license
- Enables semantic product matching in document AI
- Compatible with all major fleet management systems

**Cons:**
- Licensing costs for IMPA data
- Bi-annual update cycle may lag new products
- Some supplier-specific products may not have IMPA codes

### Option 2: Proprietary SKU System
**Description:** Create platform-specific SKU identifiers with IMPA/ISSA as optional attributes.

**Pros:**
- Complete control over identifier format
- No licensing dependencies
- Can accommodate any product type

**Cons:**
- No industry recognition or interoperability
- Requires mapping layer for all integrations
- Increases complexity for suppliers and buyers
- Document AI cannot leverage standard codes

### Option 3: ISSA Code as Primary
**Description:** Use ISSA Ship Stores Catalogue codes as primary identifier.

**Pros:**
- Larger catalog (60,000+ items)
- Commonly used by suppliers
- No licensing fees

**Cons:**
- Less universal than IMPA
- Not as well integrated with fleet management systems
- Lacks the structured category hierarchy of IMPA

---

## Decision

**Chosen Option:** IMPA Code as Primary Identifier

We will use IMPA 6-digit codes as the canonical product identifier throughout the platform, with ISSA codes maintained as secondary cross-references for supplier flexibility.

### Rationale
IMPA's 40-year history, universal industry recognition, and structured category system make it the clear choice for a platform targeting the maritime procurement market. The licensing costs are justified by the significant reduction in integration complexity and improved document AI matching accuracy. The MSG API (launched 2022) provides modern integration capabilities that eliminate manual data management overhead.

---

## Consequences

### Positive
- Immediate interoperability with existing maritime systems
- Simplified integration with fleet management ERPs
- Enhanced document AI extraction accuracy using standard codes
- Familiar system for buyers and suppliers
- Structured 35-category hierarchy for catalog organization

### Negative
- Licensing costs for IMPA data access
- **Mitigation:** Factor into platform operating costs; costs are minor relative to value
- Products without IMPA codes require special handling
- **Mitigation:** Use ISSA cross-reference or create platform extension codes with clear prefix

### Risks
- IMPA licensing terms change unfavorably: Maintain ISSA as fallback, build abstraction layer
- New product types not covered by IMPA: Extension code system with platform prefix

---

## Implementation Notes

### Dependencies
- ADR-FN-002: Product Master Data Model (schema must accommodate IMPA structure)
- ADR-FN-003: Catalog Data Ingestion Strategy (MSG API integration)
- ADR-FN-004: Product Hierarchy & Categories (derived from IMPA prefixes)

### Migration Strategy
1. Obtain IMPA MSG Data Licence
2. Import complete IMPA catalog as base product master
3. Map existing supplier catalogs to IMPA codes
4. Implement ISSA cross-reference table
5. Create extension code system for unmapped products

---

## Licensing and Update Workflow

### IMPA Licensing

| Item | Cost | Frequency | Notes |
|------|------|-----------|-------|
| IMPA MSG API Access | ~$5,000/year | Annual | Includes updates |
| MSG Database License | Per-seat or enterprise | Annual | Required for full catalog |
| Update Subscription | Included in API | Bi-annual | Jan/Jul releases |

### Bi-Annual Update Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                 IMPA Update Process (Jan/Jul)                │
├─────────────────────────────────────────────────────────────┤
│  Week 1: Receive MSG update from IMPA                       │
│     └─ Download delta file via MSG API                      │
│                                                              │
│  Week 2: Staging validation                                  │
│     └─ Import to staging environment                        │
│     └─ Run diff against production catalog                  │
│     └─ Flag: new codes, deprecated codes, changed fields    │
│                                                              │
│  Week 3: Impact analysis                                     │
│     └─ Products affected by deprecated codes                │
│     └─ Categories with structure changes                    │
│     └─ Notify suppliers of relevant changes                 │
│                                                              │
│  Week 4: Production deployment                               │
│     └─ Apply changes during maintenance window              │
│     └─ Update search indexes                                │
│     └─ Regenerate embeddings for changed products           │
└─────────────────────────────────────────────────────────────┘
```

## Extension Code Governance

### Products Without IMPA Codes

| Product Type | Code Strategy | Ownership | QA Process |
|--------------|---------------|-----------|------------|
| Regional/local products | EXT-XXXXXX (6-digit) | Platform team | Manual review |
| Custom specifications | supplier's SKU reference | Supplier | Platform verification |
| New products (pending IMPA) | TMP-XXXXXX | Platform team | Escalate to IMPA |
| Bundled/kit items | KIT-XXXXXX | Platform team | Component verification |

### Extension Code Schema

```typescript
// Extension code format
interface ExtensionCode {
  code: string;          // EXT-000001 format
  category: string;      // IMPA 2-digit category (best fit)
  name: string;
  description: string;
  createdBy: 'platform' | 'supplier';
  verificationStatus: 'pending' | 'verified' | 'rejected';
  impaCandidate: boolean;  // Flag for IMPA submission
  linkedImpaCode?: string; // If IMPA code assigned later
}
```

### Extension Code Workflow

1. **Creation**: Supplier/platform creates extension code for unmapped product
2. **Review**: Platform team verifies no existing IMPA match
3. **Categorization**: Assign to nearest IMPA 2-digit category
4. **Monitoring**: Track usage; high-volume items flagged for IMPA submission
5. **Resolution**: Link to IMPA code when assigned, deprecate extension

## Success Metrics

### KPIs for IMPA Adoption

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| **Match accuracy** | Manual matching | >90% auto-match | % of line items auto-matched |
| **Search success rate** | - | >95% | Searches returning relevant results |
| **Extension code ratio** | - | <5% | Extension codes / total products |
| **Procurement time** | Manual (hours) | <30 min | RFQ creation to submission |
| **Data consistency** | - | >99% | Products with valid IMPA codes |

### Tracking Implementation

```sql
-- Match accuracy tracking
SELECT
  COUNT(*) as total_matches,
  SUM(CASE WHEN match_confidence >= 0.95 THEN 1 ELSE 0 END) as auto_matched,
  SUM(CASE WHEN match_source = 'impa_exact' THEN 1 ELSE 0 END) as exact_impa,
  SUM(CASE WHEN match_source = 'extension' THEN 1 ELSE 0 END) as extension_matched
FROM document_line_item_matches
WHERE created_at > NOW() - INTERVAL '30 days';
```

---

## References
- [IMPA Marine Stores Guide](https://www.impa.net/marine-stores-guide/)
- [ShipServ IMPA Catalogue](https://impa-catalogue.shipserv.com)
- [ISSA Ship Stores Catalogue](https://www.shipsupply.org)
- MESPAS MSG API Integration (February 2025)
