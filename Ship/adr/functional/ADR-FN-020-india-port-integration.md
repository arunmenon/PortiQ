# ADR-FN-020: India Port Integration (PCS1x)

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

India's Port Community System (PCS1x) provides free access to vessel movement data across all 12 major ports, offering authoritative government data for maritime logistics operations.

### Business Context
India handles 95% of trade volume through maritime transport, with 12 major ports and 200+ minor ports. PCS1x, launched by the Indian Ports Association (IPA) in 2018, creates a unified digital ecosystem connecting all port stakeholders. For a chandlery platform targeting Indian ports, PCS1x integration provides:
- Free vessel arrival/departure data
- Official berth allocation information
- Customs and cargo clearance status
- Integration with Sagarmala Logistics Data Bank

### Technical Context
- PCS1x is API-based architecture
- Each major port has varying levels of API maturity
- Mumbai Port Trust was first to implement full API integration
- VTMS (Vessel Traffic Management System) integration at key ports
- Authentication requires stakeholder registration with port authorities

### Assumptions
- Platform can register as authorized stakeholder
- API access granted to registered chandlers/suppliers
- Data freshness sufficient for logistics planning
- Coverage expands as ports digitize

---

## Decision Drivers

- Free access to vessel movement data
- Official, authoritative government source
- Coverage of all major Indian ports
- API maturity and reliability
- Integration with broader port operations
- Complement to commercial AIS providers

---

## Considered Options

### Option 1: Full PCS1x Integration
**Description:** Direct integration with PCS1x APIs for all available data.

**Pros:**
- Free government data
- Authoritative source
- VTMS integration
- Port-specific details
- Berth allocation data

**Cons:**
- API maturity varies by port
- Registration process required
- Limited to India
- Documentation gaps

### Option 2: Selective Port Integration
**Description:** Integrate only with ports having mature APIs (Mumbai, Cochin, JNPT).

**Pros:**
- Focus on reliable integrations
- Lower maintenance burden
- Key ports covered
- Faster implementation

**Cons:**
- Incomplete coverage
- May miss smaller ports
- Inconsistent experience

### Option 3: Sagarmala Logistics Data Bank Only
**Description:** Use higher-level Sagarmala LDB for container tracking.

**Pros:**
- Unified interface
- RFID-based tracking
- End-to-end visibility

**Cons:**
- Container-focused, not vessel
- Less real-time data
- Limited to EXIM cargo

---

## Decision

**Chosen Option:** Full PCS1x Integration with Graceful Degradation

We will implement comprehensive PCS1x integration across all supported ports, with graceful degradation for ports with immature APIs, falling back to VesselFinder data.

### Rationale
Free, authoritative government data is invaluable for Indian port operations. While API maturity varies, the cost-benefit strongly favors full integration. Graceful degradation ensures consistent user experience regardless of per-port API capabilities.

---

## Consequences

### Positive
- Free vessel movement data for all major Indian ports
- Official berth allocation information
- Integration with customs/cargo systems
- No per-query costs for Indian operations

### Negative
- Variable API quality across ports
- **Mitigation:** Per-port adapters, graceful degradation
- Registration and compliance overhead
- **Mitigation:** Complete registration during onboarding phase

### Risks
- API downtime at specific ports: Fallback to VesselFinder
- Authentication issues: Token refresh, monitoring
- Data format changes: Version detection, adapter updates

---

## Implementation Notes

### PCS1x Port Coverage

