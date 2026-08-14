# Radar implementation status

Date: 2026-08-14

## Completed

### Phase 0
Complete.

### Phase 1
Complete and verified against real ATS sources and PostgreSQL.

### Phase 2
Complete: Greenhouse/Lever/Ashby collectors, normalized pipeline, users, profiles, deterministic matching, JobMatch persistence, saved/ignored state, Telegram connections, notification outbox, and monitoring priorities.

### Phase 3
Complete: JWT authentication, authorization/ownership, profile/jobs/company APIs, dashboard API, secure Telegram linking/webhook callbacks, and health/readiness endpoints.

### Phase 4
Complete: Next.js authentication/session proxy, protected responsive dashboard, profiles, jobs, company management, settings, Telegram linking UI, and operational states.

### Phase 4.3
Complete: Watchlist/Wide profile coverage, per-user company watchlists, paginated Detected jobs, server-side filtering, watchlist-aware match backfill/pruning, and worker source scopes.

### Phase 5
Implemented:

- GitHub Actions monitoring independent of Render
- consolidated twice-hourly cost-aware scheduled workflow
- watchlist / registry HIGH / NORMAL / LOW due-age tiers
- `monitor_runs` persistence and crawler-log grouping
- due-aware source selection using `last_checked_at`
- bounded batch sizes
- bounded async company concurrency
- stable deterministic source sharding
- production worker configuration preflight
- GitHub run trigger/external-run correlation
- workflow-level concurrency protection plus existing per-company PostgreSQL advisory locks
- partial-source failure tolerance with persisted `PARTIAL` / `FAILED` state
- updated CI for backend and frontend validation

## Database migration

Current head:

```text
0004_phase5
```

`0004_phase5` upgrades `0003_phase4_3` in place. It creates `monitor_runs` and links `crawler_logs` to the enclosing monitor execution without deleting existing users, sources, jobs, matches, notifications, or Telegram connections.

## Automated verification in this build environment

- pytest: 31 passed
- Python compilation: pass
- Alembic PostgreSQL offline SQL generation through `0004_phase5`: pass
- GitHub Actions YAML parsing: pass
- frontend source code unchanged from Phase 4.3; npm dependency installation is unavailable in this build environment, so run `npm run lint`, `npm run typecheck`, and `npm run build` on the target machine/GitHub CI
- Ruff executable unavailable locally because dependency installation is network-restricted; GitHub CI runs `ruff check .`

## Current phase boundary

Not implemented yet:

- Phase 6 ATS source candidate discovery
- automatic Greenhouse/Lever/Ashby source validation/activation
- automatic registry growth for companies not already present in `companies`

Render remains outside the monitoring critical path.
