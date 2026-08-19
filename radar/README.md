# Radar

Radar is a small, dependable job-intelligence and early-warning system. This repository now contains **Phase 0 through Phase 7D** of the master engineering specification.

## No-Docker local development

Docker is not required. PostgreSQL is installed and managed directly on your operating system.

Start here:

- [`docs/setup-no-docker.md`](docs/setup-no-docker.md) — original Phase 0/1 local setup and real Cloudflare Greenhouse smoke test
- [`docs/phase2-phase3-setup.md`](docs/phase2-phase3-setup.md) — detailed Phase 2/3 upgrade, API, matching, authentication, and Telegram-linking guide
- [`docs/phase4-setup-deployment.md`](docs/phase4-setup-deployment.md) — dashboard setup, local acceptance testing, and Vercel deployment
- [`docs/phase4-3-two-mode-coverage.md`](docs/phase4-3-two-mode-coverage.md) — Watchlist/Wide Search upgrade, Detected jobs, migration, and acceptance test
- [`docs/phase5-automated-monitoring.md`](docs/phase5-automated-monitoring.md) — GitHub Actions scheduling, repository secrets, batching, sharding, production smoke tests, and operational queries
- [`docs/phase6-source-discovery.md`](docs/phase6-source-discovery.md) — targeted ATS discovery, validation/promotion, user requests, bulk import, and discovery workflow
- [`docs/phase6b-system-discovery.md`](docs/phase6b-system-discovery.md) — zero-input system feeds, automatic registry growth, and promoted-source revalidation
- [`docs/phase6c-freshness.md`](docs/phase6c-freshness.md) — freshness-aware matching, baseline evidence, Detected filters, and notification hardening
- [`docs/phase7-active-hiring-discovery.md`](docs/phase7-active-hiring-discovery.md) — profile-driven fresh hiring discovery, ATS validation, and safe first-sync evidence
- [`docs/phase7-setup.md`](docs/phase7-setup.md) — Phase 7 migration, settings, local/GitHub acceptance testing, and dashboard checks
- [`docs/phase7-change-manifest.md`](docs/phase7-change-manifest.md) — exact Phase 7 behavior, changed areas, verification, and packaging notes
- [`docs/phase7c-wide-job-ingestion.md`](docs/phase7c-wide-job-ingestion.md) — Phase 7C job-first Wide Search and user-side acceptance test
- [`docs/phase7d-telegram-delivery.md`](docs/phase7d-telegram-delivery.md) — Phase 7D immediate Wide alerts, Telegram preview testing, and delivery status
- [`docs/postgresql-manual-setup.sql.example`](docs/postgresql-manual-setup.sql.example) — local role/database creation example

## Implemented phases

### Phase 0 — Foundation

- Next.js + TypeScript + Tailwind foundation
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL configuration
- test/lint/build configuration
- environment template and documentation

### Phase 1 — Minimum job detection

- Company / Job / CrawlerLog models
- Greenhouse collector
- normalization
- deterministic fingerprinting
- database deduplication
- lifecycle handling
- manual monitor command
- Telegram delivery
- persisted notification state

### Phase 2 — Complete monitoring core

- Lever collector
- Ashby collector
- User model
- JobProfile model
- deterministic matching engine
- JobMatch persistence
- unified saved/ignored state
- TelegramConnection
- one-time TelegramLinkToken
- per-user notification outbox/idempotency
- HIGH / NORMAL / LOW monitoring filters
- baseline-safe matching behavior

### Phase 3 — Backend API

- Argon2 password hashing
- JWT authentication
- protected API dependencies
- user ownership checks
- job-profile CRUD
- matched/saved/ignored jobs API
- save/ignore state actions
- dashboard summary
- authenticated company inspection
- administrator company creation/update
- Telegram link-token API
- Telegram webhook `/start` handling
- Telegram Save/Ignore callback handling
- `/health` and `/ready`

