# Radar implementation status

Date: 2026-08-19

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
Complete: GitHub Actions monitoring independent of Render, due-age tiers, persistent monitor runs, bounded batches/concurrency, stable sharding, worker preflight, CI, and partial-source failure isolation.

### Phase 6A
Implemented:

- `discovery_targets` queue for company/career/direct ATS URLs
- bounded same-host career-page crawler
- public-network URL/redirect validation to reduce SSRF risk
- Greenhouse, Lever, and Ashby URL recognition
- persisted `source_candidates` validation lifecycle
- deduplicated candidate-to-target links
- source validation through the real production collectors
- automatic promotion of VALID candidates into `companies`
- discovered companies default to active LOW priority
- optional automatic watchlist addition for the requesting user
- authenticated user discovery submission/retry API
- admin candidate queue, retry, manual promotion, and summary API
- dashboard Discovery page
- bulk CSV target import command
- daily/manual GitHub Actions `Source Discovery` workflow
- discovery remains independent of Render

### Phase 6B
Complete:

- bundled system discovery catalog
- optional public CSV/JSON discovery feeds
- `USER` / `SYSTEM_FEED` target provenance
- no-user-input target queuing and deduplication
- system-candidate retry after cooling period
- periodic promoted-source revalidation
- conservative revalidation failure tracking
- automatic registry-growth dashboard metrics
- GitHub Actions `DISCOVERY_SYSTEM_FEED_URLS` repository-variable support


### Phase 6C
Complete:

- per-profile maximum job age with a 30-day default
- strict handling of unknown posting dates
- baseline-import marker on jobs
- first-seen freshness fallback only for post-baseline jobs when ATS publication time is unavailable
- freshness-aware deterministic matching
- current Matched/dashboard views re-evaluate freshness while preserving historical JobMatch rows
- Detected freshness filters
- new-only Telegram enqueueing (updated existing jobs do not masquerade as newly posted alerts)
- user-facing discovery copy clarifies that system registry growth is automatic and company requests are optional


### Phase 7
Complete:

- enabled `WIDE` profiles automatically generate bounded active-hiring discovery demand
- no normal-user CSV/company-list workflow
- public no-key Arbeitnow Europe/UK and Himalayas hiring-signal adapters
- local title + freshness filtering before discovery targets are queued
- persisted signal provenance and role/posting-time hints on discovery targets
- signal targets remain system-owned and deduplicated
- Himalayas/Arbeitnow listing pages are not crawled as HTML source-discovery targets
- direct ATS tenant probes are generated from exact embedded ATS URLs, ATS-family hints, and bounded company-slug/name guesses
- guessed tenants require a matching signal title before promotion to prevent slug-collision false positives
- original Phase-7 HTTP-403 hiring targets are repaired in place on re-ingestion
- supported ATS discovery/collector validation remains mandatory before promotion
- fresh signal-discovered sources retain LOW base priority and receive a temporary effective-NORMAL monitoring boost
- external signal evidence can safely identify one otherwise-undated baseline role
- freshness precedence: `POSTED_AT -> DISCOVERY_SIGNAL -> FIRST_SEEN -> UNKNOWN`
- first-sync Telegram exception is limited to signal-identified new matches
- unrelated/ambiguous baseline inventory remains silent
- discovery GitHub Actions cadence increased from daily to every six hours
- Discovery admin metrics expose Phase-7 targets, promoted sources, and signal-backed jobs

## Phase 7C
Complete:

- WIDE hiring signals are first-class jobs before ATS resolution
- unknown employers can appear in Matched/Detected
- explicit Wide discovery vs Direct ATS provenance
- user-facing Refresh Wide Search action
- idempotent source refresh
- direct ATS promotion can attach and upgrade the same WIDE job in place

## Phase 7D
Complete:

- WIDE match notifications use the existing per-user Telegram outbox
- user-triggered Wide refresh delivers its newly queued alerts immediately when Telegram is connected
- refresh UI reports Telegram delivery outcome
- Settings provides a Telegram alert preview button and sent/pending/failed delivery counts
- Telegram messages visibly identify Wide discovery vs Direct ATS provenance
- scheduled Source Discovery can deliver WIDE alerts using `TELEGRAM_BOT_TOKEN`
- repeated refreshes remain notification-idempotent

## Database migration

Current head:

```text
0009_phase7c
```

Phase 7D does not require a new schema migration; it uses the existing Phase 7C job and notification tables.

## User-side verification target

```text
Settings → Telegram → Send test alert
→ preview arrives in Telegram
→ Jobs → Refresh Wide Search
→ new WIDE jobs appear in Matched
→ refresh summary shows Telegram N sent
→ Telegram receives the new matching jobs
→ refresh again
→ existing jobs do not generate duplicate alerts
→ later ATS upgrade keeps the same Radar job/match rather than intentionally re-alerting it
```

## Automated verification in this build

- backend pytest: 74 passed
- Python compilation: pass
- Alembic head: `0009_phase7c`
- GitHub Actions YAML parsing (`ci.yml`, `scheduled_monitor.yml`, `discovery.yml`): pass
- FastAPI OpenAPI generation: pass (`0.7.3`)
- frontend TypeScript typecheck: pass
- frontend ESLint: pass
- no real `.env`/`.env.local` files packaged
