# Radar Phase 0 + Phase 1 — Detailed Local Setup Without Docker

> This guide establishes the Phase 0/1 baseline. After it works, continue with [`phase2-phase3-setup.md`](phase2-phase3-setup.md) to upgrade the same PostgreSQL database and backend.

This guide is the primary local setup path for this repository. Docker is **not required anywhere** in Phase 0 or Phase 1.

The minimum setup for testing the real monitoring pipeline is:

- PostgreSQL installed directly on your operating system
- Python 3.10 or newer
- internet access to Greenhouse and Telegram

The frontend is optional for Phase-1 monitoring tests. If your operating system cannot run a suitable Node.js version, you can still run the backend, migrations, Greenhouse monitor, database persistence, lifecycle logic, tests, and Telegram notifications.

---

## 1. Extract the repository

Extract the ZIP somewhere with a simple path, for example:

Windows:

```text
C:\Projects\radar
```

Linux/macOS:

```text
~/projects/radar
```

Open a terminal in the `radar` directory.

---

## 2. Check Python

Run:

```bash
python --version
```

You need Python **3.10 or newer**.

If your system uses `python3` instead of `python`, use `python3` in the commands below.

For an older operating system, install the newest Python release that your OS officially supports, as long as it is Python 3.10+.

---

## 3. Install PostgreSQL directly on your computer

Install PostgreSQL normally using the installer/package method supported by your operating system. Docker is not needed.

Recommended: PostgreSQL 15 or newer. PostgreSQL 14 should also work with the Phase 0/1 code if that is the newest version your operating system supports.

During installation, remember the password you assign to the PostgreSQL administrator account, normally named `postgres`.

Typical defaults are:

```text
host: localhost
port: 5432
admin user: postgres
```

Make sure the PostgreSQL service is running before continuing.

---

## 4. Create the Radar PostgreSQL user and database

Open PostgreSQL's SQL shell (`psql`) or pgAdmin's Query Tool while connected as the PostgreSQL administrator.

Run these SQL statements one at a time:

```sql
CREATE ROLE radar WITH LOGIN PASSWORD 'RadarLocal_ChangeMe_2026';
CREATE DATABASE radar OWNER radar ENCODING 'UTF8';
```

For local development, the password above is usable as-is, but it is public example data. Change it if the machine is shared or reachable by other users.

If the `radar` role already exists, do not create it again. You can reset its password with:

```sql
ALTER ROLE radar WITH PASSWORD 'RadarLocal_ChangeMe_2026';
```

If the `radar` database already exists, do not create it again.

### Verify with psql

If `psql` is available from your terminal:

```bash
psql -h localhost -p 5432 -U radar -d radar -c "SELECT current_database(), current_user;"
```

Enter the password when prompted.

Expected values include:

```text
current_database = radar
current_user     = radar
```

If `psql` is not on your PATH, that is not fatal. You can verify the connection later using Radar's `/ready` endpoint.

---

## 5. Create Radar's `.env` file

At the repository root, copy `.env.example` to `.env`.

Windows Command Prompt:

```bat
copy .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

Open `.env` in a text editor.

For the example PostgreSQL role/database created above, use:

```dotenv
DATABASE_URL=postgresql+psycopg://radar:RadarLocal_ChangeMe_2026@localhost:5432/radar
```

If you picked a different database password, replace only the password portion.

If your password contains URL-special characters such as `@`, `:`, `/`, `#`, or `%`, URL-encode them in `DATABASE_URL`. The easiest local setup is to use a strong URL-safe password made from letters, numbers, `_`, and `-`.

Leave Telegram fields empty for the moment:

```dotenv
TELEGRAM_BOT_TOKEN=
PHASE1_TELEGRAM_CHAT_ID=
```

---

## 6. Create the backend virtual environment

Move into the backend directory:

```bash
cd backend
```

Create the virtual environment:

```bash
python -m venv .venv
```

Activate it.

Windows Command Prompt:

```bat
.venv\Scripts\activate.bat
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

If PowerShell blocks activation because of execution policy, either use Command Prompt or run the Python executables through `.venv\Scripts\python.exe` directly. You do not need to weaken your machine-wide execution policy just for Radar.

Upgrade pip and install Radar:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

---

## 7. Test the backend code before touching the database

Still inside `backend`:

```bash
pytest
ruff check .
```

The tests use an isolated SQLite test database and mocked external HTTP calls, so they do not alter your PostgreSQL database and do not require live Greenhouse/Telegram services.

---

## 8. Create Radar's PostgreSQL tables with Alembic

Still inside `backend`:

```bash
alembic upgrade head
```

This creates the Phase 0/1 tables and enum types in the `radar` database.

Check migration state:

```bash
alembic current
```

You should see revision:

```text
0001_phase0_phase1
```

Do not manually create Radar's application tables. Let Alembic own the schema.

---

## 9. Start and verify the FastAPI backend

Run:

```bash
uvicorn app.main:app --reload
```

In a browser open:

```text
http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Then open:

```text
http://localhost:8000/ready
```

A successful readiness response means the backend can reach your manually installed PostgreSQL database.