### Phase 4 — Web dashboard

- register/login UI
- HttpOnly cookie-backed Next.js session proxy
- protected responsive dashboard shell
- dashboard summary/recent matches
- job profile management
- matched/saved/ignored job views
- active/unknown/closed lifecycle filters
- save/ignore actions
- monitored company status and admin controls
- account settings
- Telegram connection management
- loading/error/empty states

### Phase 4.3 — Two-mode coverage

- profile coverage: `WATCHLIST` or `WIDE`
- per-user company watchlists
- Watch / Watching company controls
- Watchlist-aware matching/backfill/pruning
- `Matched | Detected | Saved | Ignored` jobs navigation
- paginated/filterable Detected jobs API and UI
- source-scope worker groundwork (`all`, `watchlist`, `registry`)
- watched-company dashboard metric

### Phase 5 — Automated monitoring

- GitHub Actions scheduled monitoring independent of Render
- cost-aware consolidated watchlist/registry schedule
- persistent `monitor_runs` execution records
- due-age scheduling from database state
- bounded batches and bounded async concurrency
- stable deterministic sharding for large registries
- worker trigger / external GitHub run correlation
- source-level overlap protection retained through PostgreSQL advisory locks
- production worker configuration preflight
- CI hardening with current Python/Node setup actions
- partial-company-failure tolerance without hiding fatal worker failures

### Phase 6A — Targeted discovery and validation

- user-submitted company/careers discovery targets
- bounded, SSRF-aware public-page scanning
- Greenhouse / Lever / Ashby URL detection
- persisted source candidate validation states
- validation through the production collector contract
- safe automatic promotion into the company registry as LOW priority
- optional auto-watch for the requesting user
- admin validation queue/retry/manual promotion API and UI
- bulk CSV target import
- daily + manually dispatchable GitHub Actions discovery workflow
- no dependency on Render for discovery execution

Phase 6A grows the registry from supplied company/career targets. Phase 6B adds system-managed bundled/remote discovery feeds so WIDE users no longer need to submit companies themselves. It still deliberately does not pretend the provider APIs offer a global list of all ATS tenants.

### Phase 6B — Automatic registry growth

- bundled starter source catalog ingested on every discovery cycle
- optional public CSV/JSON system feed ingestion
- source provenance (`USER` vs `SYSTEM_FEED`)
- idempotent feed entry deduplication
- stale system target refresh
- automatic retry of old invalid system candidates
- periodic revalidation of promoted ATS sources
- conservative revalidation failures that do not disable a source after one transient error
- admin dashboard metrics for system targets/promotions/revalidation warnings
- GitHub Actions repository variable support for `DISCOVERY_SYSTEM_FEED_URLS`


### Phase 6C — Freshness-aware matching

- profile-level freshness windows (1/3/7/14/30/60/90 days or Any age)
- 30-day strict freshness default for new and migrated profiles
- provider `posted_at` used when available
- post-baseline `first_seen_at` fallback when a provider omits posting time
- initial baseline inventory with no posting date remains UNKNOWN instead of looking fresh
- optional per-profile inclusion of unknown-date baseline jobs
- Matched and dashboard recent jobs re-evaluate current freshness without deleting historical JobMatch records
- Detected page freshness filters, including explicit unknown-date inspection
- notification hardening so only genuinely new post-baseline jobs enqueue user alerts; updated existing jobs may match the dashboard but do not create a fresh-job alert
- users never need to upload company CSVs for Wide Search; system/admin feeds remain an internal registry-growth mechanism

### Phase 7 — Profile-driven active-hiring discovery

