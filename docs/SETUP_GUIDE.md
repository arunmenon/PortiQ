# PortiQ — Installation & Configuration Guide

## 1. Prerequisites

| Software       | Minimum Version | Notes                                    |
|----------------|-----------------|------------------------------------------|
| Python         | 3.12+           | Required for `asyncio` and type features |
| Node.js        | 18+             | LTS recommended                          |
| PostgreSQL     | 16+             | With extension support                   |
| Redis          | 7+              | Used for Celery broker and cache         |
| Git            | 2.x             |                                          |

Optional:

| Software        | Purpose                              |
|-----------------|--------------------------------------|
| `uv`            | Fast Python package manager (alternative to pip) |
| Docker          | For running PostgreSQL/Redis in containers       |
| `jq`            | Useful for inspecting API JSON responses         |

---

## 2. Backend Setup

### 2.1 Clone & Virtual Environment

```bash
git clone <repository-url> PortiQ
cd PortiQ

# Option A: Using uv (recommended)
uv sync

# Option B: Using pip
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows
pip install -e ".[dev]"
```

### 2.2 Environment Configuration

Create a `.env` file in the project root. All settings are defined in `src/config.py`.

#### Database

| Variable            | Default                                                    | Description                          |
|---------------------|------------------------------------------------------------|--------------------------------------|
| `DATABASE_URL`      | `postgresql+asyncpg://portiq:changeme@localhost:5432/portiq` | Async SQLAlchemy connection string   |
| `DATABASE_URL_SYNC` | `postgresql://portiq:changeme@localhost:5432/portiq`         | Sync connection (seeder, migrations) |

#### Application

| Variable      | Default       | Description                    |
|---------------|---------------|--------------------------------|
| `ENVIRONMENT` | `development` | `development`, `staging`, `production` |
| `PORT`        | `8000`        | Server listen port             |
| `LOG_LEVEL`   | `info`        | Python logging level           |

#### CORS

| Variable       | Default                                       | Description                        |
|----------------|-----------------------------------------------|------------------------------------|
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:8000`  | Comma-separated allowed origins    |

#### Auth (JWT)

| Variable             | Default                  | Description                          |
|----------------------|--------------------------|--------------------------------------|
| `JWT_SECRET_KEY`     | `CHANGE-ME-IN-PRODUCTION`| **Must change for production**       |
| `JWT_ALGORITHM`      | `HS256`                  | JWT signing algorithm                |
| `JWT_EXPIRY_MINUTES` | `60`                     | Token expiry in minutes              |

#### OpenAI

| Variable              | Default   | Description                     |
|-----------------------|-----------|---------------------------------|
| `OPENAI_API_KEY`      | *(empty)* | OpenAI API key for PortiQ AI   |
| `OPENAI_MODEL`        | `gpt-4o`  | Model for AI features           |
| `PORTIQ_MAX_TOKENS`   | `4096`    | Max tokens per AI response      |
| `PORTIQ_MAX_TOOL_CALLS` | `5`    | Max tool calls per conversation |

#### Redis / Celery

| Variable                | Default                    | Description               |
|-------------------------|----------------------------|---------------------------|
| `REDIS_URL`             | `redis://localhost:6379/0` | Redis connection URL      |
| `CELERY_BROKER_URL`     | `redis://localhost:6379/0` | Celery task broker        |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | Celery result store       |

#### AIS — VesselFinder

| Variable                  | Default                            | Description              |
|---------------------------|------------------------------------|--------------------------|
| `VESSEL_FINDER_API_KEY`   | *(empty)*                          | VesselFinder API key     |
| `VESSEL_FINDER_BASE_URL`  | `https://api.vesselfinder.com`     | VesselFinder API base    |

#### AIS — PCS1x

| Variable              | Default                         | Description                |
|-----------------------|---------------------------------|----------------------------|
| `PCS1X_CLIENT_ID`     | *(empty)*                       | PCS1x OAuth client ID      |
| `PCS1X_CLIENT_SECRET` | *(empty)*                       | PCS1x OAuth client secret  |
| `PCS1X_BASE_URL`      | `https://api.pcs1x.gov.in`     | PCS1x API base URL         |

#### Polling Intervals (seconds)

| Variable                        | Default | Description                        |
|---------------------------------|---------|------------------------------------|
| `VESSEL_POSITION_POLL_SECONDS`  | `120`   | Position update polling interval   |
| `VESSEL_ETA_POLL_SECONDS`       | `300`   | ETA recalculation interval         |
| `VESSEL_ARRIVAL_POLL_SECONDS`   | `900`   | Port arrival detection interval    |

