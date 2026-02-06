# ADR-FN-024: Fleet Management ERP Integration

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

Integration with fleet management ERPs (AMOS, SERTICA, etc.) reduces friction for enterprise buyers by enabling seamless requisition flow from their existing systems.

### Business Context
Large shipping companies manage procurement through fleet management systems:
- **AMOS (Kongsberg Maritime)**: Dominant in the market, used by major fleets
- **SERTICA**: Popular European system with strong maintenance focus
- **ShipNet**: Cloud-based modern alternative
- **NS5 (BASSnet)**: Strong in Asia-Pacific region

Integration creates sticky enterprise relationships by eliminating double data entry and enabling seamless workflows from planned maintenance to fulfilled orders.

### Technical Context
- ERPs typically support PunchOut catalog integration
- Order data exchange via cXML, OCI, or REST APIs
- Real-time inventory visibility requirements
- Integration with vessel-level purchasing workflows
- Authentication via SSO or API tokens

### Assumptions
- Enterprise customers will provide integration requirements
- Standard protocols (cXML, OCI) cover most use cases
- Some custom development may be required per ERP
- Integration complexity justifies enterprise pricing tier

---

## Decision Drivers

- Enterprise customer acquisition
- Reduce friction for large fleet operators
- Support industry-standard protocols
- Minimize per-ERP custom development
- Enable automated procurement workflows
- Competitive differentiation

---

## Considered Options

### Option 1: PunchOut Catalog Only
**Description:** Implement standard PunchOut protocol for catalog access from ERPs.

**Pros:**
- Industry standard protocol
- Works with most ERPs
- Catalog browsing from within ERP
- Shopping cart integration

**Cons:**
- Limited to catalog/cart scenarios
- No order status integration
- No automated workflows

### Option 2: Full Bidirectional Integration
**Description:** Deep integration with requisition push, order status, and inventory sync.

**Pros:**
- Complete workflow integration
- Automated requisition processing
- Real-time status visibility
- Inventory synchronization

**Cons:**
- High development effort per ERP
- Ongoing maintenance burden
- Requires ERP vendor cooperation

### Option 3: Integration Platform with Pre-Built Connectors
**Description:** Use integration platform (Celigo, Boomi) with pre-built ERP connectors.

**Pros:**
- Faster implementation
- Maintained connectors
- Multiple ERPs supported
- Visual workflow builder

**Cons:**
- Additional platform costs
- Platform dependency
- May not cover maritime-specific ERPs

### Option 4: Hybrid Approach
**Description:** PunchOut for broad compatibility, custom APIs for strategic ERP partnerships.

**Pros:**
- Broad compatibility via PunchOut
- Deep integration where valuable
- Focused development effort
- Progressive capability building

**Cons:**
- Two integration patterns to support
- Prioritization decisions needed

---

## Decision

**Chosen Option:** Hybrid Approach (PunchOut + Strategic Custom Integration)

We will implement PunchOut 2.0 catalog integration for broad ERP compatibility, with custom REST API integration for strategic ERP partnerships (AMOS, SERTICA).

### Rationale
PunchOut provides immediate broad compatibility while custom integration delivers differentiated value for key enterprise accounts. Starting with the two most common ERPs (AMOS, SERTICA) maximizes impact while managing development scope.

---

## Consequences

### Positive
- Broad ERP compatibility via PunchOut
- Deep integration for major ERPs
- Enterprise customer enablement
- Competitive differentiation
- Automated workflow support

### Negative
- Multiple integration patterns to maintain
- **Mitigation:** Clear abstraction layer, documented patterns
- Per-ERP development investment
- **Mitigation:** Focus on top 2-3 ERPs initially

### Risks
- ERP API changes: Version management, monitoring, relationships
- Integration complexity: Dedicated integration team, documentation
- Scope creep: Clear prioritization, customer-funded custom work

---

## Implementation Notes

### Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ERP Integration Layer                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   Integration Gateway                         │   │
│  │                                                               │   │
│  │   PunchOut Handler  │  cXML Processor  │  REST API Gateway   │   │
│  │                                                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                            │                                         │
│         ┌──────────────────┼──────────────────┐                     │
│         │                  │                  │                     │
│  ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐               │
│  │   PunchOut  │   │    AMOS     │   │  SERTICA    │               │
│  │   Adapter   │   │   Adapter   │   │   Adapter   │               │
│  │   (Generic) │   │   (Custom)  │   │   (Custom)  │               │
│  └─────────────┘   └─────────────┘   └─────────────┘               │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Core Platform APIs                         │   │
│  │                                                               │   │
│  │   Catalog API  │  Order API  │  Inventory API  │  User API   │   │
│  │                                                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### PunchOut Implementation

