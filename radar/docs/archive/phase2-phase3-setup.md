# Radar Phase 2 + Phase 3 — No-Docker Upgrade and Setup Guide

This guide assumes Phase 0 and Phase 1 are already working on a machine where PostgreSQL is installed directly on the operating system. **Docker is not required anywhere in this guide.**

Phase 2 adds the complete multi-user monitoring core. Phase 3 adds the authenticated FastAPI management API.

## 1. What this upgrade adds

Phase 2:

- Lever collector
- Ashby collector
- users
- job profiles
- deterministic matching
- persistent job matches
- saved/ignored state
- per-user Telegram connections
- short-lived one-time Telegram link tokens
- per-user notification outbox/idempotency
- monitoring priorities

Phase 3:

- registration/login/JWT authentication
- ownership checks
- job-profile CRUD API
- matched/saved/ignored jobs API
- save/ignore actions
- dashboard summary API
- company management API for administrators
- Telegram linking endpoints
- Telegram `/start <token>` webhook handling
- Telegram Save/Ignore callback handling
- health/readiness endpoints

The web dashboard UI is still Phase 4. For Phase 3, use Swagger at `/docs`, PowerShell, curl, Postman, or another API client.

---

## 2. Back up before upgrading

Your Phase 0/1 PostgreSQL database can be upgraded in place. Do not delete it.

Optional PostgreSQL backup from PowerShell/Command Prompt if `pg_dump` is available:

```powershell
pg_dump -U radar -d radar -F c -f radar-before-phase23.backup
```

Your current Phase 1 `companies`, `jobs`, `crawler_logs`, and `notifications` data is preserved by the Phase 2/3 migration.

---

## 3. Replace/update the project files

Copy the new repository files over your existing Radar checkout, or use the new archive as the project folder.

Do **not** overwrite your real `.env` with `.env.example`.

The old `.env` remains useful; you only need to add the new Phase 3 settings described below.

---

## 4. Activate the existing Python virtual environment

From PowerShell:

```powershell
cd C:\Users\User\radar\backend
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, Command Prompt activation is:

```cmd
cd C:\Users\User\radar\backend
.venv\Scripts\activate.bat
```

Verify:

```powershell
python --version
```

Radar supports Python 3.10+.

---

## 5. Install the Phase 2/3 backend dependencies

From `radar\backend`:

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

New important dependencies include:

- `argon2-cffi` for Argon2 password hashing
- `PyJWT` for access tokens

---

## 6. Update `.env`

Open `C:\Users\User\radar\.env` and retain your existing working values.

Add or update:

```dotenv
ENVIRONMENT=development
DATABASE_URL=postgresql+psycopg://radar:YOUR_PASSWORD@localhost:5432/radar

JWT_SECRET=PUT_A_RANDOM_SECRET_HERE
JWT_ACCESS_TOKEN_MINUTES=60
ADMIN_EMAILS=your-email@example.com

FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000

