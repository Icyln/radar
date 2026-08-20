# Monitoring and discovery — Phase 1 through Phase 6

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

## Phase 6 discovery worker

Phase 6 adds a separate worker:

```bash
python -m app.workers.discovery --auto-promote
```

The discovery worker processes queued company/career targets, extracts supported ATS sources with a bounded crawler, validates those candidates using the existing collectors, and promotes only VALID sources into `companies` as LOW priority. It does not persist validation jobs into the `jobs` table; the next normal monitoring run performs canonical job ingestion.

Production discovery is triggered by `.github/workflows/discovery.yml` and by manual workflow dispatch. Phase 7 runs discovery every six hours so fresh profile-driven hiring signals can enter the registry promptly. It requires `DATABASE_URL` but not the Telegram token.

## Phase 6C freshness and alerts

Phase 6C separates current-match freshness from job retention. Old jobs remain in `jobs`; freshness only controls whether an enabled profile currently considers the job a match.

Freshness evidence is provider publication time when available. For providers/jobs without a reliable publication timestamp, `first_seen_at` is accepted only when the job was first detected after the company's initial baseline. Undated baseline inventory remains UNKNOWN.

The monitor now separates new-job matching from updated-job matching. Both may create dashboard `JobMatch` records, but only matches created from `jobs_new` on a non-initial source run are eligible for user Telegram enqueueing. This prevents a title/content update on a long-existing job from masquerading as a newly posted alert.

## Phase 7 active-hiring boost

Fresh Phase-7 signal discoveries keep `LOW` as their stored company priority and receive `discovery_boost_until`. While that timestamp is in the future, the scheduler includes those LOW companies in the effective `NORMAL` tier and excludes them from the LOW tier. When the boost expires, they automatically return to LOW rotation. This improves freshness for currently hiring companies without permanently moving a growing registry onto the higher-cost cadence.
