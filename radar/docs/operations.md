# Operations

## Scheduled Monitoring

Workflow: `.github/workflows/scheduled_monitor.yml`

Default schedule: twice per hour at minute 7 and 37.

The workflow checks, in order:

1. companies followed by any user
2. non-followed high-priority sources
3. non-followed normal-priority sources
4. non-followed low-priority sources

Each step uses bounded concurrency of 3 and age thresholds so a source is not fetched unnecessarily often.

## Source Discovery

Workflow: `.github/workflows/discovery.yml`

Default schedule: every six hours. It can:

- ingest public hiring signals
- queue/scan bounded discovery targets
- validate candidate ATS sources
- promote valid sources
- periodically revalidate promoted sources
- ingest broad-search jobs and deliver new matches

Search terms are deduplicated across users. When more distinct terms exist than the per-run query budget, the order is interleaved by user and the capped window rotates rather than permanently selecting the oldest profiles.

## Admin observability

Use **Admin → System status** for monitoring and broad-search automation health. Use **Admin → Source discovery** for target/candidate diagnostics and source promotion.

Normal users intentionally do not see these operational concepts.

## Database connections

The web API defaults to a pool size of 5 plus 5 overflow connections. Worker concurrency defaults to 3. These values are deliberately modest for Supabase and the expected user count.

Do not increase pool size or worker concurrency simply to make an individual run faster. First confirm database and provider latency/limits.

## Failure handling

- A single company/provider failure should be recorded without discarding successful work from other items.
- Telegram delivery retries are bounded by `TELEGRAM_MAX_ATTEMPTS`.
- Stuck `SENDING` notifications become claimable again after the configured stale interval.
- GitHub workflow concurrency groups prevent overlapping instances of the same scheduled workflow.

## Manual checks

```bash
# Backend tests
cd backend && pytest

# Worker config without making provider calls
python -m app.scripts.check_worker_config --require-telegram --require-remote-database

# Monitor a specific source when diagnosing an issue
python -m app.workers.monitor --ats-identifier IDENTIFIER --max-concurrency 1

# Run discovery manually
python -m app.workers.discovery --max-concurrency 1
```