TELEGRAM_BOT_TOKEN=YOUR_EXISTING_BOT_TOKEN
TELEGRAM_BOT_USERNAME=your_bot_username_without_at_sign
TELEGRAM_WEBHOOK_SECRET=PUT_ANOTHER_RANDOM_SECRET_HERE
TELEGRAM_LINK_TOKEN_MINUTES=10
TELEGRAM_SENDING_STALE_MINUTES=10
```

### Generate `JWT_SECRET`

Do not invent a short password manually. Generate a random secret:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Example output format:

```text
4b3f...64 hexadecimal characters total...
```

Copy the complete generated output into:

```dotenv
JWT_SECRET=...
```

Generate a second independent value for:

```dotenv
TELEGRAM_WEBHOOK_SECRET=...
```

### `ADMIN_EMAILS`

For a fresh Phase 3 user, set the email that should be administrator before registering:

```dotenv
ADMIN_EMAILS=me@example.com
```

Multiple administrators can be comma separated:

```dotenv
ADMIN_EMAILS=me@example.com,other@example.com
```

If you already registered before adding the email, promote the account later:

```powershell
python -m app.scripts.set_admin --email me@example.com
```

Revoke administrator access:

```powershell
python -m app.scripts.set_admin --email me@example.com --revoke
```

---

## 7. Apply the Phase 2/3 PostgreSQL migration

Still inside `radar\backend`:

```powershell
alembic current
alembic upgrade head
alembic current
```

Expected final revision:

```text
0002_phase2_phase3
```

The migration adds these tables without deleting Phase 1 jobs:

```text
users
job_profiles
job_matches
user_job_states
telegram_connections
telegram_link_tokens
```

It also upgrades `notifications` with per-user delivery identity.

If migration fails, do not manually create the new tables. Fix the connection/problem and rerun Alembic.

---

## 8. Run backend tests

```powershell
pytest
```

The supplied Phase 2/3 repository should report all tests passing.

Also run:

```powershell
python -m compileall app
```

If Ruff is installed through the dev dependencies:

```powershell
ruff check .
```

---

## 9. Frontend lint fix from Phase 1

Next.js may regenerate `frontend\next-env.d.ts` with a line similar to:

```text
/// <reference path="./.next/types/routes.d.ts" />
```

That is a generated Next.js file and should not be hand-edited. The updated `.eslintrc.json` ignores `next-env.d.ts`, so this generated declaration no longer fails `npm run lint`.

Run:

```powershell
cd C:\Users\User\radar\frontend
npm run lint
npm run typecheck
npm run build
```

Then return to the backend:

```powershell
cd C:\Users\User\radar\backend
```

---

## 10. Start FastAPI

```powershell
uvicorn app.main:app --reload
```

Verify:

```text
http://localhost:8000/health
http://localhost:8000/ready
```

Development API documentation:

```text
http://localhost:8000/docs
```

Use `/docs` for the easiest Phase 3 manual testing.

---

## 11. Register your first Radar account

In Swagger:

1. Open `POST /api/v1/auth/register`.
2. Click **Try it out**.
3. Submit:

```json
{
  "email": "me@example.com",
  "password": "choose-a-long-password"
}
```

The response contains:

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "user": {
    "id": "...",
    "email": "me@example.com",
    "is_active": true,
    "is_admin": true
  }
}
```

Your password is stored only as an Argon2 hash.

### Swagger authorization

At the top of Swagger, click **Authorize** and paste only the access token value. Swagger supplies the Bearer scheme for protected routes.

You can verify the current account with:

```text
GET /api/v1/auth/me
```

---

## 12. Create a real job profile

Use:

```text
POST /api/v1/job-profiles
```

Example:

```json
{
  "name": "Remote Backend Engineering",
  "enabled": true,
  "job_titles": [
    "Backend Engineer",
    "Python Engineer",
    "Software Engineer"
  ],
  "locations": [
    "Remote",
    "Singapore"
  ],
  "work_modes": [
    "REMOTE",
    "HYBRID"
  ],
  "excluded_keywords": [
    "Senior Director",
    "Staff Manager"
  ]
}
```

When a profile is created, Radar evaluates currently active stored jobs and creates matching records. It does **not** flood Telegram with alerts for old baseline jobs.

List profiles:

```text
GET /api/v1/job-profiles
```

Update:

```text
PATCH /api/v1/job-profiles/{profile_id}
```

Delete:

```text
DELETE /api/v1/job-profiles/{profile_id}
```

Ownership is enforced in the backend. One user cannot retrieve or edit another user's profile by changing the UUID.

---

## 13. View matched jobs

Default matched jobs:

```text
GET /api/v1/jobs
```

Saved:

```text
GET /api/v1/jobs?view=saved
```

Ignored:

```text
GET /api/v1/jobs?view=ignored
```

Closed matched jobs:

```text
GET /api/v1/jobs?status=CLOSED
```

Save a job:

```text
PUT /api/v1/jobs/{job_id}/state
```