```typescript
// integration/punchout/punchout.service.ts
@Injectable()
export class PunchOutService {
  constructor(
    private readonly catalogService: CatalogService,
    private readonly cartService: CartService,
    private readonly sessionService: SessionService,
    private readonly authService: AuthService
  ) {}

  async handleSetupRequest(request: PunchOutSetupRequest): Promise<PunchOutSetupResponse> {
    // Validate buyer credentials
    const buyer = await this.authService.validatePunchOutCredentials(
      request.header.sender.credential
    );

    // Create PunchOut session
    const session = await this.sessionService.createPunchOutSession({
      buyerOrgId: buyer.organizationId,
      buyerCookie: request.body.buyerCookie,
      returnUrl: request.body.browserFormPost.url,
      operation: request.body.operation
    });

    // Generate catalog URL with session token
    const catalogUrl = this.generateCatalogUrl(session);

    return {
      header: {
        from: { identity: 'ship-chandlery-platform' },
        to: { identity: request.header.sender.credential.identity },
        sender: { credential: this.getPlatformCredential() }
      },
      response: {
        status: { code: '200', text: 'OK' },
        punchOutSetupResponse: {
          startPage: { url: catalogUrl }
        }
      }
    };
  }

  async handleOrderMessage(request: PunchOutOrderMessage): Promise<PunchOutOrderResponse> {
    const session = await this.sessionService.validateSession(
      request.header.sender.credential.sharedSecret
    );

    // Parse cXML order items
    const items = this.parseOrderItems(request.body.orderRequest);

    // Create order in platform
    const order = await this.orderService.createFromPunchOut({
      buyerOrgId: session.buyerOrgId,
      items,
      orderInfo: request.body.orderRequest.orderRequestHeader
    });

    return {
      header: this.createResponseHeader(request),
      response: {
        status: { code: '200', text: 'OK' },
        orderResponse: {
          orderId: order.orderNumber
        }
      }
    };
  }

  private parseOrderItems(orderRequest: any): PunchOutOrderItem[] {
    return orderRequest.itemOut.map(item => ({
      impaCode: item.itemID.supplierPartID,
      quantity: parseInt(item.quantity, 10),
      unitPrice: parseFloat(item.unitPrice.money.value),
      currency: item.unitPrice.money.currency,
      description: item.itemDetail.description.value
    }));
  }

  private generateCatalogUrl(session: PunchOutSession): string {
    return `${this.configService.get('PLATFORM_URL')}/punchout/catalog` +
      `?session=${session.token}` +
      `&org=${session.buyerOrgId}`;
  }
}
```

### AMOS Integration Adapter