- enabled Wide profiles automatically become bounded source-discovery demand
- fresh public hiring signals are filtered by profile title and freshness before direct ATS resolution
- built-in Arbeitnow Europe/UK and Himalayas remote-job signal adapters require no API key
- signal targets remain system-owned; ordinary users never upload company lists or manage ATS identifiers
- aggregator application pages are provenance only; Radar stages exact or bounded guessed Greenhouse/Lever/Ashby tenants and validates their APIs directly
- guessed ATS tenants must contain the external signal title before promotion, preventing company-slug collisions
- hiring signals are discovery seeds only; direct Greenhouse/Lever/Ashby validation remains mandatory before registry promotion
- fresh signal-discovered sources retain LOW base priority but receive a temporary effective-NORMAL monitoring boost (7 days by default)
- external role evidence can safely identify one otherwise-undated baseline job without marking unrelated baseline inventory fresh
- provider `posted_at` remains authoritative over discovery-signal evidence
- first-sync Telegram suppression has one narrow exception for the exact fresh role that caused source discovery
- Source Discovery runs every six hours while Phase-5 ATS monitoring remains on its independent 30-minute cadence

### Phase 7C — Wide job ingestion

- Fresh jobs from configured hiring feeds are persisted and matched immediately for WIDE profiles, even before the employer has a verified registry entry.
- Jobs carry explicit `Wide discovery` vs `Direct ATS` provenance.
- The Jobs page has a signed-in **Refresh Wide Search** action for visible end-to-end testing.
- ATS discovery remains parallel; successful resolution can upgrade an unambiguous WIDE job in place.
- External provider failures are isolated so another provider can still complete the refresh.

### Phase 7D — Wide Search Telegram delivery

- New WIDE matches enqueue the same per-user Telegram outbox used by direct ATS monitoring.
- **Refresh Wide Search** immediately attempts delivery of only the new alerts created by that refresh.
- The refresh result shows Telegram readiness, alerts sent, and any remainder still queued.
- Settings adds **Send test alert**, which sends a real Radar alert preview using the user's latest match when available.
- Settings shows today's sent/pending/failed job-alert delivery counts.
- Scheduled Source Discovery receives `TELEGRAM_BOT_TOKEN`, so background Wide discovery can deliver new matches in the same worker run.
- Existing notification/job identity rules keep repeated Wide refreshes idempotent; a WIDE row upgraded in place to Direct ATS does not create a second match notification.


## Runtime architecture

```text
                         Web/API management
Users -> Next.js -> FastAPI -> PostgreSQL

                       Monitoring critical path
GitHub Actions / manual worker
           |
           v
  Greenhouse / Lever / Ashby
           |
           v
      NormalizedJob
           |
           v
 Dedup + lifecycle -> PostgreSQL
           |
           v
  deterministic matching
           |
           v
 JobMatch + Notification outbox
           |
           v
        Telegram
```

The monitor imports the same domain/database modules directly and never calls FastAPI. A sleeping Render API therefore cannot stop job detection or notification delivery.

## Requirements

Backend/monitoring:

- Python 3.10+
- PostgreSQL installed directly on the OS
- internet access to configured ATS providers and Telegram

Frontend dashboard:

- Node.js supported by Next.js 15
- npm

## Upgrade an existing Phase 0/1 database

```powershell
cd C:\Users\User\radar\backend
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
alembic upgrade head
pytest
```

Expected migration head:

```text
0009_phase7c
```

Then follow [`docs/phase2-phase3-setup.md`](docs/phase2-phase3-setup.md).

## Backend development

```powershell
cd backend
uvicorn app.main:app --reload
```

Endpoints:

- `GET /health`
- `GET /ready`
- development Swagger: `http://localhost:8000/docs`

## Manual monitoring

All active companies:

```powershell
python -m app.workers.monitor
```

One ATS identifier:

```powershell
python -m app.workers.monitor --ats-identifier cloudflare
```

Priority groups:

```powershell
python -m app.workers.monitor --priority high
python -m app.workers.monitor --priority normal
python -m app.workers.monitor --priority low
```

Source scopes:

```powershell
python -m app.workers.monitor --scope all
python -m app.workers.monitor --scope watchlist
python -m app.workers.monitor --scope registry
```


