# Radar Phase 4.3 — Watchlist + Wide Search Coverage

Phase 4.3 adds the two monitoring coverage modes that sit between the company source registry and deterministic matching.

It does **not** add automatic company discovery yet. The registry is still populated manually/admin-first. Phase 5 will automate scheduling; Phase 6 will expand source discovery and validation.

## What Phase 4.3 adds

- `coverage_mode` on every job profile:
  - `WATCHLIST`
  - `WIDE`
- per-user `user_company_watchlists`
- Watch / Watching controls on the Companies page
- profile coverage selector in create/edit UI
- Watchlist-only matching and backfill behavior
- `Matched | Detected | Saved | Ignored` Jobs tabs
- paginated server-side `Detected` jobs API
- Detected filters for company, ATS provider, work mode, source scope, lifecycle status, and title/company search
- source-scope worker groundwork:
  - `--scope all`
  - `--scope watchlist`
  - `--scope registry`
- an index supporting lifecycle + newest-first detected browsing
- dashboard count for watched companies

## Coverage semantics

### Watchlist

A Watchlist profile can match jobs only from companies the current user explicitly watches.

```text
User watchlist
    ↓
Watched companies
    ↓
Matching profile with coverage=WATCHLIST
    ↓
JobMatch
    ↓
Telegram notification for genuinely new matches
```

Adding a company to the watchlist immediately backfills active jobs from that company against enabled Watchlist profiles. This backfill does not send a historical Telegram flood.

Removing a company from the watchlist removes that company's matches from Watchlist-only profiles. A separate Wide profile can still keep its own match for the same job.

### Wide Search

A Wide profile can match jobs from every active company source already in Radar's registry.

```text
Active source registry
    ↓
Greenhouse / Lever / Ashby jobs
    ↓
Matching profile with coverage=WIDE
    ↓
JobMatch
```

Existing Phase 4.2 profiles are migrated to `WIDE` so the upgrade preserves their current behavior.

## Jobs page semantics

The tabs now mean:

```text
Matched   = jobs matching at least one of my profiles
Detected  = all jobs Radar collected from known sources
Saved     = my saved matched jobs
Ignored   = my ignored matched jobs
```

`Detected` is intentionally read-oriented. Use `Matched` for Save/Ignore actions. This keeps a wide registry from turning into a general job-board workflow.

The Detected page never loads the whole jobs table into React. The backend returns at most 50 rows; the UI uses 24 rows per page.

---

# Upgrade from Phase 4.2

## 1. Back up / preserve secrets

Do not overwrite your real root `.env` or `frontend/.env.local`.

The upgrade adds one PostgreSQL migration and does not delete existing jobs, users, profiles, matches, Telegram links, or notifications.

## 2. Replace project files

Copy the Phase 4.3 repository over your existing Radar checkout, preserving secret environment files.

## 3. Activate backend environment

```powershell
cd C:\Users\User\radar\backend
.\.venv\Scripts\Activate.ps1
```

## 4. Install/update backend package

```powershell
python -m pip install -e ".[dev]"
```

## 5. Confirm the database target

Before migrating, make sure this terminal is pointing at the intended Supabase database:

```powershell
python -c "from app.core.config import get_settings; from sqlalchemy.engine import make_url; u=make_url(get_settings().database_url); print('HOST =',u.host); print('DATABASE =',u.database); print('USERNAME =',u.username)"
```

Do not print or paste your database password.

## 6. Apply the Phase 4.3 migration

```powershell
alembic current
alembic upgrade head
alembic current
```

Expected migration head:

```text
0003_phase4_3
```

The migration creates:

```text
job_profiles.coverage_mode
user_company_watchlists
ix_jobs_status_first_seen
```

Existing profiles receive:

```text
coverage_mode = WIDE
```

## 7. Run backend tests

```powershell
pytest
```

The Phase 4.3 package contains 26 backend tests.

## 8. Restart backend

If you run local FastAPI:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If Render hosts the production API, commit/push the backend changes after the production database migration and let Render redeploy.

## 9. Update/restart frontend

From:

```powershell
cd C:\Users\User\radar\frontend
```

Keep your working `frontend/.env.local`, for example:

```dotenv
RADAR_API_URL=http://127.0.0.1:8000
RADAR_SESSION_MAX_AGE_SECONDS=3600
```

If your local Node networking can reach Render reliably, the URL may instead be the Render HTTPS origin.

Run:

```powershell
npm install
npm run lint
npm run typecheck
npm run build
npm run dev
```

Restart `npm run dev` after any `.env.local` change.

---

# Phase 4.3 acceptance test

## A. Existing profile migration

Open Job Profiles. Existing profiles should show a `Wide search` badge.

In Supabase:

```sql
SELECT name, coverage_mode, enabled
FROM job_profiles
ORDER BY created_at;
```

Expected: previous profiles use `WIDE`.

## B. Watch a company

Open Companies and click `Watch` for one company, for example WebFX.

Verify:

```sql
SELECT u.email, c.name, w.created_at
FROM user_company_watchlists w
JOIN users u ON u.id = w.user_id
JOIN companies c ON c.id = w.company_id
ORDER BY w.created_at DESC;
```

## C. Create Watchlist-only profile

Example:

```text
Name: Watchlist Web Dev
Titles: Web Developer, Frontend Engineer, Full Stack Engineer
Locations: empty
Work modes: empty
Excluded: empty
Coverage: Watchlist only
Enabled: yes
```

Only jobs from your watched companies should appear from this profile.

## D. Create Wide Search profile

Example:

```text
Name: Wide Web Dev
Titles: Web Developer, Frontend Engineer, Full Stack Engineer
Locations: empty
Work modes: empty
Excluded: empty
Coverage: Wide Search
Enabled: yes
```

This profile can match all active companies currently in the registry.

## E. Detected tab

Open:

```text
/jobs?view=detected&status=ACTIVE
```

You should see all collected active jobs, not only matched jobs.

Test filters:

- company
- provider
- work mode
- source scope:
  - All sources
  - My watchlist
  - Other registry sources
- search title/company
- Active / Unknown / Closed
- Previous / Next pagination

## F. Source-scope worker groundwork

All sources:

```powershell
python -m app.workers.monitor --scope all
```

Companies watched by at least one user:

```powershell
python -m app.workers.monitor --scope watchlist
```

Active companies that nobody currently watches:

```powershell
python -m app.workers.monitor --scope registry
```

These scope controls are groundwork for Phase 5 scheduling. Phase 4.3 does not create GitHub Actions schedules yet.

---

# Useful SQL checks

Total detected jobs:

```sql
SELECT status, COUNT(*)
FROM jobs
GROUP BY status
ORDER BY status;
```

Watchlist counts:

```sql
SELECT u.email, COUNT(*) AS watched_companies
FROM user_company_watchlists w
JOIN users u ON u.id = w.user_id
GROUP BY u.email;
```

Matches by profile and coverage:

```sql
SELECT
    u.email,
    p.name,
    p.coverage_mode,
    COUNT(m.id) AS matches
FROM job_profiles p
JOIN users u ON u.id = p.user_id
LEFT JOIN job_matches m ON m.job_profile_id = p.id
GROUP BY u.email, p.id, p.name, p.coverage_mode
ORDER BY u.email, p.name;
```

Detected jobs from watched companies for one user:

```sql
SELECT c.name, j.title, j.status, j.first_seen_at
FROM jobs j
JOIN companies c ON c.id = j.company_id
JOIN user_company_watchlists w ON w.company_id = c.id
JOIN users u ON u.id = w.user_id
WHERE u.email = 'YOUR_RADAR_EMAIL'
ORDER BY j.first_seen_at DESC
LIMIT 50;
```

---

# Phase 5 boundary

Phase 4.3 deliberately separates **coverage** from **scheduling**.

Phase 5 should use the same source registry and worker scopes to automate something like:

```text
watched sources -> frequent workflow
registry sources -> lower-frequency sharded workflows
```

It should also add bounded batches/shards, concurrency controls, GitHub Actions secrets, and CI. No Render request should be required for monitoring.