```typescript
// integration/adapters/amos.adapter.ts
@Injectable()
export class AmosAdapter implements ErpAdapter {
  name = 'AMOS';

  constructor(
    private readonly httpService: HttpService,
    private readonly configService: ConfigService
  ) {}

  async pushRequisition(requisition: ExternalRequisition): Promise<string> {
    // AMOS uses proprietary XML format
    const amosRequest = this.mapToAmosFormat(requisition);

    const response = await this.httpService.post(
      `${this.getAmosEndpoint(requisition.clientId)}/api/purchase/requisition`,
      amosRequest,
      {
        headers: {
          'Content-Type': 'application/xml',
          'Authorization': `Bearer ${await this.getClientToken(requisition.clientId)}`
        }
      }
    ).toPromise();

    return response.data.requisitionId;
  }

  async receiveRequisition(
    amosRequisition: AmosRequisition
  ): Promise<CreateRfqInput> {
    // Map AMOS requisition to platform RFQ
    return {
      title: amosRequisition.description,
      vesselId: await this.mapVessel(amosRequisition.vesselCode),
      lineItems: amosRequisition.lines.map(line => ({
        impaCode: line.impaCode || this.lookupImpaCode(line.partNumber),
        productName: line.description,
        quantity: line.quantity,
        unit: this.mapUnit(line.unitOfMeasure),
        specifications: {
          amosPartNumber: line.partNumber,
          amosLineId: line.lineId
        }
      })),
      requestedDeliveryDate: new Date(amosRequisition.requiredDate),
      deliveryPort: amosRequisition.deliveryPort,
      externalReference: {
        system: 'AMOS',
        requisitionId: amosRequisition.requisitionId,
        vesselCode: amosRequisition.vesselCode
      }
    };
  }

  async pushOrderStatus(
    orderId: string,
    status: OrderStatusUpdate
  ): Promise<void> {
    const order = await this.orderRepository.findById(orderId);
    const externalRef = order.externalReference;

    if (externalRef?.system !== 'AMOS') {
      return;  // Not an AMOS order
    }

    const amosStatus = this.mapStatusToAmos(status);

    await this.httpService.post(
      `${this.getAmosEndpoint(order.clientId)}/api/purchase/orders/${externalRef.requisitionId}/status`,
      amosStatus,
      {
        headers: {
          'Content-Type': 'application/xml',
          'Authorization': `Bearer ${await this.getClientToken(order.clientId)}`
        }
      }
    ).toPromise();
  }

  async syncInventory(
    clientId: string,
    products: ProductInventory[]
  ): Promise<void> {
    const amosInventory = products.map(p => ({
      partNumber: p.supplierSku,
      impaCode: p.impaCode,
      availableQuantity: p.quantity,
      leadTimeDays: p.leadTime,
      lastUpdated: new Date().toISOString()
    }));

    await this.httpService.post(
      `${this.getAmosEndpoint(clientId)}/api/catalog/inventory`,
      { items: amosInventory },
      {
        headers: {
          'Authorization': `Bearer ${await this.getClientToken(clientId)}`
        }
      }
    ).toPromise();
  }

  private mapToAmosFormat(requisition: ExternalRequisition): string {
    // Generate AMOS-specific XML format
    return `<?xml version="1.0" encoding="UTF-8"?>
      <AMOSRequisition>
        <Header>
          <RequisitionId>${requisition.externalId}</RequisitionId>
          <VesselCode>${requisition.vesselCode}</VesselCode>
          <RequiredDate>${requisition.requestedDate}</RequiredDate>
        </Header>
        <Lines>
          ${requisition.items.map(item => `
            <Line>
              <PartNumber>${item.impaCode}</PartNumber>
              <Description>${item.productName}</Description>
              <Quantity>${item.quantity}</Quantity>
              <UOM>${item.unit}</UOM>
            </Line>
          `).join('')}
        </Lines>
      </AMOSRequisition>`;
  }
}
```

### SERTICA Integration Adapter

```typescript
// integration/adapters/sertica.adapter.ts
@Injectable()
export class SerticaAdapter implements ErpAdapter {
  name = 'SERTICA';

  constructor(
    private readonly httpService: HttpService,
    private readonly configService: ConfigService
  ) {}

  async receiveRequisition(
    webhook: SerticaWebhookPayload
  ): Promise<CreateRfqInput> {
    // SERTICA uses REST API with JSON
    const requisition = webhook.data;

    return {
      title: `${requisition.vessel.name} - ${requisition.category}`,
      vesselId: await this.mapVessel(requisition.vessel.imoNumber),
      lineItems: requisition.items.map(item => ({
        impaCode: item.impaCode,
        productName: item.description,
        quantity: item.quantity,
        unit: item.unit,
        specifications: {
          serticaItemId: item.id,
          maintenanceWorkOrderId: item.workOrderId
        }
      })),
      requestedDeliveryDate: new Date(requisition.requiredBy),
      deliveryPort: requisition.deliveryPort.locode,
      externalReference: {
        system: 'SERTICA',
        requisitionId: requisition.id,
        vesselImo: requisition.vessel.imoNumber
      }
    };
  }

  async pushOrderStatus(
    orderId: string,
    status: OrderStatusUpdate
  ): Promise<void> {
    const order = await this.orderRepository.findById(orderId);
    const externalRef = order.externalReference;

    if (externalRef?.system !== 'SERTICA') {
      return;
    }

    await this.httpService.put(
      `${this.getSerticaEndpoint(order.clientId)}/api/v2/requisitions/${externalRef.requisitionId}/status`,
      {
        status: this.mapStatusToSertica(status),
        updatedAt: new Date().toISOString(),
        details: {
          platformOrderId: order.orderNumber,
          fulfillmentStatus: status.fulfillmentStatus,
          trackingInfo: status.trackingInfo
        }
      },
      {
        headers: {
          'Authorization': `Bearer ${await this.getClientToken(order.clientId)}`,
          'Content-Type': 'application/json'
        }
      }
    ).toPromise();
  }

  // Webhook handler for SERTICA events
  async handleWebhook(payload: SerticaWebhookPayload): Promise<void> {
    switch (payload.event) {
      case 'requisition.created':
        await this.handleRequisitionCreated(payload);
        break;
      case 'requisition.updated':
        await this.handleRequisitionUpdated(payload);
        break;
      case 'requisition.cancelled':
        await this.handleRequisitionCancelled(payload);
        break;
    }
  }
}
```

