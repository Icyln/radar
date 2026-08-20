# Radar Architecture

## Goals

Radar is optimized for a small production deployment of roughly 50–100 users. The architecture prioritizes predictable behavior, low operational overhead, database integrity, and failure isolation.

## Runtime components

### Next.js frontend and BFF

The frontend provides the public landing/help experience and the authenticated workspace. Browser requests to the backend go through the Next.js BFF at `/api/radar/*` so the backend access token remains in an HttpOnly cookie rather than browser JavaScript.

The BFF adds:

- same-origin checks for state-changing requests
- request-body limits
- upstream timeouts
- request ID propagation
- no-store responses
- secure HttpOnly session-cookie handling

### FastAPI backend

The backend owns authentication, users, Job Alerts, job matching, company following, source discovery, Telegram linking, and operational summaries.

It is intentionally a modular monolith. Business boundaries are represented by modules/services rather than separate deployable services.

### Supabase PostgreSQL

PostgreSQL is the system of record and coordination layer. Important safety properties are enforced with database constraints and transactional state transitions, including job identity/deduplication, notification identity, and company-level monitoring coordination.

The API and workers use conservative SQLAlchemy pool settings suitable for Supabase connection limits. External network I/O should not hold request-scoped database sessions when avoidable.

### GitHub Actions workers

Two scheduled workflows perform background work independently from the Render web process:

1. **Scheduled Monitoring** checks verified company career sources.
2. **Source Discovery** searches supported public job sources, stages/validates candidate company sources, revalidates promoted sources, and delivers broad-search matches.

This separation prevents Render web-process sleep/restarts from stopping scheduled monitoring.

### Telegram

Users link their own Telegram chat. New matching jobs enqueue per-user notification records. Delivery is idempotent and retry-bounded, and the bot webhook is protected with Telegram's webhook secret header in production.

## Job Alert model

The UI presents one Job Alert concept. Internally, `coverage_mode` remains:

- `WIDE`: search broadly and include direct monitored sources
- `WATCHLIST`: only match companies followed by that user

Keeping this internal distinction avoids a risky data migration while removing complexity from the user experience.

## Capacity model

For a 50–100 user target, current limits are intentionally conservative:

- 5 active alerts per user
- 10 total alerts per user
- 5 titles per alert
- 25 active titles per user
- company-monitor concurrency default 3
- source-discovery concurrency default 3
- broad hiring search global query budget default 25 per discovery run

Broad-search titles are deduplicated across users, interleaved by account, and rotated when the global query budget is exceeded. This avoids permanently favoring the oldest profiles without introducing another queue service.

## Concurrency and failure isolation

- Worker concurrency is bounded with `asyncio` semaphores.
- Company monitoring uses PostgreSQL advisory locking to avoid duplicate simultaneous work on the same company.
- Notification claims use transactional status changes and bounded retries.
- Database uniqueness constraints provide the final idempotency barrier.
- Worker workflows use GitHub Actions concurrency groups with `cancel-in-progress: false` so scheduled runs do not overlap unexpectedly.
- Individual provider/company failures can be recorded without failing all useful work in the run.

## When to change the architecture

Do not add Redis/Celery/Kafka merely because user count grows modestly. Reconsider a durable work queue only if one or more of these become persistent:

- scheduled runs regularly exceed their workflow time budget
- database connection pressure remains high after query/pool tuning
- thousands of distinct search terms need sub-hour freshness
- notification backlog cannot clear within the next scheduled cycle
- manual refresh endpoints need asynchronous job tracking

At that point, PostgreSQL `FOR UPDATE SKIP LOCKED` can be evaluated as a first durable queue before adding another infrastructure service.
