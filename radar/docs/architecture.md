# Architecture — Phase 0 through Phase 5

## Decision

Keep Radar as one monorepo with a Next.js management UI and a reusable Python domain package. FastAPI serves authenticated management APIs. Monitoring remains a standalone worker that talks directly to PostgreSQL, ATS sources, and Telegram.

Phase 4.3 adds a clean separation between three concepts:

```text
Source Registry     = companies Radar knows how to monitor
User Watchlist      = sources a particular user cares about most
Profile Coverage    = WATCHLIST or WIDE matching scope
```

## Why

This preserves the critical invariant that a sleeping Render API cannot stop monitoring. It also avoids duplicating ATS fetches per user: each company is fetched once, jobs are normalized once, then user/profile rules decide which jobs become matches.

## Main flow

```text
                           Job Profile
                    coverage=WATCHLIST/WIDE
                              |
                              v
                        Matching Engine
                              ^
                              |
                       Normalized Jobs
                              ^
                              |
               +--------------+--------------+
               |              |              |
          Greenhouse         Lever          Ashby
               ^              ^              ^
               |              |              |
               +------ Company Registry -----+
                              ^
                              |
                   user_company_watchlists
```

### Watchlist profile

A `WATCHLIST` profile can only match a job when `(user_id, job.company_id)` exists in `user_company_watchlists`.

### Wide profile

A `WIDE` profile can match jobs from any active source already present in the registry.

Existing pre-4.3 profiles migrate to `WIDE` for backward-compatible behavior.

## Jobs browsing

`Detected` is intentionally separate from `Matched`:

```text
Detected -> all collected source-registry jobs, paginated server-side
Matched  -> distinct jobs with JobMatch rows for current user
Saved    -> current user's SAVED states
Ignored  -> current user's IGNORED states
```

The Detected API does not return job descriptions and caps a request at 50 rows. The frontend uses 24 per page.

## Source scheduling groundwork

The worker can select:

```text
--scope all        all active sources
--scope watchlist  sources watched by at least one user
--scope registry   active sources currently watched by nobody
```

Phase 5 uses these scopes through one cost-aware GitHub Actions schedule. Database due-age state, bounded batches, bounded async concurrency, and optional deterministic sharding control how much work each invocation performs.

```text
GitHub Actions (:07/:37)
          |
          +-- watchlist sources (freshest tier)
          +-- registry HIGH
          +-- registry NORMAL
          +-- registry LOW
          |
          v
       monitor_runs
          |
          v
     crawler_logs -> company pipeline
```

Each scheduled invocation is persisted independently of the GitHub runner. Per-company PostgreSQL advisory locks remain the final overlap guard.

## Persistent invariants

1. Monitoring never depends on FastAPI staying awake.
2. ATS fetches are normalized into one downstream job model.
3. Database constraints protect job/match/notification identity.
4. Failed ATS requests cannot advance missing counters.
5. User watchlists are relational and ownership-scoped.
6. Profile coverage is deterministic and testable.
7. Adding a watched company may backfill dashboard matches but does not send historical alert floods.
8. Removing a watched company prunes only Watchlist-profile matches for that user's scope.
9. Wide profiles remain independent of personal watchlists.
10. Detected browsing is paginated server-side so registry growth does not require loading full job history in the browser.
11. Scheduled workers use database state as their durable clock; GitHub Actions is only the trigger.
12. A monitor invocation is observable through `monitor_runs`, with company outcomes linked through `crawler_logs`.
13. Batching/sharding change execution distribution, not job identity or notification semantics.
14. Phase 5 does not discover unknown companies; registry expansion remains Phase 6.