### Integration Configuration

```typescript
// integration/config/erp-connections.config.ts
export interface ErpConnectionConfig {
  clientId: string;
  erpSystem: 'AMOS' | 'SERTICA' | 'SHIPNET' | 'NS5';
  enabled: boolean;

  // Connection details
  baseUrl: string;
  authType: 'OAUTH2' | 'API_KEY' | 'BASIC';
  credentials: {
    clientId?: string;
    clientSecret?: string;
    apiKey?: string;
    username?: string;
    password?: string;
  };

  // Feature flags
  features: {
    inboundRequisitions: boolean;
    outboundOrderStatus: boolean;
    inventorySync: boolean;
    punchOutCatalog: boolean;
  };

  // Mapping configuration
  mappings: {
    vesselCodeField: string;
    portCodeFormat: 'LOCODE' | 'CUSTOM';
    customPortMapping?: Record<string, string>;
  };
}
```

### Dependencies
- ADR-FN-011: RFQ Workflow State Machine
- ADR-FN-022: Order Lifecycle & Fulfillment
- ADR-NF-007: API Design Principles
- ADR-NF-015: Authentication Strategy

### Migration Strategy
1. Implement PunchOut 2.0 handler
2. Build AMOS adapter (highest priority)
3. Add SERTICA adapter
4. Create ERP connection management UI
5. Implement webhook handling
6. Build order status sync
7. Add inventory sync capability

---

## Operational Considerations

### Target ERP Systems and Integration Patterns

**Supported ERP Systems:**

| ERP System | Vendor | Market Share | Integration Priority | Pattern |
|------------|--------|--------------|---------------------|---------|
| AMOS | Kongsberg Maritime | ~35% | P1 - Launch | REST API + Custom |
| SERTICA | Logimatic | ~20% | P1 - Launch | REST API + Webhooks |
| ShipNet | Veson | ~15% | P2 - 6 months | REST API |
| NS5 (BASSnet) | BASS | ~10% | P2 - 6 months | SOAP + File |
| Danaos | Danaos Corporation | ~8% | P3 - 12 months | REST API |
| Generic PunchOut | Any cXML-compatible | ~12% | P1 - Launch | PunchOut 2.0 (cXML) |

**Integration Patterns by ERP:**

| ERP | Inbound (to Platform) | Outbound (from Platform) | Real-time Capability |
|-----|----------------------|-------------------------|---------------------|
| AMOS | REST API polling + File import | REST API push + Webhooks | Yes (API) |
| SERTICA | Webhooks (preferred) + REST polling | REST API push | Yes (Webhooks) |
| ShipNet | REST API polling | REST API push | Yes (API) |
| NS5 | SFTP file drop (XML) | SFTP file drop (XML) | No (batch) |
| Danaos | REST API | REST API | Yes (API) |
| PunchOut | cXML OrderMessage | cXML OrderResponse | Session-based |

