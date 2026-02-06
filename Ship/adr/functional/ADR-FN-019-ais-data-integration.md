# ADR-FN-019: AIS Data Integration

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

AIS (Automatic Identification System) data provides real-time vessel tracking information essential for predictive supply chain operations in maritime chandlery.

### Business Context
Knowing when and where vessels will arrive enables proactive procurement:
- Pre-stage inventory at destination ports
- Optimize delivery logistics
- Trigger automated RFQ processes based on ETA
- Provide buyers with arrival-based ordering windows
- Enable predictive supply recommendations

Ship arrival prediction has reached 87% accuracy at 10 days before arrival (within ±48 hours) using advanced ML models, transforming reactive chandlery operations into proactive supply preparation.

### Technical Context
- Ships transmit AIS data via VHF (terrestrial receivers) and satellite
- Data includes: MMSI, IMO number, position, speed, course, destination, ETA
- Multiple data providers with varying coverage and pricing
- India's PCS1x provides free access to major port vessel movements
- Need to store historical data for pattern analysis

### Assumptions
- AIS data is reliable for commercial vessels
- Destination data may be outdated (entered by crew)
- Real-time updates every few minutes sufficient (not seconds)
- Initial use cases are port arrival prediction, not open-ocean tracking

---

## Decision Drivers

- Accuracy of arrival predictions
- Indian port coverage
- Cost at projected query volumes
- API reliability and latency
- Data freshness requirements
- Scalability to additional use cases

---

## Considered Options

### Option 1: VesselFinder API
**Description:** European provider with good coverage, cost-effective for moderate volumes.

**Pros:**
- €330 for 10,000 credits (cost-effective for MVP)
- Good Indian port coverage
- Simple REST API
- Historical track data available
- Real-time positions

**Cons:**
- Credit-based pricing can be unpredictable
- Satellite coverage less comprehensive
- Limited predictive features

### Option 2: Spire Maritime
**Description:** Premium satellite AIS provider with global coverage and integrated weather.

**Pros:**
- Superior satellite coverage (100+ nanosats)
- Sub-1-minute latency
- Integrated weather data
- Advanced vessel insights
- Predictive ETA features

**Cons:**
- Premium pricing ($10K+/month)
- Overkill for MVP
- Complex integration

### Option 3: Windward Maritime AI
**Description:** AI-powered maritime intelligence with advanced predictive analytics.

**Pros:**
- 87% ETA accuracy at 10 days
- Deep learning predictions
- Behavioral analytics
- API available

**Cons:**
- Highest cost tier
- Primarily security/compliance focused
- May be overkill for supply chain use

### Option 4: India PCS1x Integration
**Description:** Free access to Indian port vessel movements via government system.

**Pros:**
- Free for registered stakeholders
- Covers all 12 major Indian ports
- Official government data
- VTMS integration at key ports

**Cons:**
- India-only coverage
- Registration required
- API maturity varies by port
- Limited predictive features

---

## Decision

**Chosen Option:** VesselFinder (MVP) + PCS1x (India), upgrade path to Spire/Windward

We will implement a tiered approach: VesselFinder API for global vessel tracking and PCS1x for Indian port data in MVP, with architecture supporting upgrade to Spire or Windward as scale justifies.

### Rationale
VesselFinder provides cost-effective global tracking suitable for MVP volumes, while PCS1x delivers free, authoritative Indian port data. This combination covers primary use cases at minimal cost. The abstraction layer supports seamless upgrade to premium providers as business scales.

---

## Consequences

### Positive
- Cost-effective MVP implementation
- Free Indian port data via PCS1x
- Clear upgrade path to premium providers
- Enables predictive supply features
- Proactive delivery scheduling

### Negative
- Less sophisticated predictions initially
- **Mitigation:** Build ML capability using historical data
- Multiple integrations to maintain
- **Mitigation:** Provider abstraction layer

### Risks
- AIS data gaps: Multiple providers, terrestrial + satellite
- ETA inaccuracy: Buffer times, confidence intervals
- PCS1x access issues: VesselFinder as backup

---

