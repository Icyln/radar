# Radar Phase 5 — Automated Monitoring

Phase 5 moves the working Phase 4.3 monitoring pipeline from manual commands to GitHub Actions while keeping Render completely outside the monitoring critical path.

## What Phase 5 adds

- scheduled GitHub Actions monitoring
- database-backed `monitor_runs` records that group per-company crawler logs
- bounded company batches
- least-recently-checked rotation so later companies are not starved
- stable UUID-based sharding (`--shard-index` / `--shard-count`)
- bounded company concurrency
- due-age filtering (`--min-age-minutes`)
- workflow concurrency protection plus existing PostgreSQL per-company advisory locks
- worker configuration preflight
- hardened CI
- explicit partial-company-failure semantics

Automatic discovery of companies that do not yet exist in the source registry is still Phase 6.

## Engineering decision

**Decision:** use one scheduled GitHub Actions workflow with four due-aware source tiers instead of separate always-scheduled HIGH, NORMAL, LOW, and watchlist workflows.

**Reason:** Radar is still a near-zero-cost personal system. One runner can install the worker once, then process each tier while PostgreSQL decides which sources are actually due.

**Tradeoffs:** the default private-repository cadence is less aggressive than a dedicated five-minute watchlist workflow, and a very large registry will eventually need more shards/workflows. In return, the initial deployment avoids repeated runner startup/install overhead and remains easy to operate. Per-company PostgreSQL advisory locks preserve overlap safety either way.

**Files affected:** `.github/workflows/scheduled_monitor.yml`, `backend/app/workers/monitor.py`, `backend/app/services/monitor.py`, `backend/app/models/monitor_run.py`, migration `0004_phase5`, CI, and monitoring/deployment documentation.

---

## 1. Upgrade PostgreSQL

Phase 5 adds migration:

```text
0004_phase5
```

It creates:

```text
monitor_runs
crawler_logs.monitor_run_id
```

Run against the same Supabase database used by Render and the monitoring worker:

```powershell
cd C:\Users\User\radar\backend
.\.venv\Scripts\Activate.ps1

alembic upgrade head
alembic current
```

Expected:

```text
0004_phase5
```

No existing users, profiles, jobs, matches, notifications, watchlists, Telegram connections, or crawler logs are deleted.

---

## 2. Run the Phase 5 tests locally

```powershell
cd C:\Users\User\radar\backend
python -m pip install -e ".[dev]"
pytest
```

Phase 5 adds tests for:

- due-age filtering
- least-recently-checked batching
- deterministic sharding
- grouped monitor-run logging
- PARTIAL run status
- SKIPPED run status when nothing is due
- workflow secret/batch/concurrency configuration
- unexpected per-company failure diagnostic completion

Then run:

```powershell
ruff check .
python -m compileall -q app
```

---

## 3. Manual worker commands

Existing commands continue to work:

```powershell
python -m app.workers.monitor
python -m app.workers.monitor --scope watchlist
python -m app.workers.monitor --scope registry
python -m app.workers.monitor --priority high
```

### Bounded batch

```powershell
python -m app.workers.monitor `
  --scope registry `
  --priority normal `
  --batch-size 50
```

The 50 least-recently-checked eligible sources are selected. After they run, their `last_checked_at` values move forward, so later sources naturally rotate into the next batch.

### Due-age filtering

```powershell
python -m app.workers.monitor `
  --scope registry `
  --priority normal `
  --min-age-minutes 55
```

A company is eligible when it has never been checked or its last check is at least 55 minutes old.

### Bounded concurrency

```powershell
python -m app.workers.monitor `
  --scope registry `
  --batch-size 50 `
  --max-concurrency 3
