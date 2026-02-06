#!/usr/bin/env python3
"""
Extract validation checklists from ADR files.
Parses each ADR to find key decisions and implementation requirements.
Generates focused, actionable checklist items per ADR.
"""

import json
import re
from pathlib import Path
from typing import Optional

ADR_DIR = Path(__file__).parent.parent
CONFIG_FILE = ADR_DIR / ".phase-config.json"

def load_phase_config():
    """Load the phase configuration."""
    with open(CONFIG_FILE) as f:
        return json.load(f)

def find_adr_file(adr_id: str) -> Optional[Path]:
    """Find the ADR file for a given ID like 'NF-001', 'FN-002', etc."""
    prefix_map = {
        "FN": ("functional", "ADR-FN"),
        "NF": ("non-functional", "ADR-NF"),
        "UI": ("ui", "ADR-UI"),
    }

    prefix = adr_id.split("-")[0]
    num = adr_id.split("-")[1]

    if prefix not in prefix_map:
        return None

    directory, file_prefix = prefix_map[prefix]
    padded_num = num.zfill(3)

    search_dir = ADR_DIR / directory
    if not search_dir.exists():
        return None

    for file in search_dir.glob(f"{file_prefix}-{padded_num}-*.md"):
        return file

    return None

def extract_title(content: str) -> str:
    """Extract the ADR title from the first line."""
    first_line = content.split("\n")[0]
    match = re.match(r"#\s+ADR-[A-Z]+-\d+:\s*(.+)", first_line)
    if match:
        return match.group(1).strip()
    return first_line.replace("#", "").strip()

def extract_section(content: str, section_name: str) -> str:
    """Extract content of a specific section."""
    pattern = rf"^##\s+{re.escape(section_name)}\s*$"
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        return ""

    start = match.end()
    next_section = re.search(r"^##\s+", content[start:], re.MULTILINE)
    if next_section:
        end = start + next_section.start()
    else:
        end = len(content)

    return content[start:end].strip()

def extract_chosen_option(decision_section: str) -> str:
    """Extract the chosen option from Decision section."""
    match = re.search(r"\*\*Chosen Option:\*\*\s*(.+?)(?:\n|$)", decision_section)
    if match:
        return match.group(1).strip()
    return ""

