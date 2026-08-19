# Phase 7 change manifest

## Goal

Phase 7 turns Wide Search from registry-only matching into profile-driven active-hiring discovery. Normal users create job profiles; they do not maintain company CSVs, ATS identifiers, or source lists.

## Core behavior added

- Enabled Wide profiles generate bounded job-title discovery queries.
- Public hiring signals are filtered for profile title relevance and posting freshness.
- Relevant signals become system-owned discovery targets.
- Radar still requires supported ATS detection and collector validation before a source enters the registry.
- Hiring signals never write directly into the canonical jobs table.
- Fresh signal-discovered companies keep LOW as their stored priority and receive a temporary effective-NORMAL scheduler boost.
- A uniquely identified fresh baseline role can use DISCOVERY_SIGNAL freshness and may notify on the company's first sync.
- Unrelated or ambiguous first-sync baseline roles remain silent.
- Source Discovery runs every six hours; direct ATS monitoring stays on its independent Phase-5 cadence.

## New files

- `backend/alembic/versions/0008_phase7_active_hiring.py`
- `backend/app/discovery/hiring.py`
- `backend/app/services/discovery_signals.py`
- `backend/tests/test_phase7_active_hiring.py`
- `docs/phase7-active-hiring-discovery.md`
- `docs/phase7-setup.md`

## Main modified areas

- discovery service/worker and configuration
- Phase-5 monitor tier selection
- freshness evidence
- company, job, and discovery-target models/schemas
- discovery GitHub Actions workflow
- Wide Search and discovery dashboard copy/observability
- README, architecture, monitoring, and implementation-status docs

## Validation performed

- Backend tests: 62 passed.
- Python compilation: passed.
- Alembic PostgreSQL offline migration generation through `0008_phase7`: passed.
- GitHub Actions YAML parsing: passed for CI, scheduled monitoring, and discovery workflows.
- FastAPI OpenAPI generation: passed at API version 0.7.0.
- Frontend TypeScript typecheck: passed.
- Frontend ESLint: passed.
- Production Next.js build was not completed in this sandbox because the uploaded dependency tree lacks the Linux SWC native package; the build tried to load the missing platform binary. Run `npm ci`/`npm install` on the target machine or CI and then `npm run build`.

## Packaging

The delivery intentionally excludes `frontend/.env.local`, `node_modules`, `.next`, Python caches, and pytest caches.