```typescript
// pcs1x/config/ports.config.ts
export interface PortConfig {
  code: string;
  name: string;
  apiMaturity: 'FULL' | 'PARTIAL' | 'BASIC';
  baseUrl: string;
  features: PortFeature[];
  vtmsEnabled: boolean;
}

export enum PortFeature {
  VESSEL_ARRIVALS = 'VESSEL_ARRIVALS',
  VESSEL_DEPARTURES = 'VESSEL_DEPARTURES',
  BERTH_ALLOCATION = 'BERTH_ALLOCATION',
  CARGO_MANIFEST = 'CARGO_MANIFEST',
  CUSTOMS_STATUS = 'CUSTOMS_STATUS',
  PILOT_BOOKING = 'PILOT_BOOKING'
}

export const INDIAN_PORTS: PortConfig[] = [
  {
    code: 'INBOM',
    name: 'Mumbai Port (BPT)',
    apiMaturity: 'FULL',
    baseUrl: 'https://pcs.mumbaiport.gov.in/api',
    features: [
      PortFeature.VESSEL_ARRIVALS,
      PortFeature.VESSEL_DEPARTURES,
      PortFeature.BERTH_ALLOCATION,
      PortFeature.CARGO_MANIFEST
    ],
    vtmsEnabled: true
  },
  {
    code: 'INNSA',
    name: 'Jawaharlal Nehru Port (JNPT)',
    apiMaturity: 'FULL',
    baseUrl: 'https://pcs.jnport.gov.in/api',
    features: [
      PortFeature.VESSEL_ARRIVALS,
      PortFeature.VESSEL_DEPARTURES,
      PortFeature.BERTH_ALLOCATION,
      PortFeature.CARGO_MANIFEST,
      PortFeature.CUSTOMS_STATUS
    ],
    vtmsEnabled: true
  },
  {
    code: 'INCOK',
    name: 'Cochin Port',
    apiMaturity: 'FULL',
    baseUrl: 'https://pcs.cochinport.gov.in/api',
    features: [
      PortFeature.VESSEL_ARRIVALS,
      PortFeature.VESSEL_DEPARTURES,
      PortFeature.BERTH_ALLOCATION
    ],
    vtmsEnabled: true
  },
  {
    code: 'INMAA',
    name: 'Chennai Port',
    apiMaturity: 'PARTIAL',
    baseUrl: 'https://pcs.chennaiport.gov.in/api',
    features: [
      PortFeature.VESSEL_ARRIVALS,
      PortFeature.VESSEL_DEPARTURES
    ],
    vtmsEnabled: false
  },
  {
    code: 'INVIS',
    name: 'Visakhapatnam Port',
    apiMaturity: 'PARTIAL',
    baseUrl: 'https://pcs.vizagport.gov.in/api',
    features: [
      PortFeature.VESSEL_ARRIVALS,
      PortFeature.VESSEL_DEPARTURES
    ],
    vtmsEnabled: false
  },
  {
    code: 'INKOL',
    name: 'Kolkata Port',
    apiMaturity: 'PARTIAL',
    baseUrl: 'https://pcs.kolkataporttrust.gov.in/api',
    features: [
      PortFeature.VESSEL_ARRIVALS,
      PortFeature.VESSEL_DEPARTURES
    ],
    vtmsEnabled: false
  },
  {
    code: 'INMUN',
    name: 'Mundra Port',
    apiMaturity: 'FULL',
    baseUrl: 'https://pcs.adaniports.com/api',
    features: [
      PortFeature.VESSEL_ARRIVALS,
      PortFeature.VESSEL_DEPARTURES,
      PortFeature.BERTH_ALLOCATION
    ],
    vtmsEnabled: true
  },
  // Additional ports...
];
```

### PCS1x Service