def extract_specific_requirements(content: str, adr_id: str, title: str) -> list[str]:
    """
    Extract ADR-specific requirements based on the ADR's focus area.
    Returns 1-3 focused checklist items per ADR.
    """
    items = []

    # ADR-specific extraction rules
    adr_rules = {
        # Foundation - Non-Functional
        "NF-001": [
            ("PostgreSQL 16+", "PostgreSQL 16+ with extensions: pgvector, uuid-ossp, ltree"),
            ("row[- ]level security|RLS", "Row-level security enabled for tenant isolation"),
        ],
        "NF-002": [
            ("pgvector", "pgvector extension with HNSW index for vector search"),
            ("embedding", "Vector embeddings stored with cosine similarity"),
        ],
        "NF-003": [
            ("Meilisearch", "Meilisearch configured for product search"),
            ("typo[- ]?tolerance|fuzzy", "Typo-tolerant search enabled"),
        ],
        "NF-006": [
            ("modular monolith", "NestJS modular monolith with clear module boundaries"),
            ("module", "Inter-module communication via exported services or events"),
        ],
        "NF-007": [
            ("OpenAPI", "REST API with OpenAPI 3.0 specification"),
            ("versioning|/v1/", "API versioning in URL path (/v1/)"),
        ],
        "NF-008": [
            ("BullMQ", "BullMQ for async job processing with Redis backend"),
            ("queue|job", "Separate queues per job type with retry policies"),
        ],
        "NF-011": [
            ("AWS", "AWS Mumbai (ap-south-1) as primary region"),
            ("multi-AZ|availability", "Multi-AZ deployment for high availability"),
        ],
        "NF-015": [
            ("JWT", "JWT access tokens (15min) + refresh tokens (7d)"),
            ("RBAC", "Role-based access control with organization scope"),
        ],

        # Foundation - Functional
        "FN-001": [
            ("IMPA", "IMPA 6-digit codes as canonical product identifiers"),
            ("ISSA", "ISSA codes maintained as secondary cross-reference"),
        ],
        "FN-002": [
            ("JSONB", "Product attributes in JSONB with JSON Schema validation"),
            ("specifications", "Core fields in columns, extensions in specifications JSONB"),
        ],

        # Foundation - UI
        "UI-001": [
            ("App Router", "Next.js 14+ with App Router (not Pages)"),
            ("Server Components", "React Server Components for data fetching"),
        ],
        "UI-006": [
            ("Expo", "React Native with Expo managed workflow"),
            ("Zustand", "Zustand for mobile state management"),
        ],

        # MVP - Functional
        "FN-003": [
            ("MSG API|IMPA API", "IMPA MSG API integration for catalog sync"),
            ("batch|CSV", "CSV batch import as fallback ingestion method"),
        ],
        "FN-004": [
            ("ltree", "PostgreSQL ltree for category hierarchy"),
            ("IMPA.*categor|prefix", "IMPA 2-digit prefix maps to top-level category"),
        ],
        "FN-006": [
            ("queue|pipeline", "Multi-stage document pipeline: Upload→Parse→Extract→Match→Review"),
            ("S3", "Documents stored in S3 with processing status tracking"),
        ],
        "FN-007": [
            ("Azure Document Intelligence|Form Recognizer", "Azure Document Intelligence v4.0 for OCR"),
            ("prebuilt|layout", "Use prebuilt-layout model for table extraction"),
        ],
        "FN-009": [
            (r"95%|\.95", "Auto-approve threshold: ≥95% confidence"),
            (r"80%|\.80", "Quick review: 80-94% confidence, full review: <80%"),
        ],
        "FN-023": [
            ("organization|org_id", "All data scoped to organization (tenant)"),
            ("RBAC|role", "Roles: owner, admin, member, viewer per organization"),
        ],

        # MVP - Non-Functional
        "NF-012": [
            ("ECS Fargate", "ECS Fargate for container orchestration"),
            ("auto[- ]?scal", "Auto-scaling based on CPU/memory thresholds"),
        ],
        "NF-013": [
            ("S3", "S3 bucket structure: documents/, exports/, assets/"),
            ("presigned", "Presigned URLs for secure direct uploads"),
        ],

        # MVP - UI
        "UI-002": [
            ("shadcn/ui", "shadcn/ui with Radix primitives for components"),
            ("Tailwind", "Tailwind CSS for styling (no CSS-in-JS)"),
        ],
        "UI-004": [
            ("dashboard", "Buyer portal: Dashboard, RFQs, Orders, Catalog views"),
        ],
        "UI-007": [
            ("offline|SQLite", "Offline-first with expo-sqlite local cache"),
            ("sync", "Background sync when connectivity restored"),
        ],
        "UI-011": [
            ("autocomplete|search", "Search autocomplete with Meilisearch backend"),
            ("facet|filter", "Faceted filtering by category, supplier, port"),
        ],

        # Marketplace - Functional
        "FN-011": [
            ("state machine|status", "RFQ states: DRAFT→PUBLISHED→BIDDING→AWARDED→COMPLETED"),
            ("event log", "All state transitions logged for audit"),
        ],
        "FN-012": [
            ("auction", "Auction types: sealed-bid, reverse, Dutch supported"),
            ("Socket|real-?time", "Real-time bid updates via Socket.io"),
        ],
        "FN-013": [
            ("TCO|total cost", "TCO calculation: price + shipping + duties + lead time"),
            ("weight|score", "Weighted scoring across multiple criteria"),
        ],
        "FN-014": [
            ("KYC|verification", "Supplier KYC: document upload, verification workflow"),
            ("tier", "Supplier tiers based on verification level"),
        ],
        "FN-015": [
            ("Medusa|marketplace", "Medusa.js as marketplace foundation"),
        ],
        "FN-022": [
            ("order.*fulfillment|lifecycle", "Order lifecycle: CREATED→CONFIRMED→SHIPPED→DELIVERED"),
            ("split|partial", "Support for partial fulfillment and split shipments"),
        ],

        # Marketplace - Non-Functional
        "NF-005": [
            ("Redis.*cache", "Redis caching with TTL-based invalidation"),
            ("cache-aside", "Cache-aside pattern for read-heavy data"),
        ],
        "NF-018": [
            ("RLS|row.level", "PostgreSQL RLS policies for tenant data isolation"),
            ("current_org", "Tenant context via app.current_org_id session variable"),
        ],

        # Marketplace - UI
        "UI-005": [
            ("supplier.*dashboard", "Supplier dashboard: RFQ responses, orders, analytics"),
        ],
        "UI-012": [
            ("Socket.io|notification", "Real-time notifications via Socket.io"),
            ("Redis.*adapter", "Socket.io Redis adapter for horizontal scaling"),
        ],

        # Enhancement - Functional
        "FN-016": [
            ("embedded finance|fintech", "Embedded finance middleware with provider abstraction"),
        ],
        "FN-017": [
            ("invoice financing|factoring", "Invoice financing workflow with TReDS integration"),
        ],
        "FN-019": [
            ("AIS|vessel", "AIS data integration for vessel tracking"),
            ("VesselFinder", "VesselFinder API for MVP, upgrade path to Spire"),
        ],
        "FN-020": [
            ("PCS|port", "India PCS1x integration for port data"),
        ],

        # Enhancement - Non-Functional
        "NF-016": [
            ("rate limit", "API rate limiting: 100 req/min standard, 1000 req/min premium"),
            ("WAF", "AWS WAF for DDoS protection"),
        ],
        "NF-017": [
            ("encrypt|KMS", "Data encryption: TLS 1.3 in transit, AES-256 at rest"),
            ("envelope", "AWS KMS with envelope encryption for sensitive data"),
        ],
        "NF-019": [
            ("observability|monitor", "OpenTelemetry for distributed tracing"),
            ("CloudWatch|logs", "Structured logging to CloudWatch"),
        ],
        "NF-020": [
            ("CI/CD|GitHub Actions", "GitHub Actions for CI/CD pipeline"),
            ("blue-green|deploy", "Blue-green deployments with automatic rollback"),
        ],

        # Enhancement - UI
        "UI-003": [
            ("React Query", "React Query for server state management"),
            ("Zustand", "Zustand for client state (cart, UI preferences)"),
        ],
        "UI-009": [
            ("design.*token|theme", "Design tokens for consistent theming"),
            ("dark.*mode", "Light/dark mode support"),
        ],

        # Advanced - Functional
        "FN-005": [
            ("JSONB.*extend|extensib", "JSONB for custom product attributes per category"),
            ("JSON Schema", "JSON Schema validation for custom attributes"),
        ],
        "FN-008": [
            ("LLM|GPT|Claude", "LLM provider abstraction (OpenAI primary, Claude fallback)"),
            ("normali[sz]", "LLM-based product description normalization"),
        ],
        "FN-010": [
            ("large table|row-by-row", "Row-by-row extraction for large document tables"),
            ("batch", "Batched API calls to avoid timeouts"),
        ],
        "FN-018": [
            ("TReDS", "TReDS integration for invoice discounting"),
        ],
        "FN-021": [
            ("predict|ML|forecast", "Predictive supply ML model for demand forecasting"),
            ("gradient.*boost|XGBoost", "Gradient boosting for prediction model"),
        ],
        "FN-024": [
            ("ERP|PunchOut", "Fleet ERP integration via PunchOut protocol"),
        ],

        # Advanced - Non-Functional
        "NF-004": [
            ("TimescaleDB|time.series", "TimescaleDB for time-series analytics"),
            ("hypertable", "Hypertables for time-partitioned data"),
        ],
        "NF-009": [
            ("event.*driven|EventEmitter", "Event-driven communication between modules"),
            ("outbox", "Outbox pattern for reliable event publishing"),
        ],
        "NF-010": [
            ("saga|compensat", "Saga pattern for distributed transactions"),
            ("rollback", "Compensating transactions for failure recovery"),
        ],
        "NF-014": [
            ("CDN|CloudFront", "CloudFront CDN for static assets and images"),
            ("cache.*header", "Cache headers for optimal CDN performance"),
        ],

        # Advanced - UI
        "UI-008": [
            ("catalog.*cache|offline.*catalog", "Mobile catalog caching with delta sync"),
        ],
        "UI-010": [
            ("WCAG|accessib", "WCAG 2.1 AA accessibility compliance"),
            ("aria|screen.*reader", "ARIA labels for screen reader support"),
        ],
    }

    # Get rules for this specific ADR
    rules = adr_rules.get(adr_id, [])

    for pattern, checklist_text in rules:
        if re.search(pattern, content, re.IGNORECASE):
            items.append(f"{checklist_text} (ADR-{adr_id})")

    # If no specific rules matched, extract the main decision
    if not items:
        decision_section = extract_section(content, "Decision")
        chosen = extract_chosen_option(decision_section)
        if chosen:
            items.append(f"{chosen} (ADR-{adr_id})")

    return items[:3]  # Max 3 items per ADR

