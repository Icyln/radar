# Radar

Radar is a small, dependable job-intelligence and early-warning system. This repository now contains **Phase 0 through Phase 3** of the master engineering specification.

## No-Docker local development

Docker is not required. PostgreSQL is installed and managed directly on your operating system.

Start here:

- [`docs/setup-no-docker.md`](docs/setup-no-docker.md) — original Phase 0/1 local setup and real Cloudflare Greenhouse smoke test
- [`docs/phase2-phase3-setup.md`](docs/phase2-phase3-setup.md) — detailed Phase 2/3 upgrade, API, matching, authentication, and Telegram-linking guide
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

Phase 4 (web dashboard UI) and Phase 5 (scheduled GitHub Actions monitoring workflows) remain intentionally separate.

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

Frontend foundation:

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
0002_phase2_phase3
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

The backend tests cover Phase 1 behavior plus Lever/Ashby parsing, matching, match idempotency, authentication, ownership, job-profile CRUD flow, saved/ignored exclusivity, administrator company operations, and Telegram link-token behavior.

## Engineering status

See [`docs/implementation-status.md`](docs/implementation-status.md) for the exact current phase boundary and verification notes.
