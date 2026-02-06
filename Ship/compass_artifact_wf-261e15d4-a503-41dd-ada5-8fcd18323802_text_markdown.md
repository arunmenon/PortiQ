# Building a maritime ship chandlery platform: A complete technical blueprint

**The global ship chandlery market represents a $95 billion opportunity ripe for digital disruption.** While maritime procurement remains one of the most paper-intensive industries—with chandlers still manually processing 150+ line item requisitions via phone calls and Excel sheets—the convergence of document AI, marketplace technology, and India's fintech infrastructure creates ideal conditions for a platform play. ShipServ's $4 billion annual trade volume and recent acquisition by Marcura proves the model; India's sole digital player, ShipsKart, raised $2.7M in 2022 and operates fulfillment centers in Mumbai and Cochin, validating local demand. Your multi-layer strategy—starting as direct supplier, building marketplace orchestration, adding fintech early settlement, then IoT—mirrors the successful playbook of B2B procurement unicorns.

---

## The competitive landscape reveals both validation and white space

The maritime procurement market presents a classic fragmented industry awaiting consolidation. **ShipServ dominates with 73,000+ registered suppliers** and 260+ shipowner buyers representing 40% of global container capacity. Founded in 1999, its August 2023 acquisition by Marcura (portfolio company of Marlin Equity Partners) created an end-to-end procurement-to-payment platform by combining ShipServ's marketplace with MarTrust payment processing and DA-Desk port cost management. This consolidation signals market maturation and the premium investors place on integrated solutions.

**Wrist Ship Supply controls approximately 12% of the global provisions market** with the only truly global physical network spanning 35+ locations and 750+ ports. Their strategic move was funding Source2Sea—an independent multi-supplier marketplace launched December 2021 with BCG Digital Ventures. This signals that even dominant physical players recognize digital marketplace inevitability. Source2Sea's integration with RINA Digital Solutions via PunchOut catalog demonstrates the critical importance of ERP connectivity.

India represents significant whitespace. **ShipsKart, founded in 2017 by former seafarer Dhruv Sawhney**, is the sole meaningful digital player targeting mid-segment shipping companies with fulfillment centers in Mumbai and Cochin. Their $2.7M Series A (March 2022) allocated 80% to India operations, and they've achieved 13.7M SGD annual revenue by FY 2024. Yet with India's 12 major ports, 200+ minor ports, and 95% of trade volume moving via maritime transport, the market remains vastly underserved. ShipsKart's mobile-first approach and IMPA-integrated platform provide a template, but significant opportunity exists for a superior platform with embedded fintech.

**Key lessons from market leaders:** success requires (1) critical mass of suppliers creating network effects, (2) deep integration with fleet management systems like AMOS and SERTICA, (3) standardization around IMPA codes, and (4) mobile-first design for seafarers with limited connectivity. Failures typically stem from fragmented markets resisting digital adoption, relationship-based selling trumping platform efficiency, and integration complexity with legacy systems.

---

## Document AI now enables automated requisition processing at production scale

The technology stack for parsing 150+ line item requisitions from Excel, PDF, and Word documents has matured dramatically in 2024-2025. **Azure Document Intelligence v4.0 (released November 2024) natively supports DOCX, XLSX, PPTX alongside PDFs**, outputting Markdown format ideal for LLM consumption. This eliminates the need for separate parsing libraries per format. At **$1.50 per 1,000 pages for basic extraction** (dropping to $0.60 at volume), costs are negligible relative to labor savings.

The recommended architecture combines cloud document AI with LLM extraction:

1. **Initial parsing:** Azure Document Intelligence extracts tables as structured Markdown, handling complex layouts, merged cells, and multi-row headers that defeat traditional parsers
2. **LLM normalization:** GPT-4o or Claude 3.5 Sonnet (both achieving 97-98% accuracy on invoice extraction benchmarks) interprets extracted data, normalizes product names, and outputs structured JSON
3. **SKU matching:** Vector embeddings enable semantic similarity matching between extracted line items and your product catalog, with reranking via LLM for final confidence scoring

**For tables with 150+ line items, LlamaIndex's PER_TABLE_ROW extraction target is critical**—document-level extraction can miss 80% of entities in large tables due to LLM attention limitations. LlamaParse processes row-by-row, preventing this failure mode.

The pipeline architecture should be queue-based with confidence-gated routing. Items exceeding 95% confidence auto-approve; 80-95% queue for quick human review; below 80% require full validation. This human-in-the-loop pattern reduces manual effort by 60-90% while maintaining accuracy for edge cases like handwritten notes or poor scans.

