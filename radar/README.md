# Radar

Radar is a small, dependable job-intelligence and early-warning system. This repository now contains **Phase 0 through Phase 5** of the master engineering specification.

## No-Docker local development

Docker is not required. PostgreSQL is installed and managed directly on your operating system.

Start here:

- [`docs/setup-no-docker.md`](docs/setup-no-docker.md) — original Phase 0/1 local setup and real Cloudflare Greenhouse smoke test
- [`docs/phase2-phase3-setup.md`](docs/phase2-phase3-setup.md) — detailed Phase 2/3 upgrade, API, matching, authentication, and Telegram-linking guide
- [`docs/phase4-setup-deployment.md`](docs/phase4-setup-deployment.md) — dashboard setup, local acceptance testing, and Vercel deployment
- [`docs/phase4-3-two-mode-coverage.md`](docs/phase4-3-two-mode-coverage.md) — Watchlist/Wide Search upgrade, Detected jobs, migration, and acceptance test
- [`docs/phase5-automated-monitoring.md`](docs/phase5-automated-monitoring.md) — GitHub Actions scheduling, repository secrets, batching, sharding, production smoke tests, and operational queries
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

Phase 6 source discovery remains separate: Phase 5 automates monitoring of sources already in the registry.

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
0004_phase5
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
