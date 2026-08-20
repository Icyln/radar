# Production Deployment

This document describes Radar's current production topology: Render + Supabase PostgreSQL + GitHub Actions + Telegram.

## 1. Database: Supabase

Use the PostgreSQL connection string provided for the intended runtime. Configure `DATABASE_URL` in Render and as a GitHub Actions repository secret.

Radar uses conservative application-side pooling by default:

```env
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=5
DATABASE_POOL_TIMEOUT_SECONDS=10
DATABASE_POOL_RECYCLE_SECONDS=300
```

Adjust these only after measuring actual Supabase connection usage.

Run migrations before or as part of a controlled backend deployment:

```bash
cd backend
alembic upgrade head
```

## 2. Backend: Render

Minimum production configuration:

```env
ENVIRONMENT=production
DATABASE_URL=...
JWT_SECRET=...
FRONTEND_URL=https://YOUR-FRONTEND-HOST
TELEGRAM_BOT_TOKEN=...
TELEGRAM_BOT_USERNAME=...
TELEGRAM_WEBHOOK_SECRET=...
TELEGRAM_REQUIRE_WEBHOOK_SECRET_IN_PRODUCTION=true
```

`JWT_SECRET` must be at least 32 characters and must not use the development default.

When Telegram is enabled, 0.8.0 intentionally refuses production startup without `TELEGRAM_WEBHOOK_SECRET`.

Recommended Render start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## 3. Telegram webhook

After deploying the backend and setting the secret, configure the Telegram webhook with the supplied script:

```bash
cd backend
python -m app.scripts.set_telegram_webhook
```

Verify the user connection from the Radar Settings page with **Send test**.

## 4. GitHub Actions secrets and variables

Required repository secrets for scheduled workers:

- `DATABASE_URL`
- `TELEGRAM_BOT_TOKEN`

Optional repository variables are used for discovery-feed configuration. The checked-in workflows intentionally cap worker concurrency at 3.

Scheduled monitoring currently runs at minute 7 and 37 each hour. Source discovery runs every six hours.

## 5. Frontend

Set these server-side variables on the Next.js host:

```env
RADAR_API_URL=https://YOUR-RENDER-SERVICE.onrender.com
RADAR_SESSION_MAX_AGE_SECONDS=3600
RADAR_BFF_MAX_REQUEST_BYTES=262144
RADAR_BFF_UPSTREAM_TIMEOUT_MS=20000
RADAR_BFF_WIDE_SEARCH_TIMEOUT_MS=60000
```

Do not place backend secrets in `NEXT_PUBLIC_*` variables.

## 6. Pre-deploy checklist

- [ ] Supabase backup/restore options are understood.
- [ ] `alembic upgrade head` succeeds against the target database.
- [ ] Render has the strong JWT secret.
- [ ] Render has `TELEGRAM_WEBHOOK_SECRET` when Telegram is enabled.
- [ ] `FRONTEND_URL` exactly matches the production frontend origin.
- [ ] GitHub Actions secrets point to the production database/bot.
- [ ] Backend tests pass.
- [ ] Frontend lint, typecheck, and production build pass in CI.
- [ ] Scheduled Monitoring succeeds once with `workflow_dispatch`.
- [ ] Source Discovery succeeds once with `workflow_dispatch`.
- [ ] Telegram **Send test** succeeds from a linked user account.
- [ ] Admin **System status** shows healthy/recent runs after the workflows complete.