## Implementation Notes

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Maritime Data Service                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  AIS Provider Abstraction                     │   │
│  │                                                               │   │
│  │   getVesselPosition()  │  getVesselTrack()  │  getETA()      │   │
│  │   searchVessels()      │  getPortArrivals() │  subscribeVessel()│ │
│  │                                                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                            │                                         │
│         ┌──────────────────┼──────────────────┐                     │
│         │                  │                  │                     │
│  ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐               │
│  │ VesselFinder│   │   PCS1x     │   │   Spire     │               │
│  │   Adapter   │   │   Adapter   │   │  (Future)   │               │
│  └─────────────┘   └─────────────┘   └─────────────┘               │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     Local Data Store                          │   │
│  │                                                               │   │
│  │   vessel_positions  │  vessel_tracks  │  port_arrivals       │   │
│  │   (TimescaleDB hypertable - if enabled)                      │   │
│  │                                                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Provider Interface

```typescript
// ais/interfaces/ais-provider.interface.ts
export interface AisProvider {
  name: string;

  // Vessel lookup
  getVesselByImo(imo: string): Promise<VesselInfo>;
  getVesselByMmsi(mmsi: string): Promise<VesselInfo>;
  searchVessels(query: VesselSearchQuery): Promise<VesselInfo[]>;

  // Position data
  getVesselPosition(identifier: VesselIdentifier): Promise<VesselPosition>;
  getVesselTrack(identifier: VesselIdentifier, hours: number): Promise<TrackPoint[]>;

  // Port operations
  getPortArrivals(portCode: string, hours: number): Promise<PortArrival[]>;
  getPortDepartures(portCode: string, hours: number): Promise<PortDeparture[]>;

  // ETA
  getEta(identifier: VesselIdentifier, destinationPort: string): Promise<EtaPrediction>;
}

export interface VesselPosition {
  imo: string;
  mmsi: string;
  name: string;
  latitude: number;
  longitude: number;
  course: number;
  speed: number;  // Knots
  heading: number;
  destination: string;
  eta: Date;
  timestamp: Date;
  source: 'TERRESTRIAL' | 'SATELLITE';
}

export interface EtaPrediction {
  vesselIdentifier: VesselIdentifier;
  destinationPort: string;
  predictedEta: Date;
  confidence: number;  // 0-1
  lowerBound: Date;
  upperBound: Date;
  distanceRemaining: number;  // Nautical miles
  calculatedAt: Date;
}

export interface PortArrival {
  vesselImo: string;
  vesselName: string;
  portCode: string;
  eta: Date;
  source: 'AIS' | 'SCHEDULE' | 'VTMS';
  berthAssignment?: string;
}
```

### VesselFinder Adapter

```typescript
// ais/adapters/vesselfinder.adapter.ts
@Injectable()
export class VesselFinderAdapter implements AisProvider {
  name = 'VesselFinder';

  private readonly baseUrl = 'https://api.vesselfinder.com';
  private readonly apiKey: string;

  constructor(private readonly configService: ConfigService) {
    this.apiKey = this.configService.get('VESSELFINDER_API_KEY');
  }

  async getVesselByImo(imo: string): Promise<VesselInfo> {
    const response = await this.request('/vessels', {
      imo: imo,
      format: 'json'
    });

    return this.mapVesselResponse(response.data);
  }

  async getVesselPosition(identifier: VesselIdentifier): Promise<VesselPosition> {
    const response = await this.request('/vessels/positions', {
      [identifier.type]: identifier.value,
      interval: '0'  // Latest position only
    });

    const position = response.data[0];

    return {
      imo: position.IMO,
      mmsi: position.MMSI,
      name: position.NAME,
      latitude: position.LAT,
      longitude: position.LON,
      course: position.COURSE,
      speed: position.SPEED,
      heading: position.HEADING,
      destination: position.DESTINATION,
      eta: position.ETA ? new Date(position.ETA) : null,
      timestamp: new Date(position.TIMESTAMP),
      source: position.SOURCE === 1 ? 'SATELLITE' : 'TERRESTRIAL'
    };
  }

  async getVesselTrack(
    identifier: VesselIdentifier,
    hours: number
  ): Promise<TrackPoint[]> {
    const response = await this.request('/vessels/track', {
      [identifier.type]: identifier.value,
      hours: hours.toString()
    });

    return response.data.map(point => ({
      latitude: point.LAT,
      longitude: point.LON,
      speed: point.SPEED,
      course: point.COURSE,
      timestamp: new Date(point.TIMESTAMP)
    }));
  }

  async getPortArrivals(portCode: string, hours: number): Promise<PortArrival[]> {
    const response = await this.request('/ports/arrivals', {
      port: portCode,
      hours: hours.toString()
    });

    return response.data.map(arrival => ({
      vesselImo: arrival.IMO,
      vesselName: arrival.NAME,
      portCode: portCode,
      eta: new Date(arrival.ETA),
      source: 'AIS' as const
    }));
  }

  async getEta(
    identifier: VesselIdentifier,
    destinationPort: string
  ): Promise<EtaPrediction> {
    // VesselFinder provides basic ETA from AIS
    const position = await this.getVesselPosition(identifier);

    // Calculate distance to port
    const portCoords = await this.getPortCoordinates(destinationPort);
    const distance = this.calculateDistance(
      position.latitude, position.longitude,
      portCoords.latitude, portCoords.longitude
    );

    // Estimate time based on current speed
    const hoursRemaining = position.speed > 0 ? distance / position.speed : null;
    const predictedEta = hoursRemaining
      ? new Date(Date.now() + hoursRemaining * 3600000)
      : position.eta;

    return {
      vesselIdentifier: identifier,
      destinationPort,
      predictedEta,
      confidence: this.calculateConfidence(distance, position.speed),
      lowerBound: new Date(predictedEta.getTime() - 12 * 3600000),
      upperBound: new Date(predictedEta.getTime() + 12 * 3600000),
      distanceRemaining: distance,
      calculatedAt: new Date()
    };
  }

  private async request(endpoint: string, params: object): Promise<any> {
    const url = new URL(endpoint, this.baseUrl);
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.append(key, value);
    });
    url.searchParams.append('userkey', this.apiKey);

    const response = await fetch(url.toString());
    return response.json();
  }
}
```

