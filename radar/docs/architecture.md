# Architecture — Phase 0 through Phase 3

## Decision

Keep Radar as a monorepo with a Next.js frontend foundation and one reusable Python backend/domain package. FastAPI serves user-management APIs. Monitoring runs as a standalone Python worker that talks directly to PostgreSQL, ATS sources, and Telegram.

## Reason

This preserves the central architectural invariant: a sleeping Render instance cannot stop monitoring. It also lets API routes and workers reuse the same models, matching code, notification outbox, and persistence rules without introducing microservices or a queue service.

## Tradeoffs

- Synchronous SQLAlchemy is retained for the small database workload; external ATS/Telegram calls are async.
- PostgreSQL is the source of truth for all monitoring, matching, Telegram linkage, and notification state.
- PostgreSQL advisory locks protect overlapping company monitor executions without Redis.
- First source synchronization persists jobs/matches as a baseline but does not push historical board contents as per-user alerts.
- Notification delivery is practical at-least-once. Stale `SENDING` records can be retried; a rare duplicate remains possible if Telegram accepted a message immediately before a worker crash.

## Main modules

```text
backend/app/
  api/              FastAPI auth/domain/Telegram routes
  collectors/       Greenhouse, Lever, Ashby
  core/             settings, security, logging, HTTP
  db/               engine/session/base
  matching/         deterministic profile matching
  models/           persistent domain models
  notifications/    Telegram Bot API client
  schemas/          API and normalized boundary models
  scripts/          seed/admin/Telegram operational helpers
  services/         lifecycle, matching integration, outbox, linking, state
  workers/          standalone monitoring entrypoint
```

## Monitoring path

```text
GitHub Actions later / manual command now
             |
             v
        MonitorService
             |
             v
 Greenhouse / Lever / Ashby
             |
             v
        NormalizedJob[]
             |
             v
    dedup + lifecycle
             |
             v
          Job rows
             |
             v
 deterministic matching
             |
             v
        JobMatch rows
             |
             v
 verified TelegramConnection
             |
             v
      Notification outbox
             |
             v
          Telegram
```

FastAPI is not called anywhere in this path.

## Domain invariants

1. Provider external IDs are preferred for source identity.
2. Providers without an exposed external ID use a deterministic provider/company/application-URL fingerprint.
3. Job uniqueness is protected by database constraints as well as application logic.
4. Missing counters advance only after a successful complete source snapshot.
5. Job matches are unique by `(job_profile_id, job_id)`.
6. User saved/ignored state is one row per `(user_id, job_id)`, preventing contradictory states.
7. Per-user notifications are unique by `(user_id, job_id, channel)`; recipient uniqueness remains as a second guard.
8. Telegram link tokens are random, hashed at rest, expiring, and single-use.
9. Every user-owned API resource is ownership checked on the backend.
10. Workers require no persistent local filesystem state.