#### Quality Thresholds

| Variable                            | Default | Description                              |
|-------------------------------------|---------|------------------------------------------|
| `VESSEL_MAX_POSITION_AGE_SECONDS`   | `3600`  | Max age before position is stale         |
| `VESSEL_MAX_SPEED_KNOTS`            | `50.0`  | Speed sanity check                       |
| `VESSEL_MIN_SIGNAL_CONFIDENCE`      | `0.7`   | Min AIS signal confidence                |

#### Event Outbox

| Variable                     | Default | Description                    |
|------------------------------|---------|--------------------------------|
| `EVENT_OUTBOX_POLL_SECONDS`  | `5`     | Outbox polling interval        |
| `EVENT_OUTBOX_BATCH_SIZE`    | `50`    | Events per outbox poll batch   |

#### Cache TTLs (Redis, seconds)

| Variable                      | Default | Description                      |
|-------------------------------|---------|----------------------------------|
| `VESSEL_POSITION_CACHE_TTL`   | `300`   | Position cache TTL               |
| `VESSEL_ETA_CACHE_TTL`        | `900`   | ETA cache TTL                    |

#### RFQ & Bidding

| Variable                       | Default | Description                       |
|--------------------------------|---------|-----------------------------------|
| `RFQ_AUTO_CLOSE_POLL_SECONDS`  | `60`    | Auto-close deadline check interval|
| `RFQ_DRAFT_TTL_DAYS`           | `30`    | Days before draft RFQs expire    |

#### Intelligence

| Variable                                    | Default | Description                          |
|---------------------------------------------|---------|--------------------------------------|
| `INTELLIGENCE_MV_REFRESH_HOUR`              | `2`     | Hour (UTC) to refresh materialized views |
| `INTELLIGENCE_SUPPLIER_SCORE_REFRESH_HOUR`  | `2`     | Hour (UTC) to refresh supplier scores    |
| `INTELLIGENCE_PRICE_BENCHMARK_DAYS`         | `90`    | Days of data for price benchmarks        |
| `INTELLIGENCE_MIN_QUOTES_FOR_BENCHMARK`     | `3`     | Min quotes needed for benchmark          |

#### Document AI

| Variable                            | Default            | Description                               |
|-------------------------------------|--------------------|-------------------------------------------|
| `AZURE_DI_ENDPOINT`                 | *(empty)*          | Azure Document Intelligence endpoint      |
| `AZURE_DI_API_KEY`                  | *(empty)*          | Azure DI API key                          |
| `AZURE_DI_MODEL_LAYOUT`            | `prebuilt-layout`  | Azure DI layout model                     |
| `AZURE_DI_MODEL_READ`              | `prebuilt-read`    | Azure DI read model                       |
| `EXTRACTION_AUTO_THRESHOLD`         | `0.95`             | Auto-accept confidence threshold (95%+)   |
| `EXTRACTION_QUICK_REVIEW_THRESHOLD` | `0.80`             | Quick-review threshold (80-94%)           |
| `EXTRACTION_BATCH_SIZE`             | `20`               | Extraction batch size                     |

#### Minimal `.env` Example

```bash
# .env — minimal for local development
DATABASE_URL=postgresql+asyncpg://portiq:changeme@localhost:5432/portiq
DATABASE_URL_SYNC=postgresql://portiq:changeme@localhost:5432/portiq
JWT_SECRET_KEY=dev-secret-change-in-prod
REDIS_URL=redis://localhost:6379/0
```

### 2.3 Database Setup

#### Create the Database

```bash
# Connect as superuser
psql -U postgres

# Inside psql:
CREATE USER portiq WITH PASSWORD 'changeme';
CREATE DATABASE portiq OWNER portiq;
\c portiq

# Install required extensions (must be superuser)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "vector";       -- pgvector
CREATE EXTENSION IF NOT EXISTS "ltree";

-- Grant usage
GRANT ALL PRIVILEGES ON DATABASE portiq TO portiq;
\q
```

**Required Extensions Summary:**

| Extension    | Purpose                             |
|--------------|-------------------------------------|
| `uuid-ossp`  | UUID generation (`uuid_generate_v4`) |
| `pgcrypto`   | Cryptographic functions              |
| `pg_trgm`    | Trigram-based fuzzy text search      |
| `btree_gin`  | GIN index support for B-tree types   |
| `vector`     | pgvector for semantic/embedding search |
| `ltree`      | Hierarchical category path queries   |