### PCS1x Adapter (India Ports)

```typescript
// ais/adapters/pcs1x.adapter.ts
@Injectable()
export class Pcs1xAdapter implements Partial<AisProvider> {
  name = 'PCS1x';

  private readonly baseUrl: string;
  private readonly credentials: Pcs1xCredentials;

  // Supported ports
  private readonly SUPPORTED_PORTS = [
    'INMAA', // Chennai
    'INBOM', // Mumbai (JNPT)
    'INCOK', // Cochin
    'INKOL', // Kolkata
    'INMUN', // Mundra
    'INPAV', // Pipavav
    'INNSA', // Nhava Sheva
    'INVIS', // Visakhapatnam
    'INTUT', // Tuticorin
    'INKRI', // Krishnapatnam
    'INENG', // Ennore
    'INPBD'  // Paradip
  ];

  async getPortArrivals(portCode: string, hours: number): Promise<PortArrival[]> {
    if (!this.SUPPORTED_PORTS.includes(portCode)) {
      throw new Error(`Port ${portCode} not supported by PCS1x`);
    }

    const token = await this.authenticate();

    const response = await this.httpService.get(
      `${this.baseUrl}/api/v1/ports/${portCode}/vessels/expected`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        params: {
          hours_ahead: hours,
          status: 'ARRIVING'
        }
      }
    ).toPromise();

    return response.data.vessels.map(vessel => ({
      vesselImo: vessel.imo_number,
      vesselName: vessel.vessel_name,
      portCode,
      eta: new Date(vessel.expected_arrival),
      source: 'VTMS' as const,
      berthAssignment: vessel.berth_allocated
    }));
  }

  async getVesselPosition(identifier: VesselIdentifier): Promise<VesselPosition> {
    // PCS1x provides limited position data within port approaches
    const token = await this.authenticate();

    const response = await this.httpService.get(
      `${this.baseUrl}/api/v1/vessels/${identifier.value}/position`,
      {
        headers: { 'Authorization': `Bearer ${token}` }
      }
    ).toPromise();

    return {
      imo: response.data.imo_number,
      mmsi: response.data.mmsi,
      name: response.data.vessel_name,
      latitude: response.data.latitude,
      longitude: response.data.longitude,
      course: response.data.course,
      speed: response.data.speed,
      heading: response.data.heading,
      destination: response.data.destination_port,
      eta: new Date(response.data.eta),
      timestamp: new Date(response.data.timestamp),
      source: 'TERRESTRIAL'
    };
  }

  private async authenticate(): Promise<string> {
    // PCS1x authentication flow
    const response = await this.httpService.post(
      `${this.baseUrl}/auth/token`,
      {
        client_id: this.credentials.clientId,
        client_secret: this.credentials.clientSecret,
        grant_type: 'client_credentials'
      }
    ).toPromise();

    return response.data.access_token;
  }
}
```

### Vessel Tracking Service

