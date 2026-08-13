# Monitoring — Phase 1 through Phase 3

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

Supported providers:

```text
GREENHOUSE
LEVER
ASHBY
```

## Per-company sequence

1. acquire PostgreSQL advisory lock
2. create `crawler_logs` row
3. fetch ATS outside a long database transaction
4. validate provider response
5. normalize into `NormalizedJob`
6. insert/update/deduplicate observed jobs
7. advance lifecycle for jobs absent from the successful snapshot
8. evaluate new/updated jobs against enabled profiles
9. create unique `job_matches`
10. create per-user Telegram notification rows for new matches when appropriate
11. commit source state and crawler statistics
12. release company lock
13. deliver pending notifications outside source-processing transaction

One company failure does not stop unrelated companies.

## Source-failure safety

A collector must either return a complete successful snapshot or raise `CollectorError`. A timeout, HTTP error, malformed payload, or parsing error never becomes an empty successful board and therefore cannot increment missing counters or close jobs.

## HTTP policy

The shared HTTP client uses:

- connect timeout
- read timeout
- bounded retries
- bounded exponential backoff
- retry for network failure, 429, and 5xx
- no repeated retry for permanent 4xx errors

## Initial synchronization

A company's first successful source snapshot establishes the baseline. Existing jobs are persisted and can be matched for dashboard history, but normal per-user alerts are not sent for the initial board contents.

The legacy Phase-1 single-recipient test path can still be intentionally enabled with `PHASE1_NOTIFY_ON_INITIAL_SYNC=true`.

## Notification outbox

Normal Phase 2/3 notifications use:

```text
PENDING -> SENDING -> SENT
                  -> FAILED
```

Failures are bounded by `TELEGRAM_MAX_ATTEMPTS`.

A `SENDING` row older than `TELEGRAM_SENDING_STALE_MINUTES` becomes claimable again. This prevents a crash from leaving notifications stuck forever. Because Telegram and PostgreSQL cannot participate in one atomic transaction, this is practical at-least-once processing with database guards for effectively-once behavior under normal operation.

## Phase 5 boundary

GitHub Actions schedules are not part of Phase 3. Phase 5 should call the same worker with priority filters and inject secrets through GitHub Actions secrets. It must not wake/call Render to perform monitoring.