Body:

```json
{
  "state": "SAVED"
}
```

Ignore instead:

```json
{
  "state": "IGNORED"
}
```

Clear saved/ignored state:

```json
{
  "state": null
}
```

Radar uses one row per user/job, so a job cannot be simultaneously SAVED and IGNORED.

---

## 14. Dashboard API

Use:

```text
GET /api/v1/dashboard/summary
```

It returns operational data such as:

- active profiles
- active monitored companies
- jobs discovered for your matches today
- matches today
- alerts sent today
- last successful crawler run
- recent matching jobs

No fake analytics are generated.

---

## 15. Company administration

Any authenticated user can inspect configured companies:

```text
GET /api/v1/companies
```

Administrator accounts can add companies:

```text
POST /api/v1/companies
```

Example Greenhouse:

```json
{
  "name": "Cloudflare",
  "website": "https://www.cloudflare.com",
  "career_url": "https://www.cloudflare.com/careers/",
  "ats_provider": "GREENHOUSE",
  "ats_identifier": "cloudflare",
  "monitoring_priority": "HIGH",
  "active": true
}
```

You can still seed from the terminal. The seeder now accepts all three providers:

```powershell
python -m app.scripts.seed_company --provider greenhouse --name "Cloudflare" --ats-identifier cloudflare --website "https://www.cloudflare.com" --career-url "https://www.cloudflare.com/careers/" --priority high
```

Lever identifiers are the site segment in a public URL such as:

```text
https://jobs.lever.co/{SITE}
```

Ashby identifiers are the final job-board path segment:

```text
https://jobs.ashbyhq.com/{JOB_BOARD_NAME}
```

Do not guess identifiers. Verify the public board first.

---

## 16. Run all ATS collectors manually

Monitor one company by ATS identifier:

```powershell
python -m app.workers.monitor --ats-identifier cloudflare
```

Monitor only high-priority companies:

```powershell
python -m app.workers.monitor --priority high
```

Normal priority:

```powershell
python -m app.workers.monitor --priority normal
```

Low priority:

```powershell
python -m app.workers.monitor --priority low
```

With no filter, Radar processes every active configured company:

```powershell
python -m app.workers.monitor
```

The same downstream pipeline is used for Greenhouse, Lever, and Ashby.

---

## 17. Telegram linking in Phase 3

Phase 1 used one manually configured `PHASE1_TELEGRAM_CHAT_ID`. Phase 2/3 introduces a secure user-specific linking flow.

Required `.env` values:

```dotenv
TELEGRAM_BOT_TOKEN=your-real-botfather-token
TELEGRAM_BOT_USERNAME=your_bot_username_without_at_sign
TELEGRAM_WEBHOOK_SECRET=random-secret
```

### Important local-development limitation

Telegram cannot send a webhook to `http://localhost:8000` from the public internet.

You have three practical choices:

1. Keep using the Phase 1 direct chat-ID smoke test locally.
2. Use a secure HTTPS tunnel for local webhook testing.
3. Test the Phase 3 linking flow after deploying FastAPI to Render with a public HTTPS URL.

The production architecture expects option 3.

---

## 18. Configure the Telegram webhook after deploying FastAPI

Suppose Render gives you:

```text
https://your-radar-api.onrender.com
```

Set:

```dotenv
BACKEND_URL=https://your-radar-api.onrender.com
```

Deploy/restart the backend with the same Telegram environment variables.

Then run from a machine with those environment variables configured:

```powershell
python -m app.scripts.set_telegram_webhook
```

Radar registers:

```text
https://your-radar-api.onrender.com/api/v1/telegram/webhook
```

The configured `TELEGRAM_WEBHOOK_SECRET` is sent as Telegram's webhook secret token and verified by Radar for incoming webhook requests.

---

## 19. Connect your Radar account to Telegram

While authenticated, call:

```text
POST /api/v1/telegram/link-token
```

Response example:

```json
{
  "deep_link": "https://t.me/your_bot?start=ONE_TIME_TOKEN",
  "expires_at": "2026-08-13T...Z"
}
```

Open the returned `deep_link`.

Telegram sends:

```text
/start ONE_TIME_TOKEN
```

Radar verifies that the token:

- exists
- has not expired
- has not already been used
- belongs to the Radar user that requested it

Radar then binds the Telegram user/chat to that Radar account and consumes the token.

Check connection status:

```text
GET /api/v1/telegram/connection
```

Disconnect:

```text
DELETE /api/v1/telegram/connection
```

---

## 20. Telegram job buttons

Per-user job alerts include:

- **Open Job**
- **Save**
- **Ignore**

`Save` and `Ignore` callbacks identify the Telegram account through the verified connection and enforce that the linked Radar user has a match for the job. Repeated clicks are safe.

---

## 21. How Phase 2 notifications work

Normal Phase 2/3 flow:

```text
ATS collector
  -> normalized job
  -> dedup/lifecycle
  -> matching engine
  -> JobMatch
  -> verified TelegramConnection
  -> Notification outbox row
  -> Telegram
```

Notification uniqueness is enforced at the database layer for user/job/channel and job/channel/recipient.

If a worker crashes with a notification in `SENDING`, it becomes eligible for recovery after `TELEGRAM_SENDING_STALE_MINUTES`. This provides practical at-least-once processing while minimizing duplicate user alerts. As with any external API, a crash after Telegram accepted a message but before PostgreSQL recorded `SENT` can still create a rare duplicate on stale-send recovery; the tradeoff is documented rather than pretending distributed exactly-once delivery exists.

---

## 22. Verify database records manually

Recent crawler runs:

```sql
SELECT
    started_at,
    ats_provider,
    status,
    jobs_received,
    jobs_new,
    jobs_updated,
    jobs_closed,
    matches_created,
    notifications_sent
FROM crawler_logs
ORDER BY started_at DESC
LIMIT 20;
```

Users/profiles:

```sql
SELECT id, email, is_active, is_admin, created_at
FROM users
ORDER BY created_at DESC;

SELECT id, user_id, name, enabled, job_titles, locations, work_modes
FROM job_profiles
ORDER BY created_at DESC;
```

Matches:

```sql
SELECT user_id, job_profile_id, job_id, matched_at, match_reason
FROM job_matches
ORDER BY matched_at DESC
LIMIT 50;
```

Telegram connections:

```sql
SELECT user_id, telegram_user_id, telegram_chat_id, username, verified, connected_at
FROM telegram_connections;
```

Notifications:

```sql
SELECT user_id, job_id, channel, status, attempt_count, sent_at, error_message
FROM notifications
ORDER BY created_at DESC
LIMIT 50;
```

---

## 23. Recommended end-to-end Phase 2/3 test

1. Run `alembic upgrade head`.
2. Start FastAPI.
3. Register your user.
4. Make the user admin if needed.
5. Confirm Cloudflare remains configured.
6. Create a profile that matches one or more Cloudflare jobs.
7. Call `GET /api/v1/jobs` and confirm backfilled matches appear.
8. Save one job, then ignore it, and confirm only one state exists.
9. Run the monitor twice and confirm duplicate jobs/matches are not created.
10. Add a verified Telegram connection after deployment.
11. When a genuinely new matching job appears, confirm exactly one notification row is created and delivered.
12. Click Save/Ignore in Telegram and verify `user_job_states` changes.

---

## 24. Current phase boundary

After this upgrade:

- Phase 0: complete
- Phase 1: complete
- Phase 2: complete
- Phase 3: complete
- Phase 4 web management UI: not yet implemented
- Phase 5 scheduled GitHub Actions monitoring: not yet implemented
- Phase 6 discovery/hardening: not yet implemented

Do not start Phase 5 by making the Render API part of the monitoring path. Workers continue to talk directly to PostgreSQL and Telegram.