```typescript
// Integration pattern configuration per ERP
interface ErpIntegrationProfile {
  erpType: ErpType;
  inboundMethods: InboundMethod[];
  outboundMethods: OutboundMethod[];
  dataFormats: DataFormat[];
  realTimeCapable: boolean;
  authMethods: AuthMethod[];
}

const ERP_PROFILES: Record<ErpType, ErpIntegrationProfile> = {
  AMOS: {
    erpType: 'AMOS',
    inboundMethods: ['REST_POLLING', 'FILE_IMPORT'],
    outboundMethods: ['REST_PUSH', 'WEBHOOK'],
    dataFormats: ['XML', 'JSON'],
    realTimeCapable: true,
    authMethods: ['OAUTH2', 'API_KEY']
  },
  SERTICA: {
    erpType: 'SERTICA',
    inboundMethods: ['WEBHOOK', 'REST_POLLING'],
    outboundMethods: ['REST_PUSH'],
    dataFormats: ['JSON'],
    realTimeCapable: true,
    authMethods: ['OAUTH2']
  },
  NS5: {
    erpType: 'NS5',
    inboundMethods: ['SFTP_FILE'],
    outboundMethods: ['SFTP_FILE'],
    dataFormats: ['XML'],
    realTimeCapable: false,
    authMethods: ['SSH_KEY', 'BASIC']
  },
  PUNCHOUT: {
    erpType: 'PUNCHOUT',
    inboundMethods: ['CXML'],
    outboundMethods: ['CXML'],
    dataFormats: ['CXML'],
    realTimeCapable: true,
    authMethods: ['SHARED_SECRET']
  }
};
```

### Schema Mapping Strategy

**Field Mapping Architecture:**

| Layer | Purpose | Storage | Flexibility |
|-------|---------|---------|-------------|
| Core Mapping | Standard fields common to all ERPs | Code (TypeScript interfaces) | Fixed |
| ERP-Specific | Fields unique to each ERP | Database (JSON config) | Configurable |
| Client Custom | Per-client field overrides | Database (JSON config) | Fully dynamic |

**Core Field Mappings (Requisition Inbound):**

| Platform Field | AMOS | SERTICA | NS5 | PunchOut |
|----------------|------|---------|-----|----------|
| `vesselId` | `vessel_code` | `vessel.imoNumber` | `VesselIMO` | `ShipTo/Address/@addressID` |
| `requestedDate` | `required_date` | `requiredBy` | `RequiredDate` | `RequestedDeliveryDate` |
| `deliveryPort` | `delivery_port` | `deliveryPort.locode` | `DeliveryPortCode` | `ShipTo/Address/City` |
| `lineItems[].impaCode` | `impa_code` | `impaCode` | `IMPACode` | `ItemID/SupplierPartID` |
| `lineItems[].quantity` | `qty` | `quantity` | `Quantity` | `@quantity` |
| `lineItems[].unit` | `uom` | `unit` | `UOM` | `UnitOfMeasure` |
| `externalRef` | `requisition_id` | `id` | `RequisitionNumber` | `BuyerCookie` |

```typescript
// Schema mapping configuration
interface FieldMapping {
  platformField: string;
  sourceField: string;           // JSONPath or XPath expression
  transform?: TransformFunction; // Optional transformation
  required: boolean;
  defaultValue?: any;
}

interface ErpSchemaMapping {
  erpType: ErpType;
  version: string;
  inbound: {
    requisition: FieldMapping[];
    orderStatus: FieldMapping[];
  };
  outbound: {
    order: FieldMapping[];
    statusUpdate: FieldMapping[];
    inventory: FieldMapping[];
  };
}

// Example AMOS mapping
const AMOS_SCHEMA_MAPPING: ErpSchemaMapping = {
  erpType: 'AMOS',
  version: '2.3',
  inbound: {
    requisition: [
      { platformField: 'vesselId', sourceField: '$.vessel_code', required: true, transform: 'VESSEL_CODE_TO_UUID' },
      { platformField: 'requestedDate', sourceField: '$.required_date', required: true, transform: 'ISO_DATE' },
      { platformField: 'deliveryPort', sourceField: '$.delivery_port', required: true },
      { platformField: 'lineItems', sourceField: '$.lines[*]', required: true, transform: 'MAP_LINE_ITEMS' },
      { platformField: 'externalRef.requisitionId', sourceField: '$.requisition_id', required: true }
    ],
    orderStatus: [
      { platformField: 'orderId', sourceField: '$.order_reference', required: true },
      { platformField: 'status', sourceField: '$.status_code', required: true, transform: 'AMOS_STATUS_TO_PLATFORM' }
    ]
  },
  outbound: {
    order: [
      { platformField: 'orderNumber', sourceField: 'OrderId', required: true },
      { platformField: 'status', sourceField: 'Status', required: true, transform: 'PLATFORM_STATUS_TO_AMOS' },
      { platformField: 'lineItems', sourceField: 'Lines', required: true, transform: 'MAP_ORDER_LINES' }
    ],
    statusUpdate: [
      { platformField: 'orderId', sourceField: 'OrderId', required: true },
      { platformField: 'status', sourceField: 'StatusCode', required: true },
      { platformField: 'timestamp', sourceField: 'UpdatedAt', required: true }
    ],
    inventory: [
      { platformField: 'impaCode', sourceField: 'PartNumber', required: true },
      { platformField: 'quantity', sourceField: 'AvailableQty', required: true },
      { platformField: 'leadTime', sourceField: 'LeadTimeDays', required: false, defaultValue: 14 }
    ]
  }
};
```