```typescript
// pcs1x/services/pcs1x.service.ts
@Injectable()
export class Pcs1xService {
  private portClients: Map<string, Pcs1xPortClient>;

  constructor(
    private readonly authService: Pcs1xAuthService,
    private readonly cacheService: CacheService
  ) {
    this.initializePortClients();
  }

  private initializePortClients(): void {
    this.portClients = new Map();

    for (const port of INDIAN_PORTS) {
      this.portClients.set(port.code, new Pcs1xPortClient(port, this.authService));
    }
  }

  async getVesselArrivals(
    portCode: string,
    options: ArrivalQueryOptions = {}
  ): Promise<VesselArrival[]> {
    const client = this.portClients.get(portCode);

    if (!client) {
      throw new Error(`Port ${portCode} not configured`);
    }

    const cacheKey = `pcs1x:arrivals:${portCode}:${options.hoursAhead ?? 48}`;
    const cached = await this.cacheService.get<VesselArrival[]>(cacheKey);

    if (cached) return cached;

    const arrivals = await client.getVesselArrivals(options);

    await this.cacheService.set(cacheKey, arrivals, 300);  // 5 min cache

    return arrivals;
  }

  async getVesselDetails(
    portCode: string,
    vesselId: string
  ): Promise<VesselDetails> {
    const client = this.portClients.get(portCode);
    return client.getVesselDetails(vesselId);
  }

  async getBerthAllocation(
    portCode: string,
    vesselId: string
  ): Promise<BerthAllocation | null> {
    const client = this.portClients.get(portCode);
    const port = INDIAN_PORTS.find(p => p.code === portCode);

    if (!port.features.includes(PortFeature.BERTH_ALLOCATION)) {
      return null;
    }

    return client.getBerthAllocation(vesselId);
  }

  async searchVessels(query: VesselSearchQuery): Promise<VesselInfo[]> {
    const results: VesselInfo[] = [];

    // Search across all configured ports
    const searchPromises = Array.from(this.portClients.entries()).map(
      async ([portCode, client]) => {
        try {
          const vessels = await client.searchVessels(query);
          return vessels.map(v => ({ ...v, portCode }));
        } catch (error) {
          logger.warn(`Search failed for port ${portCode}`, error);
          return [];
        }
      }
    );

    const portResults = await Promise.all(searchPromises);
    return portResults.flat();
  }

  getPortCapabilities(portCode: string): PortConfig | undefined {
    return INDIAN_PORTS.find(p => p.code === portCode);
  }
}
```

### Port Client Implementation

```typescript
// pcs1x/clients/pcs1x-port.client.ts
export class Pcs1xPortClient {
  private token: string;
  private tokenExpiry: Date;

  constructor(
    private readonly portConfig: PortConfig,
    private readonly authService: Pcs1xAuthService
  ) {}

  async getVesselArrivals(options: ArrivalQueryOptions): Promise<VesselArrival[]> {
    await this.ensureAuthenticated();

    const response = await fetch(
      `${this.portConfig.baseUrl}/v1/vessels/arrivals?` +
      new URLSearchParams({
        hours_ahead: (options.hoursAhead ?? 48).toString(),
        vessel_type: options.vesselType ?? 'ALL'
      }),
      {
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'X-Port-Code': this.portConfig.code
        }
      }
    );

    if (!response.ok) {
      throw new Pcs1xApiError(
        `Failed to fetch arrivals: ${response.status}`,
        this.portConfig.code
      );
    }

    const data = await response.json();
    return this.mapArrivalsResponse(data);
  }

  async getVesselDetails(vesselId: string): Promise<VesselDetails> {
    await this.ensureAuthenticated();

    const response = await fetch(
      `${this.portConfig.baseUrl}/v1/vessels/${vesselId}`,
      {
        headers: { 'Authorization': `Bearer ${this.token}` }
      }
    );

    const data = await response.json();

    return {
      imoNumber: data.imo_number,
      name: data.vessel_name,
      flag: data.flag_country,
      vesselType: data.vessel_type,
      grossTonnage: data.gross_tonnage,
      deadweight: data.deadweight,
      length: data.length_overall,
      beam: data.beam,
      draft: data.max_draft,
      yearBuilt: data.year_built,
      owner: data.owner_name,
      manager: data.manager_name,
      callSign: data.call_sign,
      lastPort: data.last_port,
      nextPort: data.next_port
    };
  }

  async getBerthAllocation(vesselId: string): Promise<BerthAllocation> {
    await this.ensureAuthenticated();

    const response = await fetch(
      `${this.portConfig.baseUrl}/v1/berths/allocation/${vesselId}`,
      {
        headers: { 'Authorization': `Bearer ${this.token}` }
      }
    );

    const data = await response.json();

    return {
      vesselId,
      berthNumber: data.berth_number,
      berthName: data.berth_name,
      allocatedFrom: new Date(data.allocated_from),
      allocatedTo: new Date(data.allocated_to),
      status: data.status,
      pilotRequired: data.pilot_required,
      pilotBookingId: data.pilot_booking_id
    };
  }

  private async ensureAuthenticated(): Promise<void> {
    if (this.token && this.tokenExpiry > new Date()) {
      return;
    }

    const authResult = await this.authService.authenticate(this.portConfig.code);
    this.token = authResult.token;
    this.tokenExpiry = authResult.expiry;
  }

  private mapArrivalsResponse(data: any): VesselArrival[] {
    return data.vessels.map(v => ({
      imoNumber: v.imo_number,
      vesselName: v.vessel_name,
      eta: new Date(v.expected_arrival),
      etd: v.expected_departure ? new Date(v.expected_departure) : null,
      lastPort: v.last_port_of_call,
      nextPort: v.next_port_of_call,
      agent: v.shipping_agent,
      cargoType: v.cargo_type,
      berthRequested: v.berth_requested,
      status: this.mapStatus(v.status),
      vtmsTracked: v.vtms_tracked ?? false
    }));
  }
}
```

