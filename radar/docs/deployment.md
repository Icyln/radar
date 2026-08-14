# Deployment — Phase 0 through Phase 5

Phase 3 provides the deployable management API. Phase 5 adds scheduled GitHub Actions workers that operate independently of Render.

## Supabase PostgreSQL

1. Create a Supabase project/database.
2. Obtain the PostgreSQL connection string.
3. Use a SQLAlchemy psycopg URL: `postgresql+psycopg://...`.
4. Set `DATABASE_URL` securely.
5. Run `alembic upgrade head` from a trusted environment.
6. Confirm the migration head is `0004_phase5`.

The database remains the authoritative source of monitoring, matching, user state, Telegram linkage, and notification state.

## Render — FastAPI

Root directory:

```text
backend
```

Build command:

```bash
pip install -e .
```

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Required/recommended environment variables:

```text
ENVIRONMENT=production
DATABASE_URL=...
JWT_SECRET=<at least 32 random characters>
FRONTEND_URL=https://<your-vercel-app>
BACKEND_URL=https://<your-render-service>
TELEGRAM_BOT_TOKEN=...
TELEGRAM_BOT_USERNAME=...
TELEGRAM_WEBHOOK_SECRET=...
ADMIN_EMAILS=...
```

Production configuration rejects the default/short JWT secret.

A sleeping Render instance may delay dashboard/API requests or Telegram webhook processing, but it does not stop ATS monitoring because workers never call Render.

## Telegram webhook

Once `BACKEND_URL` is the public HTTPS Render URL, configure the bot webhook:

```bash
cd backend
python -m app.scripts.set_telegram_webhook
```

The endpoint is:

```text
/api/v1/telegram/webhook
```

Set a random `TELEGRAM_WEBHOOK_SECRET`. Radar verifies Telegram's secret-token request header before processing webhook updates.

## Vercel — Next.js

Root directory:

```text
frontend
```

Set:

```text
RADAR_API_URL=https://<render-service>
RADAR_SESSION_MAX_AGE_SECONDS=3600
```

The Phase 4 frontend uses a same-origin Next.js Route Handler proxy. The FastAPI JWT is held in an HttpOnly cookie rather than browser localStorage. `NEXT_PUBLIC_API_URL` is retained only as a compatibility fallback.

After Vercel deployment, update Render `FRONTEND_URL` to the production Vercel origin. See `docs/phase4-setup-deployment.md` for the complete flow.

## GitHub Actions — monitoring workers

The scheduled worker is `.github/workflows/scheduled_monitor.yml`. It executes the Python monitor directly; it does not wake or call Render.

Add these repository secrets in GitHub:

```text
DATABASE_URL
TELEGRAM_BOT_TOKEN
```

The database URL must target the production Supabase PostgreSQL instance. The Telegram token must be the same bot used by the production notification/webhook configuration.

The workflow runs at `:07` and `:37` each hour and applies due-age/batch limits to watchlist, HIGH, NORMAL, and LOW registry sources. Trigger `workflow_dispatch` once after configuration and inspect `monitor_runs` / `crawler_logs` before relying on the schedule.

See `docs/phase5-automated-monitoring.md` for exact setup, smoke tests, SQL, and scaling guidance.

Do not schedule HTTP requests to Render as the monitoring mechanism.

## Production safety

- never commit `.env`
- use generated random JWT/webhook secrets
- never log database passwords, JWT secrets, or Telegram tokens
- run Alembic before code that requires new schema
- keep `/health` non-sensitive
- restrict administrator emails and review company configuration