### 2.4 Run Migrations

```bash
# Run all 22 Alembic migrations
alembic upgrade head

# Verify current migration head
alembic current
```

### 2.5 Seed Data

```bash
python -m src.seed
```

This populates the database with reference data and test users:

**Organizations (8 total):**

| Organization                   | Type     | Slug                  |
|--------------------------------|----------|-----------------------|
| PortiQ Platform                | PLATFORM | `portiq`              |
| Great Eastern Shipping         | BUYER    | `great-eastern`       |
| Shipping Corporation of India  | BUYER    | `sci`                 |
| Ocean Ship Stores              | SUPPLIER | `ocean-ship-stores`   |
| Marine Supplies International  | SUPPLIER | `marine-supplies-intl`|
| Navkar Ship Chandlers          | SUPPLIER | `navkar-chandlers`    |
| Seahawk Marine Supplies        | SUPPLIER | `seahawk-marine`      |
| Bharat Ship Stores             | SUPPLIER | `bharat-ship-stores`  |

**Test Users (14 total, password: `portiq123`):**

| Email                            | Name              | Organization              | Role   |
|----------------------------------|-------------------|---------------------------|--------|
| `admin@portiq.in`                | Platform Admin    | PortiQ Platform           | OWNER  |
| `ops@portiq.in`                  | Platform Ops      | PortiQ Platform           | ADMIN  |
| `rajesh@greateastern.com`        | Rajesh Sharma     | Great Eastern Shipping    | OWNER  |
| `priya@greateastern.com`         | Priya Nair        | Great Eastern Shipping    | MEMBER |
| `amit@greateastern.com`          | Amit Patel        | Great Eastern Shipping    | MEMBER |
| `vikram@sci.co.in`               | Vikram Singh      | Shipping Corp. of India   | OWNER  |
| `deepa@sci.co.in`               | Deepa Menon       | Shipping Corp. of India   | MEMBER |
| `mohammed@oceanshipstores.com`   | Mohammed Khan     | Ocean Ship Stores         | OWNER  |
| `suresh@oceanshipstores.com`     | Suresh Reddy      | Ocean Ship Stores         | MEMBER |
| `chen@marinesupplies.sg`         | Chen Wei          | Marine Supplies Intl      | OWNER  |
| `kishore@navkarchandlers.com`    | Kishore Jain      | Navkar Ship Chandlers     | OWNER  |
| `lakshmi@seahawkmarine.com`      | Lakshmi Iyer      | Seahawk Marine Supplies   | OWNER  |
| `ravi@bharatshipstores.com`      | Ravi Kumar        | Bharat Ship Stores        | OWNER  |
| `anita@bharatshipstores.com`     | Anita Das         | Bharat Ship Stores        | MEMBER |

The seeder also populates: 34 IMPA categories, 28 units of measure, unit conversions, products, supplier profiles, vessels, and supplier product prices.

### 2.6 Start the Backend Server

```bash
uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
```

The API server will be available at `http://localhost:8000`.

---

## 3. Frontend Setup

### 3.1 Install Dependencies

```bash
cd apps/web
npm install
```

### 3.2 Environment Configuration

Create `apps/web/.env.local`:

```bash
BACKEND_URL=http://localhost:8000
```

### 3.3 Start the Dev Server

```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`.

### 3.4 API Proxying

The Next.js middleware (`apps/web/middleware.ts`) proxies all `/api/v1/*` requests to the FastAPI backend. This means:

- Frontend makes requests to `http://localhost:3000/api/v1/...`
- Middleware forwards them to `http://localhost:8000/api/v1/...`
- All headers (including `Authorization`) are preserved
- The `BACKEND_URL` env var controls the proxy target

The frontend API client (`apps/web/lib/api/client.ts`) reads the auth token from either:
- The `auth_token` cookie
- `localStorage` key `auth_token`

It automatically adds the `Authorization: Bearer <token>` header to all requests.

---

## 4. Infrastructure Services

### 4.1 Redis

Redis is required for Celery task queuing and caching.

```bash
# Start Redis (if not using Docker)
redis-server

# Or with Docker
docker run -d --name portiq-redis -p 6379:6379 redis:7-alpine
```

### 4.2 Celery Worker

```bash
celery -A src.celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  -Q default,vessel_tracking,document_ai,exports,rfq_management
```

**Queue List:**