### Authentication Service

```typescript
// pcs1x/services/pcs1x-auth.service.ts
@Injectable()
export class Pcs1xAuthService {
  private credentials: Map<string, PortCredentials>;

  constructor(private readonly configService: ConfigService) {
    this.loadCredentials();
  }

  async authenticate(portCode: string): Promise<AuthResult> {
    const creds = this.credentials.get(portCode);

    if (!creds) {
      throw new Error(`No credentials configured for port ${portCode}`);
    }

    const port = INDIAN_PORTS.find(p => p.code === portCode);

    const response = await fetch(
      `${port.baseUrl}/auth/token`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: creds.clientId,
          client_secret: creds.clientSecret,
          grant_type: 'client_credentials',
          scope: 'vessel.read berth.read'
        })
      }
    );

    const data = await response.json();

    return {
      token: data.access_token,
      expiry: new Date(Date.now() + data.expires_in * 1000)
    };
  }

  private loadCredentials(): void {
    this.credentials = new Map();

    // Load from config/environment
    for (const port of INDIAN_PORTS) {
      const clientId = this.configService.get(`PCS1X_${port.code}_CLIENT_ID`);
      const clientSecret = this.configService.get(`PCS1X_${port.code}_CLIENT_SECRET`);

      if (clientId && clientSecret) {
        this.credentials.set(port.code, { clientId, clientSecret });
      }
    }
  }
}
```

### Event Integration

```typescript
// pcs1x/handlers/pcs1x-event.handler.ts
@Injectable()
export class Pcs1xEventHandler {
  constructor(
    private readonly pcs1xService: Pcs1xService,
    private readonly eventEmitter: EventEmitter2,
    private readonly subscriptionService: VesselSubscriptionService
  ) {}

  @Cron('*/30 * * * *')  // Every 30 minutes
  async pollPortArrivals(): Promise<void> {
    for (const port of INDIAN_PORTS) {
      try {
        const arrivals = await this.pcs1xService.getVesselArrivals(port.code, {
          hoursAhead: 72
        });

        // Check against subscribed vessels
        const subscriptions = await this.subscriptionService.getForPort(port.code);

        for (const arrival of arrivals) {
          const subscription = subscriptions.find(
            s => s.vesselImo === arrival.imoNumber
          );

          if (subscription) {
            // Emit arrival event
            this.eventEmitter.emit('vessel.arrival.pcs1x', {
              subscription,
              arrival,
              port
            });
          }
        }
      } catch (error) {
        logger.error(`Failed to poll arrivals for port ${port.code}`, error);
      }
    }
  }

  @OnEvent('vessel.arrival.pcs1x')
  async handleArrivalDetected(event: ArrivalDetectedEvent): Promise<void> {
    const { subscription, arrival, port } = event;

    // Get berth allocation if available
    let berthAllocation = null;
    if (port.features.includes(PortFeature.BERTH_ALLOCATION)) {
      berthAllocation = await this.pcs1xService.getBerthAllocation(
        port.code,
        arrival.imoNumber
      );
    }

    // Notify subscriber
    await this.notificationService.notify(subscription.organizationId, {
      type: 'VESSEL_ARRIVAL_DETECTED',
      vesselName: arrival.vesselName,
      portName: port.name,
      eta: arrival.eta,
      berthAllocation
    });

    // Trigger supply preparation workflow if configured
    if (subscription.autoTriggerRfq) {
      this.eventEmitter.emit('supply.preparation.trigger', {
        subscription,
        arrival,
        port
      });
    }
  }
}
```

