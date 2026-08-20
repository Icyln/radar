# Radar

Radar is a personal job-monitoring web app that turns a focused job search into a small set of alerts. It combines broad public job discovery with direct company career-source monitoring, matches jobs to each user's preferences, and can deliver new matches to Telegram.

**Current release: 0.8.0**

## What changed in 0.8.0

- Added a public landing page and a dedicated **How to Use** page.
- Simplified the signed-in workspace to **Home, Job Alerts, Jobs, Companies, Settings**.
- Kept technical discovery and monitoring details in an **Admin** section.
- Added workspace-only light/dark mode.
- Replaced user-facing `WIDE` / `WATCHLIST` jargon with one **Job Alert** concept.
- Added product limits designed for a stable 50–100 user deployment.
- Added fair rotation for shared broad-search terms so later users are not permanently starved.
- Added conservative PostgreSQL pooling, request size limits, request IDs, rate limits, and safer discovery fetching.
- Added frontend BFF same-origin protection and security headers.
- Removed generated files, duplicate backend code from the frontend, and the obsolete single-recipient Telegram path.
- Reorganized documentation around the current product instead of development phases.

## Product model

A user creates a **Job Alert** with job titles, locations, work style, and freshness preferences. By default Radar searches broadly. An advanced option can limit an alert to companies the user follows.

Recommended account limits are enforced by the backend:

- 5 active Job Alerts
- 10 Job Alerts total, including paused alerts
- 5 job titles per alert
- 25 active job titles per user

These limits intentionally favor predictable performance and understandable searches over unlimited configuration.

## Architecture

```text
Browser
  |
  v
Next.js frontend / BFF
  |
  v
FastAPI on Render  -----------> Telegram Bot API
  |
  v
PostgreSQL on Supabase
  ^
  |
GitHub Actions workers
  |-- Scheduled company monitoring
  `-- Broad job/source discovery
```

The application remains a modular monolith. For the intended 50–100 users, Redis, Kafka, Celery, and microservices would add operational complexity without a clear stability benefit.

See [docs/architecture.md](docs/architecture.md) for details.

## Repository layout

```text
backend/                 FastAPI API, domain services, workers, migrations, tests
frontend/                Next.js public site, workspace, BFF, UI components
.github/workflows/       CI and scheduled monitoring/discovery
 docs/                   Current operating and engineering documentation
 docs/archive/           Historical phase-based development notes
```

## Local development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'
cp ../.env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000` by default.

### Frontend

```bash
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

The frontend is available at `http://localhost:3000` by default.

Set `RADAR_API_URL` in `frontend/.env.local` to the backend URL. Keep this variable server-only; do not expose secrets through `NEXT_PUBLIC_*` variables.

## Quality checks

```bash
make backend-test
make backend-lint
make frontend-lint
make frontend-typecheck
make frontend-build
```

CI performs backend lint/compile/tests and frontend lint/typecheck/build on every push and pull request.

## Production deployment

The current supported production topology is:

- **Backend:** Render
- **Database:** Supabase PostgreSQL
- **Scheduled workers:** GitHub Actions
- **Notifications:** Telegram
- **Frontend:** any supported Next.js host with `RADAR_API_URL` pointing to Render

Before deploying 0.8.0, confirm the Render service has a strong `JWT_SECRET` and, when Telegram is enabled, a configured `TELEGRAM_WEBHOOK_SECRET`. Production startup intentionally rejects an enabled Telegram configuration without the webhook secret.

See [docs/deployment.md](docs/deployment.md) for the deployment checklist and [docs/operations.md](docs/operations.md) for worker schedules and health checks.

## Documentation

- [User guide](docs/user-guide.md)
- [Architecture](docs/architecture.md)
- [Deployment](docs/deployment.md)
- [Security](docs/security.md)
- [Operations](docs/operations.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Changelog](CHANGELOG.md)

Historical phase-based documents are retained under `docs/archive/` for reference but do not describe the current product contract.