```

Radar processes at most three companies concurrently. Each company still has its own PostgreSQL advisory lock, so overlapping workflows/manual runs cannot normally process the same company simultaneously.

### Stable sharding

For a four-shard registry:

```powershell
python -m app.workers.monitor --scope registry --shard-count 4 --shard-index 0
python -m app.workers.monitor --scope registry --shard-count 4 --shard-index 1
python -m app.workers.monitor --scope registry --shard-count 4 --shard-index 2
python -m app.workers.monitor --scope registry --shard-count 4 --shard-index 3
```

A company UUID always maps to the same shard while `shard_count` remains unchanged. The shard sets do not overlap and their union covers the eligible source set.

Do not change `shard_count` casually during a running multi-shard deployment; changing it intentionally redistributes companies.

---

## 4. GitHub repository secrets

Open the Radar repository on GitHub:

```text
Settings
→ Secrets and variables
→ Actions
→ New repository secret
```

Create these repository secrets.

### `DATABASE_URL`

Use the Supabase Session Pooler URL used by the production worker.

Example shape only:

```text
postgresql://postgres.PROJECT_REF:ENCODED_PASSWORD@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres
```

If a password contains reserved URL characters they must be URL encoded. For example a password ending in `@` must use `%40` inside the URL.

Do not put the database URL directly in a workflow file.

### `TELEGRAM_BOT_TOKEN`

Use the real BotFather token for the same Radar bot already connected to your Render webhook.

The scheduled worker uses the token only for outgoing notifications. It does not call Render.

No `JWT_SECRET`, Render URL, frontend URL, or Telegram webhook secret is required by the scheduled worker.

---

## 5. Worker preflight

Before GitHub Actions runs the monitor it executes:

```bash
python -m app.scripts.check_worker_config --require-telegram --require-remote-database
```

It checks that:

- the database hostname is not localhost
- a Telegram bot token is present

It prints the database hostname but never the password or Telegram token.

You can test the same command locally while your shell is pointed at Supabase:

```powershell
python -m app.scripts.check_worker_config --require-telegram --require-remote-database
```

---

## 6. Scheduled workflow

The active Phase 5 workflow is:

```text
.github/workflows/scheduled_monitor.yml
```

Default schedule:

```text
07 and 37 minutes past every hour (UTC)
```

This is intentionally away from the top of the hour and is a cost/freshness compromise for a small private repository.

Every workflow run executes four bounded source tiers inside the same GitHub runner:

### Watchlist sources

```text
scope = watchlist
batch = 50
minimum age = 25 minutes
concurrency = 3
```

Any company watched by at least one Radar user is eligible regardless of its stored HIGH/NORMAL/LOW priority.

### Non-watched HIGH registry sources

```text
scope = registry
priority = HIGH
batch = 25
minimum age = 25 minutes
```

### Non-watched NORMAL registry sources

```text
scope = registry
priority = NORMAL
batch = 50
minimum age = 55 minutes
```

Because the workflow wakes twice per hour, a NORMAL source generally becomes due about once per hour.

### Non-watched LOW registry sources

```text
scope = registry
priority = LOW
batch = 100
minimum age = 235 minutes
```

LOW sources therefore rotate on an approximately four-hour cadence when capacity allows.

The scheduler is not a real-time system. GitHub may start scheduled runs late, so these are target cadences, not guarantees.

---

## 7. Why there is one scheduled workflow

Radar could create separate cron workflows for watchlist, HIGH, NORMAL, and LOW sources. That would also create separate GitHub runner startups and repeated dependency installation.

Phase 5 instead uses:

```text
one runner wake-up
    ↓
watchlist due batch
    ↓
HIGH registry due batch
    ↓
NORMAL registry due batch
    ↓
LOW registry due batch
```

This is deliberately optimized for the initial near-zero-cost deployment.

The database remains authoritative about when each company was last checked.

---

## 8. GitHub Actions cost note

For private repositories, GitHub-hosted Actions consume the account's included monthly minutes. Public repositories using standard GitHub-hosted runners do not consume those private-repository included minutes.

The default twice-hourly schedule is a compromise, not a guarantee that a private repository will remain below its included quota. Actual usage depends on how long each workflow takes plus CI usage.

If your repository is private, monitor GitHub billing/Actions usage before increasing frequency.

If your repository is public and you want a faster watchlist cadence, you can edit the schedule. GitHub currently permits scheduled workflows as frequently as every five minutes.

A five-minute offset schedule can be written as:

```yaml
schedule:
  - cron: "2-59/5 * * * *"
```

If you do that, also reduce the watchlist command's due age from:

```text
--min-age-minutes 25
```

to approximately:

```text
--min-age-minutes 4
```

Do not assume a five-minute cron means exactly five-minute delivery; scheduled workflows can be delayed.

---

## 9. Workflow overlap protection

GitHub workflow-level protection:

```yaml
concurrency:
  group: radar-scheduled-monitor
  cancel-in-progress: false