### Dependencies
- ADR-FN-019: AIS Data Integration
- ADR-FN-021: Predictive Supply ML Model

### Migration Strategy
1. Apply for PCS1x stakeholder registration
2. Complete port-by-port onboarding
3. Implement authentication service
4. Build port clients for mature ports (Mumbai, JNPT, Cochin)
5. Add remaining ports progressively
6. Implement caching and fallback mechanisms
7. Create monitoring dashboard for port API health

---

## Operational Considerations

### PCS1x Scope Definition

The integration covers the following PCS1x functional areas and data elements:

| Module | Data Elements | Access Level | Business Value |
|--------|---------------|--------------|----------------|
| Vessel Traffic | Arrivals, departures, ETA/ETD | Read | Pre-order logistics planning |
| Berth Management | Berth allocation, timestamps | Read | Delivery timing optimization |
| Cargo Manifest | Manifest status, container count | Read (limited) | Vessel supply estimation |
| Customs Status | Clearance status, holds | Read | Delivery feasibility checks |
| Agent Directory | Shipping agents, contacts | Read | Agent coordination |
| VTMS Data | Real-time position (where available) | Read | Last-mile delivery tracking |

**Out of Scope (Phase 1):**

| Module | Reason |
|--------|--------|
| Pilot Booking | Not required for chandlery operations |
| Container Tracking | Sagarmala LDB better suited |
| Customs Filing | Outside platform scope |
| Invoice/Payment | Handled by port directly |

### Mandatory Compliance Steps

Registration and ongoing compliance requirements for PCS1x integration:

**Initial Registration Process:**

| Step | Owner | Timeline | Documentation Required |
|------|-------|----------|------------------------|
| 1. Stakeholder Application | Platform ops | Week 1 | Business registration, PAN, GST |
| 2. IPA Verification | Indian Ports Association | 2-4 weeks | Verified by IPA regional office |
| 3. Digital Signature | Platform ops | Week 2 | Class 3 DSC from licensed CA |
| 4. API Credentials | IPA Tech Team | 1-2 weeks | Per-port client_id/secret issued |
| 5. UAT Integration | Engineering | 2-4 weeks | Test against staging environment |
| 6. Production Go-Live | IPA + Platform | 1 week | Security audit sign-off |

**Ongoing Compliance:**

| Requirement | Frequency | Owner | Consequence of Non-Compliance |
|-------------|-----------|-------|-------------------------------|
| DSC Renewal | Annual | Platform ops | API access revoked |
| Security Audit | Annual | Engineering | Access suspended |
| Data Retention | Continuous | Platform | Audit failure, legal exposure |
| Usage Reporting | Quarterly | Platform ops | Registration review |
| Incident Reporting | As needed | Platform ops | Required within 24 hours |

```typescript
// Compliance tracking configuration
const COMPLIANCE_CONFIG = {
  dataRetention: {
    vesselData: 90,      // days - per MeitY guidelines
    berthAllocation: 180, // days
    auditLogs: 365       // days - 1 year minimum
  },
  reporting: {
    usageReportCron: '0 0 1 */3 *',  // First day of each quarter
    incidentNotificationEmail: 'pcs1x-support@indianpcs.gov.in'
  },
  certExpiry: {
    dscExpiryWarningDays: 30,
    apiCredentialRotationDays: 365
  }
};
```

