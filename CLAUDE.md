# PortiQ Maritime Procurement Platform

## Quick Reference
- **ADR Index**: `/Ship/adr/README.md`
- **Phase Config**: `/Ship/adr/.phase-config.json`
- **Current Phase**: 0.1 (Database Core)

## Project Overview
PortiQ is a B2B maritime ship chandlery platform targeting the $95B global market. It features an AI-native UX with conversation-first paradigm.

## Key Decisions (from ADRs)
- **Product Identification**: IMPA 6-digit codes as primary product identifier (FN-001)
- **Database**: PostgreSQL with pgvector for semantic search (NF-001, NF-002)
- **Architecture**: FastAPI modular monolith (NF-006)
- **Document AI**: Confidence-gated review (95%+ auto, 80-95% quick, <80% full) (FN-009)
- **UX Paradigm**: PortiQ AI-native conversation-first interfaces (UI-013 through UI-016)

## ADR Structure (60 Total)
- **Functional (FN-001 to FN-024)**: Business logic and domain features
- **Non-Functional (NF-001 to NF-020)**: Infrastructure, performance, security
- **UI (UI-001 to UI-016)**: Frontend architecture and user experience

## Phase Validation
Run `/Ship/adr/scripts/phase-validator.sh context` to see current phase requirements.
Run `/Ship/adr/scripts/phase-validator.sh validate` to validate changes against phase.

## Development Phases
| Phase | Focus | Key ADRs |
|-------|-------|----------|
| 0.x | Infrastructure | NF-001, NF-002, NF-006, NF-007, NF-011, NF-015 |
| 1.x | Data Ingestion | FN-003, FN-024 |
| 2.x | Prediction Engine | FN-002, NF-002 |
| 3.x | Marketplace | FN-011, FN-012, FN-013, FN-014 |
| 4.x | Document AI | FN-006, FN-007, FN-008, FN-009, FN-010 |
| 5.x | Finance | FN-016, FN-017, FN-018 |
| 6.x | UX | UI-013, UI-014, UI-015, UI-016 |
| 7.x | Hardening | NF-015, NF-016, NF-017, NF-018, NF-019, NF-020 |

## For Teammates

### Guidelines
- Each ADR is the source of truth for that component
- Check validation checklist in `.phase-config.json` before marking tasks complete
- Use descriptive variable names
- Never implement mock data - real functionality or TODO comments only

### Directory Ownership (Avoid File Conflicts)
When working in parallel, teammates should own specific directories:
- Backend API: `/src/modules/{module-name}/`
- Database: `/src/database/` or `/alembic/`
- Models: `/src/models/`
- Frontend Web: `/apps/web/`
- Mobile: `/apps/mobile/`
- Shared types: Coordinate with Lead before modifying

### Reading ADRs
ADRs are located at `/Ship/adr/`:
- Functional: `/Ship/adr/functional/ADR-FN-XXX-*.md`
- Non-Functional: `/Ship/adr/non-functional/ADR-NF-XXX-*.md`
- UI: `/Ship/adr/ui/ADR-UI-XXX-*.md`

### Key Technologies
- **Backend**: FastAPI, Python, SQLAlchemy 2.0 (async)
- **Database**: PostgreSQL 16+, pgvector, TimescaleDB
- **Migrations**: Alembic
- **Search**: Meilisearch, pgvector semantic search
- **Queue**: Celery with Redis
- **Frontend**: Next.js 14+ (App Router), shadcn/ui, React Query
- **Mobile**: React Native with Expo
- **Cloud**: AWS Mumbai (ap-south-1)

## Agent Teams Plan
For full Agent Teams configuration and workflows, see:
`/Users/arunmenon/.claude/plans/twinkly-squishing-zephyr.md`