Stop the server with `Ctrl+C` when you want to run other terminal commands.

---

# Telegram setup

## 10. Create a Telegram bot and get `TELEGRAM_BOT_TOKEN`

1. Open Telegram.
2. Search for the verified bot named **@BotFather**.
3. Start the chat.
4. Send:

```text
/newbot
```

5. BotFather asks for a display name. Example:

```text
Radar Job Alerts
```

6. BotFather asks for a unique bot username. Use a username Telegram accepts, for example:

```text
my_radar_job_alerts_bot
```

7. BotFather returns an HTTP API token. It looks structurally similar to:

```text
1234567890:AAExampleOnly_DoNotUseThisValue
```

That string is your **real** `TELEGRAM_BOT_TOKEN`.

Do not send the real token to other people, commit it to Git, put it in screenshots, or paste it into public issue trackers. Anyone with the token can control the bot.

Put your actual token in the root `.env` file:

```dotenv
TELEGRAM_BOT_TOKEN=YOUR_REAL_BOTFATHER_TOKEN_HERE
```

The example token in this guide is intentionally invalid; Radar cannot provide a shared real bot token because the token must belong to your own Telegram bot.

---

## 11. Get `PHASE1_TELEGRAM_CHAT_ID` without exposing the token in a browser URL

Telegram bots cannot initiate a private conversation with you. First:

1. Open the bot you just created.
2. Press **Start**, or send:

```text
/start
```

3. Return to the terminal in `backend` with the virtual environment active.
4. Run Radar's helper:

```bash
python -m app.scripts.telegram_chat_id
```

Example output:

```text
Chats seen by this bot:
  chat_id=123456789  type=private  name=Your Name

Copy the correct chat_id into PHASE1_TELEGRAM_CHAT_ID in .env.
```

Use **your actual value**:

```dotenv
PHASE1_TELEGRAM_CHAT_ID=123456789
```

The number above is only a format example. A real private chat ID is unique to your Telegram account/chat, so Radar cannot provide one universal value.

If the helper prints `No chats found`, send another message such as `hello` to your bot and run the helper again.

### Group chat IDs

If you later want Phase 1 alerts in a Telegram group, add the bot to the group, send a message the bot can receive, and run the same helper. Group/supergroup IDs are commonly negative numbers. For personal Phase-1 testing, a private chat is simpler.

---

## 12. Send a direct Telegram configuration test

After both values are in `.env`, run:

```bash
python -m app.scripts.test_telegram
```

You should receive:

```text
✅ Radar Telegram configuration is working.
```

This test does not require a company or job and is the easiest way to verify the credentials first.

---

# Real Greenhouse test company

## 13. Seed Cloudflare using a real Greenhouse board identifier

Cloudflare currently exposes jobs through a Greenhouse board whose board token is:

```text
cloudflare
```

Use this real seed command.

### One-line command — works best on all shells

```bash
python -m app.scripts.seed_company --name "Cloudflare" --ats-identifier cloudflare --website "https://www.cloudflare.com" --career-url "https://www.cloudflare.com/careers/"
```

### Linux/macOS multiline form

```bash
python -m app.scripts.seed_company \
  --name "Cloudflare" \
  --ats-identifier cloudflare \
  --website "https://www.cloudflare.com" \
  --career-url "https://www.cloudflare.com/careers/"
```

### PowerShell multiline form

```powershell
python -m app.scripts.seed_company `
  --name "Cloudflare" `
  --ats-identifier cloudflare `
  --website "https://www.cloudflare.com" `
  --career-url "https://www.cloudflare.com/careers/"
```

The monitor does not scrape the marketing careers page. For Greenhouse it calls the public board API using the `ats_identifier`, conceptually:

```text
https://boards-api.greenhouse.io/v1/boards/cloudflare/jobs?content=true
```

The seed command prints Cloudflare's generated Radar company UUID when successful.

---

## 14. First real Greenhouse database test without Telegram flood

For normal operation, keep these `.env` values:

```dotenv
PHASE1_NOTIFY_ALL_NEW_JOBS=false
PHASE1_NOTIFY_ON_INITIAL_SYNC=false
PHASE1_NOTIFY_TITLE_KEYWORDS=engineer,python,backend
PHASE1_MAX_NOTIFICATIONS_PER_RUN=10
```

Run:

```bash
python -m app.workers.monitor --ats-identifier cloudflare
```

Expected behavior on the first successful run:

1. Radar calls the real Cloudflare Greenhouse board.
2. Current jobs are normalized.
3. New database records are created.
4. The first sync becomes the baseline.
5. No first-sync job alerts are sent by default.

Run the exact same command a second time:

```bash
python -m app.workers.monitor --ats-identifier cloudflare
```

The same jobs should **not** be inserted again. This is the simplest real-world deduplication check.

---

## 15. Optional one-message end-to-end monitor notification test

Do this only if Cloudflare has **not already been synced** into this database, or use a fresh test database.

Temporarily set:

```dotenv
PHASE1_NOTIFY_ALL_NEW_JOBS=true
PHASE1_NOTIFY_ON_INITIAL_SYNC=true
PHASE1_MAX_NOTIFICATIONS_PER_RUN=1
```

Then run:

```bash
python -m app.workers.monitor --ats-identifier cloudflare
```

Radar should persist the fetched jobs and deliver at most one Phase-1 Telegram job notification during that run.

After the test, immediately restore safer normal settings:

```dotenv
PHASE1_NOTIFY_ALL_NEW_JOBS=false
PHASE1_NOTIFY_ON_INITIAL_SYNC=false
PHASE1_MAX_NOTIFICATIONS_PER_RUN=10
PHASE1_NOTIFY_TITLE_KEYWORDS=engineer,python,backend
```

Why this is necessary: Radar intentionally treats a company's very first successful sync as a baseline, so enabling first-sync alerts permanently could flood you with old postings when adding a company that already has many open jobs.

---

## 16. Check the data directly in PostgreSQL

Using `psql`:

```bash
psql -h localhost -p 5432 -U radar -d radar
```

Then run:

```sql
SELECT id, name, ats_provider, ats_identifier, last_successful_check_at
FROM companies;
```

```sql
SELECT title, status, first_seen_at, last_seen_at
FROM jobs
ORDER BY first_seen_at DESC
LIMIT 20;
```

```sql
SELECT status, COUNT(*)
FROM notifications
GROUP BY status
ORDER BY status;
```

```sql
SELECT status, jobs_received, jobs_new, jobs_updated, jobs_closed, notifications_sent, started_at
FROM crawler_logs
ORDER BY started_at DESC
LIMIT 10;
```

Exit `psql` with:

```text
\q
```

---

# Frontend setup (optional for Phase 1)

## 17. Only if your OS can run Node.js

The included Next.js 15 frontend requires Node.js 18.18 or newer at the framework level. A currently supported Node.js release is strongly preferable for real development/deployment.

Check:

```bash
node --version
npm --version
```

If Node works, from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

Quality checks:

```bash
npm run lint
npm run typecheck
npm run build
```

If your operating system cannot run a compatible Node.js version, skip this section. The Phase-1 monitoring system does not depend on the frontend or on a continuously running FastAPI process.

---

# Daily development commands

## Backend

Activate the virtual environment first, then from `backend`:

```bash
pytest
ruff check .
alembic upgrade head
uvicorn app.main:app --reload
python -m app.workers.monitor --ats-identifier cloudflare
```

## Telegram helpers

```bash
python -m app.scripts.telegram_chat_id
python -m app.scripts.test_telegram
```

---

# Common problems

## `connection refused` on port 5432

PostgreSQL is probably not running, is listening on another port, or your `.env` points at the wrong port.

## `password authentication failed for user "radar"`

The password in `DATABASE_URL` does not match the PostgreSQL `radar` role password. Reset it as the PostgreSQL administrator or fix `.env`.

## `database "radar" does not exist`

Create the database in Step 4, or correct the database name in `DATABASE_URL`.

## `alembic` is not recognized

The virtual environment is probably not active or dependencies were not installed. Use:

```bash
python -m alembic upgrade head
```

if needed.

## Telegram helper finds no chat

Open your bot and send `/start` or any message, then retry:

```bash
python -m app.scripts.telegram_chat_id
```

## Telegram says `Unauthorized`

The token is invalid/revoked or copied incorrectly. Get the current token from BotFather and update `.env`.

## Monitor stores jobs but sends no Telegram notification

This may be correct. Check:

```dotenv
TELEGRAM_BOT_TOKEN=...
PHASE1_TELEGRAM_CHAT_ID=...
PHASE1_NOTIFY_TITLE_KEYWORDS=...
PHASE1_NOTIFY_ALL_NEW_JOBS=false
PHASE1_NOTIFY_ON_INITIAL_SYNC=false
```

On the first sync, Radar suppresses job alerts by default. Use `python -m app.scripts.test_telegram` to test Telegram independently.

## `No companies selected`

Seed Cloudflare first:

```bash
python -m app.scripts.seed_company --name "Cloudflare" --ats-identifier cloudflare --website "https://www.cloudflare.com" --career-url "https://www.cloudflare.com/careers/"
```

---

# Recommended order for your first run

1. Install/start PostgreSQL directly on your OS.
2. Create the `radar` role and `radar` database.
3. Copy `.env.example` to `.env` and set `DATABASE_URL`.
4. Create/activate the Python virtual environment.
5. Install backend dependencies.
6. Run `pytest` and `ruff check .`.
7. Run `alembic upgrade head`.
8. Start FastAPI and verify `/health` and `/ready`.
9. Create your Telegram bot with BotFather.
10. Put the bot token in `.env`.
11. Message your bot with `/start`.
12. Run `python -m app.scripts.telegram_chat_id`.
13. Put your chat ID in `.env`.
14. Run `python -m app.scripts.test_telegram`.
15. Seed the real Cloudflare Greenhouse board.
16. Run the monitor once.
17. Run it again and confirm jobs are not duplicated.
18. Configure the Phase-1 notification policy you actually want.