**Estimated cost for 5,000 pages monthly:** Azure Document Intelligence ($7.50-$50), LLM API calls ($25-50), totaling approximately **$75-100/month**—less than one hour of manual data entry labor.

---

## IMPA codes provide the foundation for your product master database

The **International Marine Purchasing Association's Marine Stores Guide (MSG)** is the de facto global standard for maritime procurement, used for 40+ years. The system comprises **50,000+ six-digit unique codes** organized into 35 main categories covering everything from provisions (00) through welding equipment (85). These codes have remained consistent for nearly 40 years, enabling seamless ordering across language barriers worldwide.

The complete IMPA category hierarchy spans:
- **Deck operations:** Rope & hawsers (21), rigging equipment (23), marine paint (25), nautical equipment (37)
- **Engine room:** Pipes & tubes (71), valves & cocks (75), bearings (77), machinery equipment (87)
- **Safety:** Protective gear (31), safety equipment (33), medicine (39)
- **Consumables:** Petroleum products (45), cleaning chemicals (55)
- **Tools:** Pneumatic & electrical (59), hand tools (61), cutting tools (63), measuring tools (65)
- **Provisions:** Food and bonded stores (00), welfare items (11), tableware (17)

**IMPA offers multiple integration paths:** the MSG Data Licence provides CSV/Excel format for bulk import with bi-annual updates; the **MSG API launched in 2022** enables live cloud-based data feeds with key-based authentication, eliminating manual uploads. MESPAS became the first platform to integrate this API in February 2025. Licensing costs vary by company size, with annual subscriptions requiring 3-year minimum commitment.

For practical implementation, structure your product master with IMPA codes as primary identifiers, cross-referenced with ISSA codes (from the International Shipsuppliers & Services Association) for supplier flexibility. ISSA's Ship Stores Catalogue contains 60,000+ items and is commonly used by suppliers. Include essential attributes: IMPA code, description, specifications, unit of measure, manufacturer, part number, equivalents, and IHM (Inventory of Hazardous Materials) relevance flags.

**The ShipServ IMPA Catalogue** (impa-catalogue.shipserv.com) provides free lookup functionality useful for validation during development.

---

## Marketplace architecture should follow composable, API-first patterns

Modern B2B marketplaces adopt **composable, headless architecture** aligned with MACH principles (Microservices, API-first, Cloud-native, Headless). The reference model separates concerns cleanly: API gateway for routing and authentication; discrete services for RFQ management, bidding engine, quote comparison, orders, catalog, and payments; event-driven communication via Apache Kafka or RabbitMQ; and headless frontends consuming APIs.

**For the bidding system, three auction types serve different procurement scenarios:**

1. **Reverse auction (British):** Open bidding where suppliers see competing bids and prices decrease over time. Best for commodity items where price is primary criterion. Implement with time-based countdown plus automatic extensions when bids arrive near deadline.

2. **Sealed-bid auction:** Single confidential submission with winner determination after deadline. Ensures fairness for strategic sourcing where relationship concerns exist.

3. **Multi-attribute reverse auction:** Scoring combines price, quality, delivery time, and payment terms with weighted evaluation criteria. Optimal for complex maritime requisitions where total cost of ownership matters more than unit price.

**The RFQ lifecycle follows a state machine:** DRAFT → PUBLISHED → BIDDING_OPEN → BIDDING_CLOSED → EVALUATION → AWARDED → COMPLETED, with cancellation possible at any stage. OroCommerce's RFQ management provides a proven reference pattern including multi-level approval workflows.

**Medusa.js with the Mercur marketplace extension** offers the strongest open-source foundation. Key capabilities include unified multi-vendor checkout, automatic split payments via Stripe Connect, vendor dashboards, commission handling, and a built-in workflow engine supporting the saga pattern for complex transactions like quote acceptance that span multiple services.

The quote comparison engine requires sophisticated TCO calculation incorporating base price, shipping costs (derived from Incoterms), lead time penalties, quality scores from supplier history, and payment terms adjustments. Store quotes in a normalized schema with line-item granularity enabling item-by-item comparison across suppliers.

---

## Maritime intelligence enables predictive supply preparation

**Ship arrival prediction accuracy has reached 87% at 10 days before arrival** (within ±48 hours) using Windward Maritime AI's deep learning models trained on 12+ years of data. This capability transforms reactive chandlery operations into proactive supply preparation, triggering warehouse staging 48-72 hours before predicted arrival.