**Schema Mapping Service:**

```typescript
class SchemaMappingService {
  private readonly mappings: Map<string, ErpSchemaMapping>;

  async transform(
    data: any,
    erpType: ErpType,
    direction: 'inbound' | 'outbound',
    messageType: string,
    clientOverrides?: ClientFieldOverrides
  ): Promise<any> {
    const baseMapping = this.mappings.get(`${erpType}:${direction}:${messageType}`);
    const effectiveMapping = this.applyClientOverrides(baseMapping, clientOverrides);

    const result = {};
    for (const field of effectiveMapping) {
      const sourceValue = this.extractValue(data, field.sourceField);
      const transformedValue = field.transform
        ? await this.applyTransform(sourceValue, field.transform)
        : sourceValue;

      if (transformedValue === undefined && field.required) {
        throw new MappingError(`Required field ${field.platformField} not found in source`);
      }

      this.setNestedValue(result, field.platformField, transformedValue ?? field.defaultValue);
    }

    return result;
  }

  private applyClientOverrides(
    baseMapping: FieldMapping[],
    overrides?: ClientFieldOverrides
  ): FieldMapping[] {
    if (!overrides) return baseMapping;

    return baseMapping.map(field => {
      const override = overrides[field.platformField];
      if (override) {
        return { ...field, ...override };
      }
      return field;
    });
  }
}
```

### Versioning Strategy

**API Version Management:**

| Component | Versioning Scheme | Compatibility Policy |
|-----------|-------------------|---------------------|
| Platform Integration API | Semantic (v1.x.x) | Breaking changes = major version |
| ERP Adapter Schemas | Per-ERP version tracking | Maintain N-2 versions |
| Client Configurations | Timestamped snapshots | Rollback to any previous |

```sql
-- Schema version tracking
CREATE TABLE erp_schema_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    erp_type VARCHAR(20) NOT NULL,
    version VARCHAR(20) NOT NULL,
    schema_definition JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE',  -- ACTIVE, DEPRECATED, RETIRED
    deprecated_at TIMESTAMPTZ,
    sunset_date DATE,
    migration_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(erp_type, version)
);

-- Client-specific mapping overrides
CREATE TABLE client_erp_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES organizations(id),
    erp_type VARCHAR(20) NOT NULL,
    erp_schema_version VARCHAR(20) NOT NULL,
    custom_mappings JSONB DEFAULT '{}',
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(client_id, erp_type)
);

-- Configuration change audit
CREATE TABLE erp_config_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID,
    erp_type VARCHAR(20),
    change_type VARCHAR(20),  -- MAPPING_UPDATE, VERSION_CHANGE, ENABLE, DISABLE
    previous_config JSONB,
    new_config JSONB,
    changed_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Version Negotiation:**

```typescript
// Version negotiation for API calls
class ErpVersionNegotiator {
  async negotiateVersion(
    erpType: ErpType,
    clientRequestedVersion?: string
  ): Promise<string> {
    const supportedVersions = await this.getSupportedVersions(erpType);

    if (clientRequestedVersion) {
      if (supportedVersions.includes(clientRequestedVersion)) {
        return clientRequestedVersion;
      }
      // Find closest compatible version
      const compatible = this.findCompatibleVersion(clientRequestedVersion, supportedVersions);
      if (compatible) {
        this.logger.warn(`Client requested ${clientRequestedVersion}, using compatible ${compatible}`);
        return compatible;
      }
      throw new VersionNotSupportedError(erpType, clientRequestedVersion, supportedVersions);
    }

    // Return latest active version
    return supportedVersions[0];
  }