### Update Cadence

| Data Type | Poll Frequency | Cache TTL | Rationale |
|-----------|----------------|-----------|-----------|
| Vessel Arrivals (48h window) | 30 minutes | 5 minutes | Balance freshness vs API load |
| Vessel Arrivals (7d window) | 2 hours | 30 minutes | Planning data, less volatile |
| Berth Allocation | 15 minutes | 2 minutes | Time-sensitive for delivery |
| Vessel Details | On-demand | 24 hours | Static data, rarely changes |
| Port Status | 5 minutes | 1 minute | Operational awareness |
| VTMS Position (if available) | 5 minutes | 30 seconds | Real-time tracking |

```typescript
// Polling scheduler configuration
const POLL_SCHEDULES = {
  'arrivals-48h': {
    cron: '*/30 * * * *',      // Every 30 minutes
    ports: ['INBOM', 'INNSA', 'INCOK', 'INMUN'],  // Full API maturity ports
    params: { hoursAhead: 48 }
  },
  'arrivals-7d': {
    cron: '0 */2 * * *',       // Every 2 hours
    ports: 'ALL',
    params: { hoursAhead: 168 }
  },
  'berth-allocation': {
    cron: '*/15 * * * *',      // Every 15 minutes
    ports: ['INBOM', 'INNSA', 'INCOK'],  // Ports with berth API
    params: {}
  },
  'port-status': {
    cron: '*/5 * * * *',       // Every 5 minutes
    ports: 'ALL',
    params: {}
  }
};
```

### Retry and Backoff Strategy

**Retry Configuration:**

| Error Type | Initial Delay | Max Retries | Backoff | Final Action |
|------------|---------------|-------------|---------|--------------|
| Network timeout | 5 seconds | 5 | Exponential (2x) | Fallback to VesselFinder |
| HTTP 429 (Rate limit) | 60 seconds | 3 | Linear (+60s) | Skip this poll cycle |
| HTTP 500 (Server error) | 30 seconds | 5 | Exponential (2x) | Alert + fallback |
| HTTP 401 (Auth error) | Immediate | 1 | None | Token refresh, then retry |
| HTTP 503 (Maintenance) | 5 minutes | 12 | Fixed (5 min) | Wait for service |

```typescript
// Retry policy implementation
class Pcs1xRetryPolicy {
  private readonly policies: Record<number, RetryConfig> = {
    408: { initialDelay: 5000, maxRetries: 5, backoff: 'exponential', factor: 2 },
    429: { initialDelay: 60000, maxRetries: 3, backoff: 'linear', increment: 60000 },
    500: { initialDelay: 30000, maxRetries: 5, backoff: 'exponential', factor: 2 },
    503: { initialDelay: 300000, maxRetries: 12, backoff: 'fixed' }
  };

  async executeWithRetry<T>(
    operation: () => Promise<T>,
    portCode: string
  ): Promise<T> {
    let lastError: Error;
    let attempt = 0;

    while (attempt <= this.getMaxRetries()) {
      try {
        return await operation();
      } catch (error) {
        lastError = error;
        const statusCode = error.response?.status || 0;
        const policy = this.policies[statusCode];

        if (!policy || attempt >= policy.maxRetries) {
          // Trigger fallback
          await this.triggerFallback(portCode, error);
          throw error;
        }

        const delay = this.calculateDelay(policy, attempt);
        this.metrics.recordRetry(portCode, statusCode, attempt);

        await this.sleep(delay);
        attempt++;
      }
    }

    throw lastError;
  }

  private calculateDelay(policy: RetryConfig, attempt: number): number {
    switch (policy.backoff) {
      case 'exponential':
        return policy.initialDelay * Math.pow(policy.factor, attempt);
      case 'linear':
        return policy.initialDelay + (policy.increment * attempt);
      case 'fixed':
        return policy.initialDelay;
      default:
        return policy.initialDelay;
    }
  }
}
```

