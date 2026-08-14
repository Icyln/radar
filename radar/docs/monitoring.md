# Monitoring — Phase 1 through Phase 5

Radar uses one reusable Python monitoring pipeline for manual execution and GitHub Actions. The worker talks directly to PostgreSQL, ATS providers, and Telegram; it never calls Render/FastAPI.

## Manual execution

All active companies:

```bash
cd backend
python -m app.workers.monitor
```

One ATS identifier:

```bash
python -m app.workers.monitor --ats-identifier cloudflare
```

Priority filter:

```bash
python -m app.workers.monitor --priority high
python -m app.workers.monitor --priority normal
python -m app.workers.monitor --priority low
```

Source scope:

```bash
python -m app.workers.monitor --scope all
python -m app.workers.monitor --scope watchlist
python -m app.workers.monitor --scope registry
```

`watchlist` means a source watched by at least one Radar user. `registry` means an active source currently watched by nobody.

## Phase 5 scheduling controls

The same worker supports bounded, due-aware, deterministic selection:

```bash
python -m app.workers.monitor \
  --scope registry \
  --priority normal \
  --batch-size 50 \
  --min-age-minutes 55 \
  --shard-index 0 \
  --shard-count 4 \
  --max-concurrency 3
```

- `--batch-size` caps sources selected in one invocation.
- `--min-age-minutes` excludes a source until its persisted `last_checked_at` is old enough. Never-checked sources are due first.
- `--shard-index` / `--shard-count` partition source UUIDs deterministically so later scale-out does not depend on unstable SQL offsets.
- `--max-concurrency` bounds simultaneous company processing.
- `--allow-partial-failures` lets a scheduled batch finish successfully when individual sources fail; those failures remain persisted in `crawler_logs` / `monitor_runs`. Fatal worker/database failures still fail the process.

Supported providers:

```text
GREENHOUSE
LEVER
ASHBY
```

## Scheduled production workflow

`.github/workflows/scheduled_monitor.yml` runs at minute `07` and `37` each hour. One runner installation handles multiple source tiers to avoid repeating checkout/setup/install overhead.

Default tiers:

```text
watchlist       batch 50   due after 25 min
registry HIGH   batch 25   due after 25 min
registry NORMAL batch 50   due after 55 min
registry LOW    batch 100  due after 235 min
```

The workflow uses repository secrets for `DATABASE_URL` and `TELEGRAM_BOT_TOKEN`, validates that the database is remote before monitoring, and uses a workflow concurrency group so scheduled executions do not intentionally overlap at the workflow level.

Per-company PostgreSQL advisory locks remain the final overlap guard if a manual run or another workflow reaches the same source concurrently.

## Persistent monitor runs

Each worker invocation creates a `monitor_runs` row. `crawler_logs.monitor_run_id` links company-level outcomes to the enclosing batch. Useful fields include source scope, priority, shard, batch/due settings, counts, trigger, external GitHub run identifier, status, and errors.

## Per-company sequence

1. acquire PostgreSQL advisory lock
2. create crawler log linked to the monitor run
3. fetch ATS outside a long DB transaction
4. validate and normalize source payload
5. insert/update/deduplicate jobs
6. advance lifecycle only after a successful complete snapshot
7. evaluate new/updated jobs against enabled profiles
8. enforce profile coverage (`WIDE` or `WATCHLIST`)
9. create unique JobMatch rows
10. enqueue eligible Telegram notifications
11. commit crawler/source state
12. release advisory lock
13. deliver pending notifications after company processing

## Coverage behavior

A Wide profile is evaluated against any active job in the source registry. A Watchlist profile is evaluated only when the job's company appears in that user's `user_company_watchlists` rows.

When a user starts watching a company, Radar backfills active jobs from that company against enabled Watchlist profiles. Historical backfill matches are persisted for the dashboard but are not pushed as a notification burst.

## Phase 6 boundary

Phase 5 schedules sources already present in `companies`. It does not discover companies absent from the registry. Source candidate discovery, validation, and registry growth belong to Phase 6.