  private async getSupportedVersions(erpType: ErpType): Promise<string[]> {
    return this.db.query(`
      SELECT version FROM erp_schema_versions
      WHERE erp_type = $1 AND status IN ('ACTIVE', 'DEPRECATED')
      ORDER BY created_at DESC
    `, [erpType]).then(rows => rows.map(r => r.version));
  }
}
```

### Error Handling for Sync

**Error Categories and Handling:**

| Error Category | Examples | Handling Strategy | Retry |
|----------------|----------|-------------------|-------|
| Transient | Timeout, 503, network error | Exponential backoff retry | Yes (5x) |
| Rate Limit | 429, quota exceeded | Respect Retry-After header | Yes (delayed) |
| Authentication | 401, token expired | Refresh token, retry once | Yes (1x) |
| Validation | 400, schema mismatch | Log, alert, skip record | No |
| Not Found | 404, resource deleted | Log, mark as orphaned | No |
| Server Error | 500, unhandled exception | Alert, manual review | Yes (3x) |

```typescript
// Error handling middleware
class ErpSyncErrorHandler {
  private readonly errorStrategies: Map<ErrorCategory, ErrorStrategy> = new Map([
    ['TRANSIENT', { retry: true, maxAttempts: 5, backoff: 'exponential', alertThreshold: 3 }],
    ['RATE_LIMIT', { retry: true, maxAttempts: 10, backoff: 'retry-after', alertThreshold: 5 }],
    ['AUTH', { retry: true, maxAttempts: 2, backoff: 'none', refreshAuth: true }],
    ['VALIDATION', { retry: false, logLevel: 'WARN', alertThreshold: 10 }],
    ['NOT_FOUND', { retry: false, logLevel: 'INFO', markOrphaned: true }],
    ['SERVER', { retry: true, maxAttempts: 3, backoff: 'exponential', alertThreshold: 1 }]
  ]);

  async handleError(error: ErpSyncError, context: SyncContext): Promise<ErrorResolution> {
    const category = this.categorizeError(error);
    const strategy = this.errorStrategies.get(category);

    // Log with context
    this.logger.log(strategy.logLevel || 'ERROR', 'ERP sync error', {
      category,
      erpType: context.erpType,
      clientId: context.clientId,
      operation: context.operation,
      error: error.message,
      details: error.details
    });

    // Track for alerting
    await this.errorTracker.record(context, category);
    const errorCount = await this.errorTracker.getRecentCount(context, category);

    if (errorCount >= strategy.alertThreshold) {
      await this.alertService.alert({
        severity: category === 'SERVER' ? 'HIGH' : 'MEDIUM',
        message: `ERP sync errors for ${context.erpType}/${context.clientId}`,
        data: { category, count: errorCount, lastError: error.message }
      });
    }

    // Determine resolution
    if (strategy.retry && context.attemptCount < strategy.maxAttempts) {
      const delay = this.calculateDelay(strategy.backoff, context.attemptCount, error);
      return { action: 'RETRY', delayMs: delay };
    }

    if (strategy.markOrphaned) {
      await this.markAsOrphaned(context);
    }

    return { action: 'FAIL', reason: error.message };
  }

  private categorizeError(error: ErpSyncError): ErrorCategory {
    const status = error.httpStatus;

    if (!status || status === 408 || status === 503 || status === 504) return 'TRANSIENT';
    if (status === 429) return 'RATE_LIMIT';
    if (status === 401 || status === 403) return 'AUTH';
    if (status === 400 || status === 422) return 'VALIDATION';
    if (status === 404) return 'NOT_FOUND';
    if (status >= 500) return 'SERVER';

    return 'SERVER';  // Default to server for unknown errors
  }
}
```

**Sync State Management:**

```sql
-- Track sync state per entity per client
CREATE TABLE erp_sync_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES organizations(id),
    erp_type VARCHAR(20) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,  -- 'REQUISITION', 'ORDER', 'INVENTORY'
    entity_id UUID NOT NULL,           -- Platform entity ID
    external_id VARCHAR(100),          -- ERP's ID
    sync_direction VARCHAR(10) NOT NULL,  -- 'INBOUND', 'OUTBOUND'
    sync_status VARCHAR(20) NOT NULL,  -- 'PENDING', 'SYNCED', 'FAILED', 'ORPHANED'
    last_sync_at TIMESTAMPTZ,
    last_error TEXT,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(client_id, erp_type, entity_type, entity_id, sync_direction)
);