AIS (Automatic Identification System) data provides the foundation. Ships automatically transmit position, speed, course, and destination via transponders, collected by 13,000+ terrestrial receivers (MarineTraffic's network) and satellite constellations (Spire operates 100+ nanosatellites with sub-1-minute latency). Key data elements include MMSI, IMO number, current position, SOG/COG, heading, and critically, declared destination and ETA.

**Tier-appropriate data sources for your platform:**

- **MVP phase:** VesselFinder API at €330 for 10,000 credits offers cost-effective entry with good Indian port coverage. India's PCS1x (Port Community System) provides free access to registered stakeholders for vessel movement data at Mumbai, Cochin, and all 12 major ports.

- **Scale phase:** Spire Maritime ($10K+/month) delivers superior satellite coverage for open-ocean tracking plus integrated weather data. Windward provides best-in-class ETA predictions with API integration.

**India-specific intelligence:** PCS1x (indianpcs.gov.in), launched by Indian Ports Association in 2018, integrates all 12 major ports with API-based architecture for real-time vessel movements. Mumbai Port Trust was first to implement full API integration. Cochin Port operates VTMS (Vessel Traffic Management System) with radar/AIS-based monitoring. The Sagarmala programme's Logistics Data Bank provides RFID-based real-time EXIM container tracking.

**Predictive supply requirements** should model: vessel type (bulk carriers need more provisions, tankers need safety equipment), crew size (typically 15-30), voyage length and route, days since last resupply, and historical purchase patterns. Machine learning approaches combining time series forecasting (LSTM/Prophet for consumption patterns), collaborative filtering (similar vessels' purchases), and gradient boosting (XGBoost with vessel/voyage features) can generate preliminary requisition lists before ships even submit orders.

---

## India's fintech infrastructure enables embedded early settlement

**Ship chandlers facing 90-120 day payment cycles can receive 70% at 30 days** through India's robust trade finance ecosystem. The RBI-regulated TReDS (Trade Receivables Discounting System) operates on a **mandatory "without recourse" basis**, meaning suppliers bear no liability if buyers default—highly advantageous for chandlers.

**Five licensed TReDS platforms** enable competitive bidding among financiers:

| Platform | Backing | Scale |
|----------|---------|-------|
| **M1xchange** | Amazon, SIDBI | Largest: 66+ banks, 50,000+ MSMEs, ₹1.7 Lakh Cr+ discounted |
| **RXIL** | NSE + SIDBI | Pioneer platform with transparent auction |
| **Invoicemart** | Axis Bank + mjunction | Strong bank network |
| **C2treds** | C2FO | International technology |
| **DTX** | KredX | Newest license (January 2025), fastest growing |

**Key NBFCs for direct integration** include Vivriti Capital (tech-enabled, API-first, unicorn status), KredX (invoice discounting marketplace), CredAble (embedded finance APIs with white-label solutions), and Northern Arc (wholesale funding platform). Processing typically delivers funds within 24-48 hours via NACH mechanism.

**The recommended integration architecture** uses an embedded finance middleware layer (CredAble, FinBox, or Decentro) providing single integration to multiple lenders. This handles invoice validation, credit scoring, offer matching, and compliance while you maintain control of the user experience. The API flow: invoice upload → automated credit assessment → financing request → multi-lender offer matching → acceptance → T+1 disbursement.

**Data requirements for invoice financing:** invoice details (number, date, amount, GSTIN), buyer acceptance/approval, delivery confirmation, and supporting documentation. Credit assessment leverages 12-24 months transaction history, bank statements via Account Aggregator, GST returns revealing buyer payment patterns, and platform-specific order frequency data.

**Practical pricing model:** 2-4% discount for 60-90 days early payment yields effective APR of 8-18%—competitive with working capital loans but requiring no collateral beyond the invoice itself. The platform captures 0.5-1% commission on financed amounts plus SaaS fees for order management.

---

## The recommended 2025 technology stack optimizes for speed and scale

**Primary backend: NestJS (Node.js/TypeScript)** provides Angular-style modular architecture with dependency injection, native microservices support, first-class WebSocket handling for real-time bidding, and strong TypeScript typing critical for financial transactions. Start with a modular monolith architecture—premature microservices adoption is a leading cause of B2B platform failures due to operational complexity.

**Database layer: PostgreSQL with extensions** serves as the unified foundation:

- **Core PostgreSQL 16+:** ACID compliance for financial transactions, row-level security for multi-tenant vendor isolation, complex joins for quote comparison
- **pgvector extension:** Production-ready vector storage for RAG and semantic search, eliminating need for separate vector database infrastructure. Supports HNSW indexing delivering sub-50ms queries for catalogs under 10M products
- **TimescaleDB extension:** Hypertables for IoT sensor data when you add device integration, using familiar SQL queries

**Search: Meilisearch** delivers sub-50ms typo-tolerant product search with faceted filtering, requiring minutes rather than days to configure compared to Elasticsearch. Supports hybrid keyword + semantic search in 2024-2025 versions.

**Document processing pipeline:**
```
[Upload API] → [S3 Storage] → [BullMQ Queue] → [Worker Pool]
                                                    ↓
                              [Azure Document Intelligence → LLM Extraction → pgvector]
```

**Frontend: Next.js 14+ with App Router** provides server-side rendering for marketplace SEO, React Server Components for performance, and TypeScript consistency with backend. Use shadcn/ui + Tailwind CSS for rapid UI development.

**Mobile: React Native with Expo** enables code sharing with web frontend, over-the-air updates critical for field agents who rarely visit app stores, and offline-first architecture with local SQLite syncing when connectivity returns.

**Cloud: AWS Mumbai (ap-south-1)** offers strongest compliance for RBI data localization, most mature managed services, and largest talent pool in India. Use **ECS Fargate over Kubernetes** initially—lower operational overhead, automatic scaling, native AWS integration. Graduate to EKS only when multi-cloud becomes a requirement or team gains Kubernetes expertise.

**Real-time architecture:** Socket.io with Redis adapter enables WebSocket scaling across multiple instances. For bidding concurrency, implement optimistic locking with unique constraints on parent_bid_id to prevent concurrent bid race conditions.

---

## Implementation follows a phased approach balancing speed and capability

**Phase 1 (Months 1-4): MVP with direct supplier model**
- NestJS modular monolith with core services (auth, catalog, orders)
- PostgreSQL + pgvector for unified data and search
- Basic document upload with Azure Document Intelligence extraction
- IMPA code integration via MSG Data Licence
- Next.js buyer portal, React Native mobile skeleton
- Manual quote management, no marketplace

**Phase 2 (Months 5-8): Marketplace orchestration**
- Chandler/supplier onboarding with KYC verification
- RFQ workflow engine with state machine
- Sealed-bid quote submission and comparison
- Real-time notifications via WebSockets
- Meilisearch integration for product discovery

**Phase 3 (Months 9-12): Fintech layer**
- Embedded finance integration via CredAble or FinBox
- TReDS platform connection for non-recourse financing
- Dynamic discounting for buyer cash deployment
- Credit scoring model using platform transaction data
- Payment reconciliation and settlement dashboard

**Phase 4 (Months 13-18): Intelligence and scale**
- AIS data integration (VesselFinder → Spire/Windward)
- PCS1x India port system connection
- Predictive supply requirements ML model
- Real-time reverse auction for price-sensitive items
- TimescaleDB integration for IoT foundation

**Critical success factors:** supplier network density creates buyer value; ERP integration (AMOS, SERTICA) reduces friction; mobile offline capability addresses vessel connectivity constraints; embedded fintech differentiates from pure marketplace competitors.

---

## Conclusion: The path to a defensible platform business

The maritime chandlery platform opportunity combines a fragmented $95 billion market, maturing document AI eliminating manual data entry, India-specific advantages in fintech infrastructure and port digitization, and proven marketplace patterns from adjacent industries. Your multi-layer strategy—direct supplier to marketplace to fintech to IoT—creates compounding defensibility at each stage.

**The immediate priorities:** (1) secure IMPA MSG Data Licence and build product master database; (2) deploy document AI pipeline for requisition processing; (3) establish warehouse operations at Mumbai and Cochin; (4) build initial buyer relationships while developing marketplace MVP. The technology stack is mature; execution and network effects will determine success.

India's mandatory TReDS registration for companies exceeding ₹250 Cr turnover (deadline June 2025) creates tailwinds for fintech adoption. PCS1x integration across all 12 major ports provides free access to vessel movement intelligence. ShipsKart's success at modest scale proves market demand exists. The window for establishing market position is open—and the consolidation trajectory evident in ShipServ's acquisition suggests strategic exit opportunities for successful platforms within 5-7 years.