### Manual Fallback for Outages

When PCS1x is unavailable, the system implements a tiered fallback strategy:

| Fallback Tier | Trigger | Data Source | Data Quality |
|---------------|---------|-------------|--------------|
| Tier 1: Cache | API latency > 10s | Redis cache | Last successful poll |
| Tier 2: VesselFinder | Cache miss + API down | VesselFinder API | Real-time, less detail |
| Tier 3: Manual Entry | Both automated sources down | Admin portal | Operator-provided |

```typescript
// Fallback chain implementation
class VesselDataService {
  async getVesselArrivals(portCode: string): Promise<VesselArrival[]> {
    // Tier 1: Try PCS1x with cache fallback
    try {
      const cached = await this.cache.get(`pcs1x:arrivals:${portCode}`);
      if (cached && this.isFresh(cached, 300)) {
        return cached.data;
      }

      const fresh = await this.pcs1xService.getVesselArrivals(portCode);
      await this.cache.set(`pcs1x:arrivals:${portCode}`, fresh, 3600);
      return fresh;
    } catch (pcs1xError) {
      this.logger.warn(`PCS1x unavailable for ${portCode}`, pcs1xError);

      // Tier 2: VesselFinder fallback
      try {
        const vfData = await this.vesselFinderService.getPortArrivals(portCode);
        await this.metrics.recordFallback(portCode, 'VESSELFINDER');
        return this.mapVesselFinderToStandard(vfData);
      } catch (vfError) {
        this.logger.error(`VesselFinder also unavailable for ${portCode}`, vfError);

        // Tier 3: Return cached data even if stale, or empty
        const staleCached = await this.cache.get(`pcs1x:arrivals:${portCode}`);
        if (staleCached) {
          await this.metrics.recordFallback(portCode, 'STALE_CACHE');
          return staleCached.data;
        }

        // Tier 4: Alert for manual intervention
        await this.alertService.critical({
          message: `No vessel data available for ${portCode}`,
          action: 'MANUAL_ENTRY_REQUIRED'
        });
        return [];
      }
    }
  }
}

// Manual entry API for operators
@Controller('admin/ports/:portCode/arrivals')
class ManualArrivalController {
  @Post()
  @Roles('PORT_OPERATOR', 'ADMIN')
  async createManualArrival(
    @Param('portCode') portCode: string,
    @Body() arrival: ManualArrivalInput
  ): Promise<VesselArrival> {
    const created = await this.arrivalService.createManual({
      ...arrival,
      portCode,
      source: 'MANUAL',
      createdBy: this.currentUser.id
    });

    // Flag for verification when PCS1x resumes
    await this.reconciliationQueue.add('verify-manual', {
      arrivalId: created.id,
      portCode
    });

    return created;
  }
}
```

### Outage Communication and Monitoring

| Monitoring Aspect | Method | Threshold | Alert Channel |
|-------------------|--------|-----------|---------------|
| API availability | Health check ping | 3 consecutive failures | PagerDuty |
| Response latency | P95 tracking | > 5 seconds | Slack |
| Error rate | Rolling 5-minute window | > 10% errors | Slack + PagerDuty |
| Data freshness | Last successful sync | > 2 hours stale | Slack |
| Token expiry | Days until expiry | < 7 days | Email to ops |

