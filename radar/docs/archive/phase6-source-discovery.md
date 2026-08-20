# Radar Phase 6 — ATS source discovery and validation

Phase 6 expands Radar beyond companies that were manually inserted into `companies`.

It does **not** attempt to crawl the entire internet or enumerate every Greenhouse, Lever, or Ashby tenant. Those ATS systems expose public job feeds per organization, not a global public company directory. Radar therefore uses a bounded candidate pipeline:

```text
company/careers URL or direct ATS URL
        ↓
discovery_targets
        ↓
bounded public-page scan
        ↓
recognized Greenhouse / Lever / Ashby URL
        ↓
source_candidates
        ↓
provider API validation
        ↓
VALID
        ↓
promote into companies as active LOW-priority source
        ↓
normal Phase 5 monitor collects jobs
        ↓
Wide/Watchlist profile matching + Telegram
```

This keeps discovery separate from job monitoring and prevents an invalid guessed source from entering high-frequency monitoring.

## 1. Upgrade the database

Phase 6 adds migration:

```text
0005_phase6
```

From `backend` with the production/Supabase `DATABASE_URL` active:

```powershell
alembic upgrade head
alembic current
```

Expected:

```text
0005_phase6
```

Existing users, companies, jobs, profiles, matches, notifications, watchlists, crawler logs, and monitor runs remain intact.

## 2. New tables

### `discovery_targets`

A target is a public company homepage, careers URL, or direct ATS URL submitted for inspection.

Important fields include:

```text
submitted_by_user_id
url
company_name_hint
auto_watch
status
scan_attempt_count
pages_scanned
sources_found
error_type
error_message
```

Statuses:

```text
PENDING
SCANNING
COMPLETE
FAILED
```

### `source_candidates`

A candidate is a concrete supported ATS source detected from a target.

```text
ats_provider
ats_identifier
career_url
source_url
status
validation_attempt_count
jobs_seen
promoted_company_id
```

Statuses:

```text
DISCOVERED
VALIDATING
VALID
INVALID
```

A candidate is promoted only after the existing provider collector successfully parses its public job feed. A legitimate empty job board is still valid; `jobs_seen=0` simply means it currently has no listed jobs.

`discovery_target_candidates` links multiple user requests to the same deduplicated ATS candidate.

## 3. User workflow

Open:

```text
Dashboard → Discovery
```

Submit one of:

```text
https://company.example
https://company.example/careers
https://boards.greenhouse.io/company-token
https://jobs.lever.co/company-token
https://jobs.ashbyhq.com/company-token
```

The normal user does not directly create an active company. The request is queued for validation.

If **Automatically add the source to my watchlist** is checked, a successfully promoted source is added to that user's watchlist.

This means:

```text
WATCHLIST profile
→ can match the new company automatically after promotion when auto-watch is enabled

WIDE profile
→ can match the new company because every promoted source joins the active registry
```

## 4. What the bounded crawler does

For an ordinary company URL Radar:

1. validates that the URL is public HTTP/HTTPS;
2. rejects localhost, private-network, link-local, reserved, and non-standard-port targets;
3. fetches a small bounded number of pages;
4. follows only same-host links whose paths look career/job related;
5. extracts direct ATS links from anchors and page HTML;
6. recognizes only Greenhouse, Lever, and Ashby URL patterns.

Default maximum:

```text
6 pages per target
```

Targets/candidates left in an in-progress state by a terminated worker are eligible for recovery after 30 minutes (`DISCOVERY_STALE_MINUTES`).

This is deliberately not a general web crawler.

## 5. Validation

Each discovered candidate is validated through Radar's real collector contract:

```text
GreenhouseCandidate → GreenhouseCollector.fetch_jobs()
LeverCandidate      → LeverCollector.fetch_jobs()
AshbyCandidate      → AshbyCollector.fetch_jobs()
```

Therefore source validation exercises the same schema parsing and HTTP behavior used by production monitoring.

A source that returns an invalid/missing board or malformed public payload becomes `INVALID` and is not promoted.

A successful candidate becomes `VALID` and the scheduled workflow uses `--auto-promote` to create or reuse a `companies` row.