CREATE INDEX idx_sync_state_pending ON erp_sync_state(next_retry_at)
    WHERE sync_status = 'PENDING' OR sync_status = 'FAILED';
```

### Custom Field Mapping Support Model

**Self-Service Capabilities (Included):**

| Capability | Availability | Method |
|------------|--------------|--------|
| View current mappings | All enterprise clients | Admin portal |
| Add custom field (non-breaking) | All enterprise clients | Admin portal + validation |
| Modify field transform | Enterprise Pro tier | Admin portal |
| Test mapping changes | All enterprise clients | Sandbox environment |

**Professional Services (Billable):**

| Service | Scope | Typical Effort | Rate |
|---------|-------|----------------|------|
| New ERP Adapter | Full integration for unsupported ERP | 4-8 weeks | Project-based |
| Custom Transform | Complex transformation logic | 2-5 days | Time & materials |
| Schema Migration | Breaking changes to existing mapping | 1-2 weeks | Project-based |
| Integration Consulting | Architecture review, optimization | 1-3 days | Time & materials |

```typescript
// Self-service mapping management
@Controller('admin/erp-integrations/:erpType/mappings')
class ErpMappingAdminController {
  @Get()
  @Roles('ERP_ADMIN')
  async getMappings(@Param('erpType') erpType: string): Promise<ErpSchemaMapping> {
    return this.mappingService.getClientMappings(this.currentUser.organizationId, erpType);
  }

  @Post('custom-fields')
  @Roles('ERP_ADMIN')
  async addCustomField(
    @Param('erpType') erpType: string,
    @Body() field: CustomFieldInput
  ): Promise<CustomFieldResult> {
    // Validate the custom field won't break existing sync
    const validation = await this.mappingService.validateCustomField(
      this.currentUser.organizationId,
      erpType,
      field
    );

    if (!validation.valid) {
      throw new BadRequestException(validation.errors);
    }

    // Apply to sandbox first
    await this.mappingService.applyToSandbox(
      this.currentUser.organizationId,
      erpType,
      field
    );

    return {
      fieldId: field.platformField,
      status: 'APPLIED_TO_SANDBOX',
      testUrl: this.generateSandboxTestUrl(erpType)
    };
  }

  @Post('custom-fields/:fieldId/promote')
  @Roles('ERP_ADMIN')
  async promoteCustomField(
    @Param('erpType') erpType: string,
    @Param('fieldId') fieldId: string
  ): Promise<void> {
    // Verify sandbox testing was successful
    const sandboxResults = await this.mappingService.getSandboxTestResults(
      this.currentUser.organizationId,
      erpType,
      fieldId
    );

    if (!sandboxResults.allPassed) {
      throw new BadRequestException('Sandbox tests must pass before promoting to production');
    }

    // Promote to production with audit trail
    await this.mappingService.promoteToProduction(
      this.currentUser.organizationId,
      erpType,
      fieldId,
      this.currentUser.id
    );
  }
}
```

### Open Questions (Resolved)

- **Q:** What is the support model for custom ERP field mappings?
  - **A:** A tiered support model balances self-service flexibility with professional services for complex requirements:

    **Self-Service (Included with Enterprise tier):**
    - View and understand current field mappings via admin portal
    - Add non-breaking custom fields through guided UI workflow
    - Test all mapping changes in isolated sandbox environment before production
    - Rollback to previous mapping configurations

    **Professional Services (Billable):**
    - New ERP adapter development for unsupported systems (4-8 week projects)
    - Custom transformation logic for complex data manipulation
    - Schema migration support for breaking changes
    - Integration architecture consulting

    All custom mappings follow a sandbox-first deployment model: changes are validated and tested in a sandbox environment before promotion to production, with full audit trail of who made changes and when. The platform maintains N-2 version compatibility for ERP schemas, allowing gradual migrations without forcing immediate client updates.

---

## References
- [cXML PunchOut Specification](http://cxml.org/)
- [AMOS Technical Documentation](https://www.kongsberg.com/maritime/products/vessel-and-fleet-performance-optimisation/amos/)
- [OCI (Open Catalog Interface)](https://help.sap.com/docs/ARIBA_P2P)
- [Source2Sea RINA Integration](https://www.rina.org/en/digital-solutions)