```typescript
// Port health monitoring
@Injectable()
class Pcs1xHealthMonitor {
  @Cron('*/1 * * * *')  // Every minute
  async checkPortHealth(): Promise<void> {
    for (const port of INDIAN_PORTS) {
      const health = await this.checkSinglePort(port.code);

      await this.metrics.gauge('pcs1x_port_health', {
        port: port.code,
        status: health.status
      });

      if (health.status === 'DOWN' && health.consecutiveFailures >= 3) {
        await this.alertService.alert({
          severity: 'HIGH',
          message: `PCS1x ${port.name} API is DOWN`,
          data: {
            lastSuccessful: health.lastSuccessfulPoll,
            consecutiveFailures: health.consecutiveFailures,
            lastError: health.lastError
          }
        });

        // Auto-enable VesselFinder fallback
        await this.fallbackService.enableForPort(port.code);
      }
    }
  }

  private async checkSinglePort(portCode: string): Promise<PortHealthStatus> {
    const start = Date.now();
    try {
      await this.pcs1xService.healthCheck(portCode);
      const latency = Date.now() - start;

      return {
        status: latency > 5000 ? 'DEGRADED' : 'UP',
        latency,
        consecutiveFailures: 0,
        lastSuccessfulPoll: new Date()
      };
    } catch (error) {
      const failures = await this.incrementFailureCount(portCode);
      return {
        status: 'DOWN',
        latency: Date.now() - start,
        consecutiveFailures: failures,
        lastError: error.message
      };
    }
  }
}
```

### PCS1x SLA Expectations

Based on IPA documentation and operational experience:

| Metric | Published SLA | Observed Reality | Platform Handling |
|--------|---------------|------------------|-------------------|
| Availability | 99.5% | ~98% (varies by port) | Fallback strategy |
| Response Time | < 3 seconds | 1-5 seconds typical | 10-second timeout |
| Scheduled Maintenance | Sundays 02:00-06:00 IST | Adhered | Skip polling window |
| Unplanned Outages | 4-hour resolution target | 2-12 hours observed | Fallback + alerts |
| Data Freshness | Real-time | 5-30 minute lag | Acceptable for planning |

**Outage Communication Channels:**

| Channel | What to Expect | Platform Action |
|---------|----------------|-----------------|
| PCS1x Portal Banner | Scheduled maintenance announcements | Auto-parse, pause polling |
| Email to registered contacts | Unplanned outage notifications | Forward to ops Slack |
| No notification | Frequent for minor outages | Rely on health monitoring |

```typescript
// Maintenance window handling
const MAINTENANCE_WINDOWS = {
  scheduled: {
    dayOfWeek: 0,  // Sunday
    startHourIST: 2,
    endHourIST: 6
  }
};

function isMaintenanceWindow(): boolean {
  const now = new Date();
  const istOffset = 5.5 * 60;  // IST is UTC+5:30
  const istHour = (now.getUTCHours() + (istOffset / 60)) % 24;
  const istDay = now.getUTCDay();

  return istDay === MAINTENANCE_WINDOWS.scheduled.dayOfWeek &&
         istHour >= MAINTENANCE_WINDOWS.scheduled.startHourIST &&
         istHour < MAINTENANCE_WINDOWS.scheduled.endHourIST;
}
```

### Open Questions (Resolved)

- **Q:** What SLAs does PCS1x provide, and how will outages be communicated?
  - **A:** PCS1x publishes a 99.5% availability SLA with < 3 second response times, though operational experience shows ~98% availability with response times of 1-5 seconds. Outage communications are inconsistent:
    - **Scheduled maintenance**: Announced via portal banner and email, typically Sundays 02:00-06:00 IST.
    - **Unplanned outages**: Email notifications to registered contacts, but often delayed or absent for minor issues.

    The platform addresses this gap through:
    1. **Active health monitoring**: Per-port health checks every minute with automatic fallback activation after 3 consecutive failures.
    2. **Proactive polling pause**: Automatic detection and skipping of scheduled maintenance windows.
    3. **Multi-tier fallback**: VesselFinder API as secondary source, stale cache as tertiary, manual entry as last resort.
    4. **Ops alerts**: Slack and PagerDuty integration ensures awareness within 5 minutes of any outage.

---

## References
- [Indian PCS1x Portal](https://indianpcs.gov.in/)
- [Sagarmala Programme](https://sagarmala.gov.in/)
- [Mumbai Port Trust](https://mumbaiport.gov.in/)
- [JNPT Port](https://www.jnport.gov.in/)