def extract_operational_items(content: str, adr_id: str) -> list[str]:
    """Extract operational considerations as validation items."""
    items = []

    # Get the Operational Considerations section
    op_section = extract_section(content, "Operational Considerations")
    if not op_section:
        return items

    # Find subsection headers (the feedback items converted to headers)
    # Pattern: ### Some feedback item text
    subsections = re.findall(r"^###\s+([^#\n]+)", op_section, re.MULTILINE)

    for subsection in subsections:
        subsection = subsection.strip()
        # Skip "Open Questions" subsection
        if subsection.lower() == "open questions":
            continue

        # Convert feedback statement to validation item
        # "Define X, Y, and Z" -> "X, Y, and Z documented/defined"
        validation_item = convert_to_validation(subsection)
        if validation_item:
            items.append(f"{validation_item} (ADR-{adr_id})")

    return items[:2]  # Max 2 operational items per ADR


def convert_to_validation(feedback: str) -> str:
    """Convert a feedback statement to a validation item."""
    feedback = feedback.strip()

    # Common patterns and their transformations
    conversions = [
        # "Define X" -> "X defined"
        (r"^Define\s+(.+)", lambda m: f"{m.group(1).rstrip('.')} defined"),
        # "Specify X" -> "X specified"
        (r"^Specify\s+(.+)", lambda m: f"{m.group(1).rstrip('.')} specified"),
        # "Plan for X" -> "X plan documented"
        (r"^Plan for\s+(.+)", lambda m: f"{m.group(1).rstrip('.')} plan documented"),
        # "Address X" -> "X addressed"
        (r"^Address\s+(.+)", lambda m: f"{m.group(1).rstrip('.')} addressed"),
        # "Clarify X" -> "X clarified"
        (r"^Clarify\s+(.+)", lambda m: f"{m.group(1).rstrip('.')} clarified"),
        # "Document X" -> "X documented"
        (r"^Document\s+(.+)", lambda m: f"{m.group(1).rstrip('.')} documented"),
        # "Confirm X" -> "X confirmed"
        (r"^Confirm\s+(.+)", lambda m: f"{m.group(1).rstrip('.')} confirmed"),
        # "Add X" -> "X added"
        (r"^Add\s+(.+)", lambda m: f"{m.group(1).rstrip('.')} added"),
        # "Include X" -> "X included"
        (r"^Include\s+(.+)", lambda m: f"{m.group(1).rstrip('.')} included"),
        # "Enumerate X" -> "X enumerated"
        (r"^Enumerate\s+(.+)", lambda m: f"{m.group(1).rstrip('.')} enumerated"),
    ]

    for pattern, replacement in conversions:
        match = re.match(pattern, feedback, re.IGNORECASE)
        if match:
            return replacement(match)

    # Default: append "addressed" if no pattern matches
    return f"{feedback.rstrip('.')} addressed"


