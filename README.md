# PortiQ - AI-Native Maritime Procurement Platform

A B2B maritime ship chandlery platform targeting the $95B global market. PortiQ features a conversation-first AI paradigm, connecting fleet managers with port suppliers through intelligent RFQ workflows, predictive supply management, and document automation.

## Screenshots

| Dashboard | Chat (PortiQ AI) | RFQ Create |
|-----------|-------------------|------------|
| ![Dashboard](portiq-01-dashboard.png) | ![Chat](portiq-15-chat-page.png) | ![RFQ Create](portiq-04-rfq-create-intelligence.png) |

| Supplier Portal | Products | Search |
|-----------------|----------|--------|
| ![Supplier](portiq-05-supplier-dashboard.png) | ![Products](portiq-13-products-page.png) | ![Search](portiq-08-search-page.png) |

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, Python 3.12, SQLAlchemy 2.0 (async), Pydantic v2 |
| **Database** | PostgreSQL 16 + pgvector + ltree + tsvector FTS |
| **Migrations** | Alembic (16 migrations) |
| **Queue** | Celery + Redis |
| **Frontend** | Next.js 14 (App Router), shadcn/ui, Tailwind CSS, React Query, Zustand |
| **AI** | OpenAI function-calling (GPT-4o) with 10 domain tools |
| **Auth** | JWT (HS256) with multi-tenant RLS |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Next.js Frontend                   │
│  Buyer Portal (11 routes) │ Supplier Portal (6 routes) │
│  PortiQ Chat │ Command Bar │ Intelligence Sidebar     │
└──────────────────────┬──────────────────────────────┘
                       │ /api/v1/* (middleware proxy)
┌──────────────────────▼──────────────────────────────┐
│                 FastAPI Backend                       │
│  Modular Monolith (~151 endpoints)                   │
│ ┌──────────┬──────────┬──────────┬─────────────────┐ │
│ │ Products │ RFQs     │ Vessels  │ Organizations   │ │
│ │ Search   │ Suppliers│ TCO      │ Predictions     │ │
│ │ Docs AI  │ Intel    │ PortiQ   │ Health/Auth     │ │
│ └──────────┴──────────┴──────────┴─────────────────┘ │
└──────────┬──────────────────────────┬───────────────┘
           │                          │
┌──────────▼──────────┐   ┌──────────▼───────────────┐
│  PostgreSQL 16      │   │  Redis + Celery          │
│  pgvector, ltree    │   │  Async tasks, mat views  │
│  RLS, tsvector FTS  │   │  Scheduled refreshes     │
└─────────────────────┘   └──────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker (for PostgreSQL)

### 1. Database

```bash
# Start PostgreSQL with pgvector
docker run -d --name portiq-postgres \
  -e POSTGRES_USER=portiq \
  -e POSTGRES_PASSWORD=changeme \
  -e POSTGRES_DB=portiq \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

### 2. Backend

```bash
# Create and activate virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run migrations
PYTHONPATH=. .venv/bin/python -m alembic upgrade head

# Seed data (492 products, 8 orgs, 14 users, 5 suppliers, 8 vessels)
PYTHONPATH=. .venv/bin/python -m src.seed

# Start server
PYTHONPATH=. .venv/bin/uvicorn src.app:app --port 8000
```

### 3. Frontend

```bash
cd apps/web
npm install
npm run dev
# Open http://localhost:3000
```

### 4. Celery (optional, for async tasks)

```bash
# Requires Redis running on localhost:6379
celery -A celery_app worker --loglevel=info
```

## Project Structure

```
├── src/
│   ├── app.py                    # FastAPI application
│   ├── api/v1.py                 # API router aggregation
│   ├── config.py                 # Settings (pydantic-settings)
│   ├── models/                   # 38 SQLAlchemy models
│   │   ├── product.py            # IMPA-coded products
│   │   ├── organization.py       # Multi-tenant orgs
│   │   ├── rfq.py                # RFQ workflow
│   │   └── ...
│   ├── modules/                  # Business logic modules
│   │   ├── document_ai/          # OCR, extraction, IMPA matching
│   │   ├── intelligence/         # Price benchmarks, risk, timing
│   │   ├── portiq/               # AI chat with function-calling
│   │   ├── prediction/           # Consumption forecasting
│   │   └── tco/                  # Total Cost of Ownership engine
│   ├── seed.py                   # Database seeder
│   └── seed_data/                # Seed data definitions
├── alembic/versions/             # 16 database migrations
├── apps/web/                     # Next.js 14 frontend
│   ├── app/(dashboard)/          # Buyer portal routes
│   ├── app/(supplier)/           # Supplier portal routes
│   ├── components/               # UI components
│   ├── lib/api/                  # API client functions
│   └── stores/                   # Zustand stores
├── tests/                        # pytest + LLM integration tests
├── celery_app.py                 # Celery configuration
├── Ship/adr/                     # 60 Architecture Decision Records
└── pyproject.toml                # Python project config
```

## API Endpoints (~151 total)

| Module | Prefix | Endpoints |
|--------|--------|-----------|
| Products | `/api/v1/products` | ~15 |
| Categories | `/api/v1/categories` | ~7 |
| Search | `/api/v1/search` | ~5 |
| Organizations | `/api/v1/organizations` | ~17 |
| Suppliers | `/api/v1/suppliers` | ~15 |
| Vessels | `/api/v1/vessels` | ~15 |
| RFQs | `/api/v1/rfqs` | ~24 |
| Predictions | `/api/v1/predictions` | ~6 |
| Intelligence | `/api/v1/intelligence` | ~5 |
| Documents | `/api/v1/documents` | ~6 |
| TCO | `/api/v1/tco` | ~10 |
| PortiQ AI | `/api/v1/portiq` | ~3 |
| Health/Auth | various | ~23 |

API docs available at `http://localhost:8000/docs` (Swagger UI).

## Frontend Routes

**Buyer Portal** (11 routes):
`/` `/products` `/categories` `/search` `/suppliers` `/rfqs` `/rfqs/create` `/rfqs/[id]` `/orders` `/chat` `/login`

**Supplier Portal** (6 routes):
`/supplier` `/supplier/rfqs` `/supplier/rfqs/[id]` `/supplier/rfqs/[id]/quote` `/supplier/orders` `/supplier/profile`

## Seed Data

The seeder populates the database with realistic maritime procurement data:

| Entity | Count |
|--------|-------|
| Categories | 34 |
| Products (IMPA-coded) | 492 |
| Organizations | 8 |
| Users | 14 |
| Supplier Profiles | 5 |
| Vessels | 8 |
| Supplier Products | 197 |
| Price Points | 210 |

## Development Phase Status

| Phase | Name | Status |
|-------|------|--------|
| 0.1 | Database Core (PostgreSQL + pgvector) | Done |
| 0.2 | Backend Architecture (FastAPI modular monolith) | Done |
| 0.3 | Cloud & Auth (AWS, JWT login) | Deferred |
| 0.4 | Hybrid Search & Async (FTS + Celery) | Done |
| 1.1 | Maritime Data Feeds (vessels, ports) | Done |
| 2.1 | Product Data Model (IMPA codes, categories) | Done |
| 2.2 | Catalog Extensibility (JSONB attributes) | Done |
| 3.1 | Multi-tenancy (org-scoped RLS) | Done |
| 3.2 | Vendor Onboarding (supplier KYC) | Done |
| 3.3 | RFQ & Bidding (sealed-bid MVP) | Done |
| 3.4 | TCO & Quote Comparison | Done |
| 4.1 | Predictions (consumption forecasting) | Done |
| 4.2 | Intelligence (price benchmarks, risk) | Done |
| 4.3 | Document AI (extraction, IMPA matching) | Done |
| 6.1 | Web Foundation (Next.js + shadcn/ui) | Done |
| 6.2 | Fleet Manager Portal (buyer dashboard) | Done |
| 6.5 | State & Theming (React Query, dark mode) | Done |
| 6.6 | PortiQ AI Experience (chat + tools) | Done |

**Upcoming**: 0.3 (Cloud & Auth), 2.3 (ML Predictions), 5.x (Finance), 6.4 (Mobile), 7.x (Hardening)

## Testing

```bash
# Unit tests
PYTHONPATH=. .venv/bin/pytest tests/

# Specific module
PYTHONPATH=. .venv/bin/pytest tests/test_document_ai.py
PYTHONPATH=. .venv/bin/pytest tests/test_intelligence_service.py
PYTHONPATH=. .venv/bin/pytest tests/test_prediction_service.py

# TCO module tests
PYTHONPATH=. .venv/bin/pytest src/modules/tco/tests/

# LLM integration tests (requires OPENAI_API_KEY)
PYTHONPATH=. .venv/bin/pytest tests/llm_integration/
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://portiq:changeme@localhost:5432/portiq` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis for Celery |
| `JWT_SECRET` | `CHANGE-ME-IN-PRODUCTION` | JWT signing secret |
| `OPENAI_API_KEY` | - | Required for PortiQ AI chat |
| `BACKEND_URL` | `http://localhost:8000` | Backend URL for Next.js proxy |

## Architecture Decision Records

60 ADRs organized by domain:
- **24 Functional** (FN-001 to FN-024): Business logic and domain features
- **20 Non-Functional** (NF-001 to NF-020): Infrastructure and operations
- **16 UI** (UI-001 to UI-016): Frontend architecture and UX

See [ADR Index](Ship/adr/README.md) for the full list.

## License

Proprietary. All rights reserved.
