# Deployment — Phase 0 through Phase 3

Phase 3 provides the deployable management API. Automated scheduled monitoring remains Phase 5.

## Supabase PostgreSQL

1. Create a Supabase project/database.
2. Obtain the PostgreSQL connection string.
3. Use a SQLAlchemy psycopg URL: `postgresql+psycopg://...`.
4. Set `DATABASE_URL` securely.
5. Run `alembic upgrade head` from a trusted environment.
6. Confirm the migration head is `0002_phase2_phase3`.

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
NEXT_PUBLIC_API_URL=https://<render-service>
```

The frontend remains a Phase-0 foundation/status surface until Phase 4 implements authentication and management screens.

## Monitoring deployment boundary

Phase 5 will add GitHub Actions schedules. Those jobs should receive `DATABASE_URL` and `TELEGRAM_BOT_TOKEN` through GitHub Actions secrets and execute the Python worker directly.

Do not schedule HTTP requests to Render as the monitoring mechanism.

## Production safety

- never commit `.env`
- use generated random JWT/webhook secrets
- never log database passwords, JWT secrets, or Telegram tokens
- run Alembic before code that requires new schema
- keep `/health` non-sensitive
- restrict administrator emails and review company configuration