def extract_checklist_for_adr(adr_id: str) -> list[str]:
    """Extract checklist items for a single ADR."""
    file_path = find_adr_file(adr_id)
    if not file_path:
        return [f"ADR-{adr_id}: File not found"]

    with open(file_path) as f:
        content = f.read()

    title = extract_title(content)

    # Get technical requirements (from adr_rules)
    tech_items = extract_specific_requirements(content, adr_id, title)

    # Get operational items (from feedback)
    op_items = extract_operational_items(content, adr_id)

    # Combine: max 2 technical + max 2 operational = max 4 per ADR
    return tech_items[:2] + op_items[:2]

def consolidate_checklist(items: list[str]) -> list[str]:
    """
    Consolidate similar items to avoid redundancy.
    Keeps the most specific version of each concept.
    """
    # Group by ADR reference
    by_adr = {}
    for item in items:
        match = re.search(r"\(ADR-([A-Z]+-\d+)\)", item)
        if match:
            adr = match.group(1)
            if adr not in by_adr:
                by_adr[adr] = []
            by_adr[adr].append(item)

    # Keep items per ADR (up to 4: 2 technical + 2 operational)
    result = []
    for adr, adr_items in by_adr.items():
        result.extend(adr_items[:4])

    return result

def extract_all_checklists():
    """Extract checklists for all phases."""
    config = load_phase_config()

    result = {}
    for phase_num, phase_data in config["phases"].items():
        phase_checklist = []
        adr_ids = phase_data["adrs"]

        for adr_id in adr_ids:
            items = extract_checklist_for_adr(adr_id)
            phase_checklist.extend(items)

        # Consolidate and deduplicate
        consolidated = consolidate_checklist(phase_checklist)

        result[phase_num] = {
            "name": phase_data["name"],
            "description": phase_data["description"],
            "checklist": consolidated
        }

    return result

def main():
    """Main entry point."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--update-config":
        # Update the phase config with extracted checklists
        config = load_phase_config()
        checklists = extract_all_checklists()

        for phase_num, data in checklists.items():
            config["phases"][phase_num]["validationChecklist"] = data["checklist"]

        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

        print(f"Updated {CONFIG_FILE}")
    else:
        # Just print the checklists
        checklists = extract_all_checklists()

        for phase_num, data in sorted(checklists.items()):
            print(f"\n{'='*70}")
            print(f"PHASE {phase_num}: {data['name'].upper()}")
            print(f"{'='*70}")
            print(f"{data['description']}\n")

            for i, item in enumerate(data["checklist"], 1):
                print(f"  {i:2}. {item}")

            print(f"\n  Total items: {len(data['checklist'])}")

if __name__ == "__main__":
    main()
