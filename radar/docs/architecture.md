# Architecture — Phase 0 through Phase 6C

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
14. Discovery is upstream of monitoring: validation never writes jobs directly into the main job lifecycle pipeline.
15. Untrusted discovery URLs are bounded and public-network validated before fetching.
16. Only collector-validated Greenhouse/Lever/Ashby candidates may be promoted automatically.
17. Catalog/feed-discovered sources enter the registry as LOW priority; fresh Phase-7 hiring-signal sources keep that base priority but receive a temporary effective-NORMAL discovery boost, without overwriting an admin-set priority.
18. Public hiring indexes are discovery seeds only; persisted job lifecycle state still comes from validated direct ATS collectors.
19. First-sync alert suppression may be relaxed only for one role unambiguously identified by fresh external evidence.


## Phase 6 discovery flow

```text
User / admin / curated CSV
          |
          v
   discovery_targets
          | bounded public-page scan
          v
    source_candidates
          | production collector validation
          v
        VALID
          | promote
          v
   Company Registry (LOW)
          | next Phase 5 monitor
          v
 Normalized Jobs -> matching -> notification
```

Discovery does not create a parallel job ingestion path. The monitor remains the only owner of persisted job lifecycle processing.


## Phase 6C freshness model

Freshness is a profile rule, not a destructive retention rule. Radar keeps all jobs and historical JobMatch rows, while current Matched/dashboard views re-evaluate whether at least one enabled profile still considers a job fresh.

```text
provider posted_at available
        -> use posted_at

provider posted_at unavailable
        + job discovered after company baseline
        -> use first_seen_at

provider posted_at unavailable
        + job imported during initial baseline
        -> freshness UNKNOWN
```

This distinction prevents the first synchronization of a newly discovered company from making old undated inventory look freshly posted. A strict 30-day profile excludes UNKNOWN baseline jobs by default; users may opt into them explicitly or choose Any age.

Notification eligibility is stricter than dashboard matching: initial baseline matches are never pushed, and updates to an already-known job may create/update dashboard match state but do not enqueue a fresh-job Telegram alert. Only match records created from genuinely new post-baseline job identities are considered for user notification.

Registry growth remains system-managed. Ordinary users do not upload bulk company CSVs; system/admin catalogs and configured feeds grow the shared source registry, while a user company request is only an optional fallback for a missing source.


## Phase 7 active-hiring discovery

```text
Active enabled WIDE profiles
          | unique target titles
          v
Public hiring-signal adapters (bounded)
          | local title + freshness filter
          v
   discovery_targets [SYSTEM_FEED]
          | bounded scan
          v
    source_candidates
          | collector validation
          v
Company Registry (LOW + temporary NORMAL boost when signal-fresh)
          |
          v
Phase 5 direct ATS monitor
```

A signal may also carry publication evidence for the specific role that caused discovery. Radar attaches that timestamp only when the first ATS snapshot contains one unambiguous matching job. Provider `posted_at` has precedence; unrelated baseline inventory remains UNKNOWN.