```typescript
// ais/services/vessel-tracking.service.ts
@Injectable()
export class VesselTrackingService {
  constructor(
    private readonly vesselFinderAdapter: VesselFinderAdapter,
    private readonly pcs1xAdapter: Pcs1xAdapter,
    private readonly vesselRepository: VesselRepository,
    private readonly eventEmitter: EventEmitter2
  ) {}

  async trackVessel(identifier: VesselIdentifier): Promise<VesselPosition> {
    // Try PCS1x first for Indian ports (free)
    const vessel = await this.vesselRepository.findByIdentifier(identifier);

    if (vessel?.lastKnownDestination && this.isIndianPort(vessel.lastKnownDestination)) {
      try {
        return await this.pcs1xAdapter.getVesselPosition(identifier);
      } catch (error) {
        // Fall back to VesselFinder
      }
    }

    return await this.vesselFinderAdapter.getVesselPosition(identifier);
  }

  async subscribeToVessel(
    identifier: VesselIdentifier,
    organizationId: string
  ): Promise<VesselSubscription> {
    const subscription = await this.vesselRepository.createSubscription({
      identifier,
      organizationId,
      active: true,
      createdAt: new Date()
    });

    // Start polling for this vessel
    await this.startPolling(subscription);

    return subscription;
  }

  @Cron('*/15 * * * *')  // Every 15 minutes
  async updateSubscribedVessels(): Promise<void> {
    const subscriptions = await this.vesselRepository.getActiveSubscriptions();

    for (const sub of subscriptions) {
      try {
        const position = await this.trackVessel(sub.identifier);

        // Check for significant changes
        if (this.hasSignificantChange(sub.lastPosition, position)) {
          await this.handlePositionUpdate(sub, position);
        }

        await this.vesselRepository.updatePosition(sub.id, position);
      } catch (error) {
        logger.error(`Failed to update vessel ${sub.identifier.value}`, error);
      }
    }
  }

  private async handlePositionUpdate(
    subscription: VesselSubscription,
    position: VesselPosition
  ): Promise<void> {
    // Check if approaching subscribed port
    const approachingPorts = await this.checkPortApproach(position);

    for (const port of approachingPorts) {
      this.eventEmitter.emit('vessel.approaching', {
        subscription,
        position,
        port,
        estimatedArrival: position.eta
      });
    }
  }

  private hasSignificantChange(
    previous: VesselPosition | null,
    current: VesselPosition
  ): boolean {
    if (!previous) return true;

    // Speed change > 2 knots
    if (Math.abs(previous.speed - current.speed) > 2) return true;

    // Destination changed
    if (previous.destination !== current.destination) return true;

    // Position change > 10nm
    const distance = this.calculateDistance(
      previous.latitude, previous.longitude,
      current.latitude, current.longitude
    );
    if (distance > 10) return true;

    return false;
  }
}
```

### Dependencies
- ADR-FN-020: India Port Integration (PCS1x)
- ADR-FN-021: Predictive Supply ML Model
- ADR-NF-004: Time Series with TimescaleDB (optional)

### Migration Strategy
1. Register for VesselFinder API access
2. Apply for PCS1x stakeholder registration
3. Implement provider abstraction layer
4. Build VesselFinder adapter
5. Add PCS1x adapter for Indian ports
6. Create vessel tracking service
7. Build arrival prediction triggers

---

## AIS Provider Configuration

### Provider Selection

| Phase | Provider | Coverage | Update Frequency | Cost |
|-------|----------|----------|------------------|------|
| **MVP** | VesselFinder | Global, 95% accuracy | 1-5 min | ~$500/month |
| **Scale** | Spire Maritime | Global, 99% accuracy | Real-time (satellite) | ~$3,000/month |
| **Fallback** | MarineTraffic | Global, 90% accuracy | 1-10 min | ~$300/month |

### Update Frequency by Use Case

| Use Case | Required Freshness | Polling Interval |
|----------|-------------------|------------------|
| Vessel tracking (map) | <5 min | 2 min |
| ETA calculation | <15 min | 5 min |
| Pre-arrival trigger | <1 hour | 15 min |
| Historical analytics | Daily | Batch (midnight) |

### Data Quality Filtering Rules