New automatically discovered sources use:

```text
monitoring_priority = LOW
active = true
```

This prevents discovery from silently turning unknown sources into high-frequency monitoring targets.

## 6. Manual discovery worker test

Queue a request from the UI, then run:

```powershell
python -m app.workers.discovery --target-batch-size 25 --candidate-batch-size 50 --max-concurrency 3 --auto-promote
```

Example result:

```json
{
  "targets_selected": 1,
  "targets_complete": 1,
  "targets_failed": 0,
  "candidates_selected": 1,
  "candidates_valid": 1,
  "candidates_invalid": 0,
  "candidates_promoted": 1
}
```

Then inspect:

```sql
select status, url, sources_found, error_message
from discovery_targets
order by created_at desc;

select ats_provider, ats_identifier, status, jobs_seen, promoted_company_id
from source_candidates
order by created_at desc;

select name, ats_provider, ats_identifier, monitoring_priority, active
from companies
order by created_at desc;
```

## 7. GitHub Actions discovery

New workflow:

```text
.github/workflows/discovery.yml
```

It runs daily at approximately:

```text
03:23 UTC
```

and also supports manual `workflow_dispatch`.

It requires only:

```text
DATABASE_URL
```

as a GitHub repository secret. Discovery itself does not need the Telegram bot token.

On GitHub:

```text
Actions
→ Source Discovery
→ Run workflow
```

The workflow processes bounded target and candidate batches and auto-promotes validated sources.

If your GitHub repository contains the project under an extra `radar/` directory, remember that GitHub workflow files must still live at repository-root `.github/workflows/`; adjust workflow `working-directory` and cache paths to `radar/backend` as you did for Phase 5.

## 8. Bulk discovery targets

For larger curated testing, create a CSV:

```csv
url,company_name
https://example-one.com/careers,Example One
https://example-two.com/jobs,Example Two
https://jobs.lever.co/example-three,Example Three
```

Import it:

```powershell
python -m app.scripts.import_discovery_targets --file targets.csv
```

These imported targets are not tied to a user and therefore are not auto-watched. They still expand the registry after validation/promotion, so WIDE profiles can use them.

This is a useful low-cost way to grow from dozens to hundreds of curated sources without adding a paid search API.

## 9. When are jobs collected?

Discovery validates and registers the source; it does not write the validation snapshot into `jobs`.

After promotion:

```text
new company.last_checked_at = NULL
```

so the next Phase 5 scheduled monitoring run considers it due immediately. The normal monitor then owns job lifecycle, deduplication, matching, notification outbox, and Telegram delivery.

This separation preserves the architectural invariant that every ATS job enters the same downstream monitoring pipeline.

## 10. Retry behavior

Failed target scans can be retried from the Discovery page.

Administrators can inspect the validation queue. Invalid candidates can be reset to `DISCOVERED`; VALID but unpromoted candidates can be promoted manually.

Retries are bounded by worker batch sizes and each attempt is persisted.

## 11. Security boundary

Discovery URLs are untrusted user input. Radar therefore does not intentionally allow scanning:

```text
localhost
127.0.0.0/8
private RFC1918 networks
link-local networks
reserved/non-global IPs
URLs containing credentials
arbitrary non-80/443 ports
```

Redirect targets are revalidated before following them.

Do not weaken these checks merely to make an unusual internal career site work; manually add a trusted source as an administrator instead.

## 12. What Phase 6 does not promise

Phase 6 means:

> Detect new matching jobs across the validated ATS sources Radar knows or is given enough information to discover.

It does not mean:

> Enumerate every employer on the internet with no seed information.

Greenhouse, Lever, and Ashby public job APIs remain organization-scoped. To grow the universe, feed Radar company/career URLs through user requests, curated bulk imports, or future external discovery feeds. The validation/promotion pipeline added here is the safe boundary for any future discovery feed.

## Phase 6B continuation

Phase 6B removes the requirement that an end user personally provide every seed URL. See [`phase6b-system-discovery.md`](phase6b-system-discovery.md) for bundled/remote system feeds, provenance, automatic retry, and promoted-source revalidation.