```

This prevents two scheduled Radar workflow runs from executing simultaneously as separate active runs.

Radar also retains its PostgreSQL advisory lock per company. Therefore manual runs, future workflows, and delayed schedules still have database-backed overlap protection.

The database lock is the final correctness mechanism; GitHub concurrency is an efficiency mechanism.

---

## 10. Partial failures

Scheduled commands include:

```text
--allow-partial-failures
```

This is deliberate.

If one ATS source is temporarily broken, Radar:

1. records that company as FAILED
2. increments its failure information
3. continues monitoring unrelated companies
4. records the containing `monitor_runs` row as PARTIAL or FAILED as appropriate

The scheduled workflow is intended not to become permanently red merely because one company has a bad ATS configuration.

Database/configuration failures that prevent the worker itself from running still fail the GitHub workflow.

---

## 11. Monitor-run observability

Each invocation of the worker now creates one `monitor_runs` row.

Inspect recent runs in Supabase:

```sql
SELECT
    id,
    started_at,
    completed_at,
    status,
    source_scope,
    priority,
    shard_index,
    shard_count,
    batch_size,
    min_age_minutes,
    max_concurrency,
    companies_selected,
    companies_succeeded,
    companies_failed,
    companies_skipped,
    notifications_sent,
    trigger,
    external_run_id,
    error_type,
    error_message
FROM monitor_runs
ORDER BY started_at DESC
LIMIT 30;
```

Inspect per-company logs for one worker run:

```sql
SELECT
    c.name,
    cl.status,
    cl.jobs_received,
    cl.jobs_new,
    cl.jobs_updated,
    cl.jobs_closed,
    cl.matches_created,
    cl.notifications_sent,
    cl.error_type,
    cl.error_message,
    cl.duration_ms
FROM crawler_logs cl
JOIN companies c ON c.id = cl.company_id
WHERE cl.monitor_run_id = 'MONITOR_RUN_UUID_HERE'
ORDER BY cl.started_at;
```

Inspect recent failures:

```sql
SELECT
    c.name,
    c.ats_provider,
    c.ats_identifier,
    c.consecutive_failures,
    c.last_error_at,
    cl.error_type,
    cl.error_message
FROM companies c
LEFT JOIN LATERAL (
    SELECT error_type, error_message
    FROM crawler_logs
    WHERE company_id = c.id
      AND status = 'FAILED'
    ORDER BY started_at DESC
    LIMIT 1
) cl ON true
WHERE c.consecutive_failures > 0
ORDER BY c.consecutive_failures DESC, c.last_error_at DESC;
```

---

## 12. First GitHub Actions test

After pushing Phase 5 to the default branch and adding both secrets:

```text
GitHub repository
→ Actions
→ Scheduled Monitoring
→ Run workflow
```

Watch the steps:

```text
Check out repository
Set up Python
Install Radar worker
Validate worker secrets
Monitor watched companies
Monitor non-watched HIGH sources
Monitor non-watched NORMAL sources
Monitor non-watched LOW sources
```

Then query:

```sql
SELECT
    started_at,
    status,
    source_scope,
    priority,
    companies_selected,
    companies_succeeded,
    companies_failed,
    notifications_sent,
    trigger,
    external_run_id
FROM monitor_runs
ORDER BY started_at DESC
LIMIT 10;
```

For a GitHub-triggered run, `trigger` should be:

```text
github-actions
```

and `external_run_id` should contain the GitHub Actions run ID/attempt.

---

## 13. CI

Phase 5 updates CI to run:

Backend:

```text
ruff
compileall
pytest
```

Frontend:

```text
npm install
npm run lint
npm run typecheck
npm run build
```

CI uses read-only repository permissions and cancels superseded CI runs for the same ref.

Scheduled monitoring uses read-only repository permissions as well. Database and Telegram credentials are supplied only through repository secrets.

---

## 14. Phase 5 acceptance checklist

- [ ] `alembic current` reports `0004_phase5`
- [ ] backend tests pass
- [ ] `scheduled_monitor.yml` is on the GitHub default branch
- [ ] `DATABASE_URL` Actions secret exists
- [ ] `TELEGRAM_BOT_TOKEN` Actions secret exists
- [ ] manual workflow dispatch succeeds
- [ ] `monitor_runs` receives GitHub-triggered rows
- [ ] `crawler_logs.monitor_run_id` links company runs to their worker run
- [ ] watched companies are selected by the watchlist tier
- [ ] NORMAL/LOW registry sources respect due-age filtering
- [ ] duplicate job rows are not created on repeated scheduled runs
- [ ] duplicate Telegram notifications are not created on retries/overlap
- [ ] Render can be asleep while GitHub monitoring still works

---

## 15. What Phase 5 does not do

Phase 5 does not discover companies that are absent from `companies`.

The next phase is Phase 6A:

```text
candidate ATS source
    ↓
provider detection
    ↓
validation
    ↓
VALID source registry entry
    ↓
automated monitoring
```

Then Phase 6B can grow that candidate pool automatically.