### Bounded / due / sharded manual runs

```powershell
python -m app.workers.monitor --scope watchlist --batch-size 50 --min-age-minutes 25 --max-concurrency 3
python -m app.workers.monitor --scope registry --priority normal --batch-size 50 --min-age-minutes 55
python -m app.workers.monitor --scope registry --priority low --shard-index 0 --shard-count 4 --batch-size 100
```

`--min-age-minutes` uses persisted `last_checked_at` state, so repeated scheduled invocations do not blindly refetch sources that are not due yet.

## GitHub Actions monitoring

The production scheduled workflow is:

```text
.github/workflows/scheduled_monitor.yml
```

It runs one cost-aware worker job at `:07` and `:37` each hour and handles the source tiers with different due ages:

```text
watchlist      ~25 minutes
registry HIGH  ~25 minutes
registry NORMAL ~55 minutes
registry LOW   ~235 minutes
```

Required GitHub repository secrets:

```text
DATABASE_URL
TELEGRAM_BOT_TOKEN
```

Before enabling the schedule, run the production preflight locally or in CI:

```powershell
python -m app.scripts.check_worker_config --require-remote-database --require-telegram
```

See [`docs/phase5-automated-monitoring.md`](docs/phase5-automated-monitoring.md) for the full setup, workflow-dispatch smoke test, monitoring SQL, cost notes, and scaling guidance.

## Phase 6 source discovery

Queue company/career URLs from the dashboard at `/discovery`, or bulk import curated targets, then process them manually with:

```powershell
python -m app.workers.discovery --auto-promote
```

Production discovery is scheduled by `.github/workflows/discovery.yml`. Phase 7 also uses enabled Wide-profile titles to seed fresh active-hiring discovery automatically. See [`docs/phase7-active-hiring-discovery.md`](docs/phase7-active-hiring-discovery.md).

## Seed companies

Greenhouse example:

```powershell
python -m app.scripts.seed_company --provider greenhouse --name "Cloudflare" --ats-identifier cloudflare --website "https://www.cloudflare.com" --career-url "https://www.cloudflare.com/careers/" --priority high
```

The same seeder accepts `--provider lever` and `--provider ashby` when the correct public ATS identifier is known.

## Authentication

Generate a development JWT signing secret:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Place the result in root `.env`:

```dotenv
JWT_SECRET=...
```

Register/login through:

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me
```

Passwords are stored as Argon2 hashes, never plaintext.

## Telegram Phase 2/3

Phase 1's `PHASE1_TELEGRAM_CHAT_ID` remains available as a local smoke-test compatibility path. Normal multi-user notifications use verified `telegram_connections` rows.

After deploying the API to public HTTPS:

```powershell
python -m app.scripts.set_telegram_webhook
```

Authenticated users request a one-time deep link through:

```text
POST /api/v1/telegram/link-token
```

Telegram then delivers `/start <token>` to Radar's webhook. Tokens are random, short-lived, single-use, and stored only as hashes.

## Frontend lint fix

`next-env.d.ts` is generated by Next.js and can include a triple-slash route-types reference. It is now ignored by ESLint rather than manually edited.

```powershell
cd frontend
npm run lint
npm run typecheck
npm run build
```

## Testing

Backend:

```powershell
cd backend
pytest
ruff check .
```

Frontend:

```powershell
cd frontend
npm run lint
npm run typecheck
npm run build
```

The backend tests cover Phase 1 behavior plus Lever/Ashby parsing, matching, match idempotency, authentication, ownership, job-profile CRUD, Watchlist/Wide coverage, Detected pagination/source filtering, saved/ignored exclusivity, administrator company operations, monitor source scopes, due/batch/shard selection, persisted monitor-run grouping/status, scheduled-workflow safety, and Telegram link-token behavior.

## Engineering status

See [`docs/implementation-status.md`](docs/implementation-status.md) for the exact current phase boundary and verification notes.