```typescript
// AIS data quality filters
interface AISQualityRules {
  // Position validation
  maxPositionAge: 3600,        // Reject positions >1 hour old
  validLatRange: [-90, 90],
  validLonRange: [-180, 180],

  // Speed/course validation
  maxSpeedKnots: 50,           // Filter anomalous speeds
  minSpeedForMoving: 0.5,      // Below = "at anchor"

  // Vessel type filtering
  excludeVesselTypes: [        // Focus on commercial vessels
    'fishing',
    'pleasure',
    'sailing'
  ],

  // Signal quality
  minSignalConfidence: 0.7,    // Reject low-confidence positions
  requireValidIMO: true,       // Must have IMO for linking
}

// Duplicate/stale position handling
function filterAISPosition(pos: AISPosition): boolean {
  if (pos.timestamp < Date.now() - RULES.maxPositionAge * 1000) return false;
  if (pos.speed > RULES.maxSpeedKnots) return false;
  if (!pos.imo && RULES.requireValidIMO) return false;
  return true;
}
```

## Licensing and Data Retention

### Licensing Terms

| Provider | License Type | Key Restrictions |
|----------|--------------|------------------|
| VesselFinder | API subscription | No redistribution, rate limits |
| Spire | Enterprise | NDA required, data ownership retained |
| MarineTraffic | API subscription | Attribution required |

### Data Retention Policy

| Data Type | Retention Period | Storage | Justification |
|-----------|------------------|---------|---------------|
| Real-time positions | 24 hours | Redis | Operational use only |
| Historical tracks | 90 days | PostgreSQL | Analytics, dispute resolution |
| Port call records | 2 years | PostgreSQL | Business intelligence |
| Aggregated statistics | 5 years | TimescaleDB | Trend analysis |
| Raw AIS messages | 7 days | S3 (compressed) | Debugging, audit |

### Data Deletion Workflow

```sql
-- Automated cleanup job (runs nightly)
-- 1. Delete old real-time positions
DELETE FROM vessel_positions WHERE timestamp < NOW() - INTERVAL '24 hours';

-- 2. Archive historical tracks older than 90 days
INSERT INTO vessel_tracks_archive SELECT * FROM vessel_tracks WHERE timestamp < NOW() - INTERVAL '90 days';
DELETE FROM vessel_tracks WHERE timestamp < NOW() - INTERVAL '90 days';

-- 3. Aggregate and purge port calls older than 2 years
-- (aggregate to monthly summaries before deletion)
```

## Vessel Record Linking and Validation

### Linking Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                  AIS → Vessel Linking                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  AIS Data                    Vessel Registry                │
│  ┌─────────────┐             ┌─────────────┐                │
│  │ MMSI        │─────────────│ MMSI        │  Direct match  │
│  │ IMO Number  │─────────────│ IMO Number  │  Primary key   │
│  │ Call Sign   │─────────────│ Call Sign   │  Fallback      │
│  │ Vessel Name │─────────────│ Vessel Name │  Fuzzy match   │
│  └─────────────┘             └─────────────┘                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Validation Rules

| Field | Validation | Action on Mismatch |
|-------|------------|-------------------|
| IMO Number | Must match registry | Reject update, alert |
| MMSI | Should match (can change) | Update vessel record |
| Vessel Name | Fuzzy match >80% | Flag for review |
| Flag State | Should match registry | Log discrepancy |
| Vessel Type | Should match registry | Log discrepancy |

### Linking Process

```typescript
async function linkAISToVessel(aisData: AISMessage): Promise<Vessel | null> {
  // 1. Primary: IMO number (most reliable)
  if (aisData.imo) {
    const vessel = await vesselRepo.findByIMO(aisData.imo);
    if (vessel) return vessel;
  }

  // 2. Secondary: MMSI (can be reassigned)
  if (aisData.mmsi) {
    const vessel = await vesselRepo.findByMMSI(aisData.mmsi);
    if (vessel) {
      // Verify with additional fields
      if (this.validateVesselMatch(vessel, aisData)) {
        return vessel;
      }
    }
  }

  // 3. Fallback: Name + Type fuzzy match
  const candidates = await vesselRepo.searchByName(aisData.vesselName);
  const match = candidates.find(v =>
    this.fuzzyNameMatch(v.name, aisData.vesselName) > 0.8 &&
    v.vesselType === aisData.vesselType
  );

  if (match) {
    // Flag for human verification
    await this.flagForReview(match.id, aisData, 'fuzzy_match');
    return match;
  }

  return null; // Unknown vessel
}
```

---

## References
- [VesselFinder API](https://api.vesselfinder.com/docs/)
- [Indian PCS1x Portal](https://indianpcs.gov.in/)
- [AIS Data Specification](https://www.navcen.uscg.gov/sites/default/files/pdf/AIS/AISGuide.pdf)
- [Spire Maritime API](https://spire.com/maritime/)