| Queue              | Purpose                                  |
|--------------------|------------------------------------------|
| `default`          | General tasks                            |
| `vessel_tracking`  | AIS position fetch, backfill             |
| `document_ai`      | Document extraction, OCR                 |
| `exports`          | Data export generation (CSV, XLSX, PDF)  |
| `rfq_management`   | Auto-close expired RFQs                  |

### 4.3 Celery Beat (Scheduler)

```bash
celery -A src.celery_app beat --loglevel=info
```

Periodic tasks include:
- Vessel position polling (every 120s)
- Vessel ETA recalculation (every 300s)
- RFQ auto-close check (every 60s)
- Event outbox processing (every 5s)
- Intelligence materialized view refresh (daily at 2:00 UTC)

---

## 5. Optional Services

### 5.1 OpenAI (PortiQ AI)

Set `OPENAI_API_KEY` in `.env` to enable AI-powered features:
- Conversational procurement interface
- Natural language product search
- Intelligent order suggestions

### 5.2 Azure Document Intelligence

Set `AZURE_DI_ENDPOINT` and `AZURE_DI_API_KEY` to enable:
- Requisition document parsing
- Purchase order extraction
- Confidence-gated review routing (auto at 95%+, quick review 80-95%, full review <80%)

### 5.3 AIS Providers

Set either VesselFinder or PCS1x credentials for live vessel tracking:
- **VesselFinder**: `VESSEL_FINDER_API_KEY`
- **PCS1x** (Indian ports): `PCS1X_CLIENT_ID` + `PCS1X_CLIENT_SECRET`

Without these, vessel positions can still be created manually via the API.

---

## 6. Verification Checklist

After completing setup, verify everything is working:

```bash
# 1. Health check
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# 2. API docs load
# Open in browser: http://localhost:8000/api/docs
# Should show Swagger UI with all endpoints

# 3. ReDoc
# Open in browser: http://localhost:8000/api/redoc

# 4. Migration status
alembic current
# Should show the latest migration revision as head

# 5. Frontend loads
# Open in browser: http://localhost:3000
# Should show login page (redirected from / since no auth token)

# 6. API proxy works (via frontend)
curl http://localhost:3000/api/v1/tenancy/roles
# Should return 401 (authentication required) — proves proxy is working
```

---

## 7. Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `relation "xxx" does not exist` | Migrations not run | Run `alembic upgrade head` |
| `extension "vector" is not available` | pgvector not installed | Install pgvector: `apt install postgresql-16-pgvector` or compile from source |
| `extension "ltree" does not exist` | Missing extension | Run `CREATE EXTENSION ltree;` as superuser |
| CORS errors in browser | Frontend origin not in allowlist | Add `http://localhost:3000` to `CORS_ORIGINS` |
| `Connection refused` on port 5432 | PostgreSQL not running | Start PostgreSQL service |
| `Connection refused` on port 6379 | Redis not running | Start Redis or disable Celery |
| `too many clients already` / pool exhaustion | Too many DB connections | Reduce `--workers` count or increase `max_connections` in `postgresql.conf` |
| `UNIQUE constraint violation` during seed | Seed run multiple times | Safe to ignore — seeder uses `ON CONFLICT DO UPDATE` (upsert) |
| `JWTError: Invalid token` | Wrong or expired JWT | Re-generate token with correct `JWT_SECRET_KEY` |
| `ModuleNotFoundError` | Dependencies not installed | Run `pip install -e ".[dev]"` or `uv sync` |
| `alembic.util.exc.CommandError` | Multiple heads | Run `alembic heads` to check, merge if needed |
| Frontend 502 Bad Gateway | Backend not running | Start uvicorn on port 8000 |

---

## 8. Production Notes

- **JWT Secret**: Generate a strong random secret: `python -c "import secrets; print(secrets.token_urlsafe(64))"`
- **Workers**: Use `gunicorn` with `uvicorn.workers.UvicornWorker` for multi-process:
  ```bash
  gunicorn src.app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```
- **CORS**: Restrict `CORS_ORIGINS` to your actual frontend domain(s)
- **Security Headers**: Add a reverse proxy (nginx/Caddy) with HSTS, CSP, X-Frame-Options
- **Database**: Use connection pooling (PgBouncer) for production workloads
- **Environment**: Set `ENVIRONMENT=production` to disable debug features
- **Rate Limiting**: The API applies `60/minute` default rate limit per client IP. Adjust in `src/app.py` if needed.
- **Secrets Management**: Never commit `.env` files. Use a secrets manager (AWS Secrets Manager, Vault) in production.
