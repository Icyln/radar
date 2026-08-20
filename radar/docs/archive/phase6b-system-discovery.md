# Radar Phase 6B — System-managed discovery feeds

Phase 6A introduced a safe validation boundary for user/admin-supplied company URLs. Phase 6B adds **zero-user-input registry growth** on top of that boundary.

Radar still does not pretend Greenhouse, Lever, or Ashby provide a public global tenant directory. Instead, the scheduled discovery worker now ingests **system-managed source catalogs** and routes every entry through the same persisted target → candidate → validation → promotion pipeline.

```text
bundled starter catalog
        +
optional remote CSV / JSON feeds
        ↓
system discovery targets
        ↓
Phase 6A bounded discovery / direct ATS detection
        ↓
source candidates
        ↓
real collector validation
        ↓
VALID only
        ↓
active LOW-priority company registry
        ↓
Phase 5 scheduled monitoring
        ↓
WIDE profile matching
```

## Database migration

Phase 6B adds migration:

```text
0006_phase6b
```

It adds provenance to `discovery_targets`:

```text
origin = USER | SYSTEM_FEED
source_label
```

and source-health fields to `source_candidates`:

```text
last_revalidated_at
revalidation_failure_count
```

Existing Phase 6A targets migrate to `origin=USER`.

## Bundled starter catalog

Radar ships a small catalog at:

```text
backend/app/discovery/catalogs/starter.csv
```

Format:

```csv
url,company_name
https://jobs.ashbyhq.com/example,Example
https://jobs.lever.co/example-two,Example Two
```

The daily discovery worker ingests this catalog automatically. Existing companies/candidates are skipped, so repeated runs are idempotent.

The bundled file is intentionally small. Its purpose is to prove system-managed registry growth and provide a no-input baseline, not to claim exhaustive internet coverage.

## Optional remote system feeds

Set a comma-separated list of public CSV/JSON URLs:

```dotenv
DISCOVERY_SYSTEM_FEED_URLS=https://example.com/radar-feed.csv,https://example.org/sources.json
```

CSV supports:

```csv
url,company_name
https://company.example/careers,Example Company
https://jobs.lever.co/example-two,Example Two
```

JSON supports either a list of URLs:

```json
[
  "https://jobs.ashbyhq.com/example"
]
```

or objects:

```json
[
  {
    "url": "https://jobs.lever.co/example",
    "company_name": "Example"
  }
]
```

For GitHub Actions, `DISCOVERY_SYSTEM_FEED_URLS` is a **repository variable**, not a secret:

```text
Settings
→ Secrets and variables
→ Actions
→ Variables
→ New repository variable
```

The workflow reads:

```text
vars.DISCOVERY_SYSTEM_FEED_URLS
```

Leaving it unset is valid; the bundled catalog still runs.

## Feed safety

Remote feed downloads are bounded and public-network checked:

- redirects are validated;
- localhost/private/link-local/reserved hosts are rejected;
- maximum feed bytes are configurable;
- only CSV/JSON/plain-text catalog content is accepted by the parser;
- feed entries are still sent through normal discovery/ATS validation before promotion.

Default maximum:

```text
DISCOVERY_SYSTEM_FEED_MAX_BYTES=1000000
DISCOVERY_SYSTEM_FEED_MAX_ENTRIES=1000
```

A remote feed therefore cannot directly create an active company record.

## Automatic retry and revalidation

System-generated invalid candidates are eligible for retry after:

```text
DISCOVERY_INVALID_RETRY_DAYS=7
```

Promoted sources are revalidated after:

```text
DISCOVERY_REVALIDATE_DAYS=14
```

Revalidation is deliberately conservative. One revalidation failure:

- records the error;
- increments `revalidation_failure_count`;
- does **not** immediately disable the promoted company.

The normal Phase 5 monitor already tracks live source failures separately. This avoids taking a valid source offline because of one temporary provider/network problem.

A successful revalidation resets the revalidation failure counter.

## Worker usage

Normal Phase 6B run:

```powershell
python -m app.workers.discovery --auto-promote --ingest-system-feeds --revalidate-promoted
```

Useful testing command:

```powershell
python -m app.workers.discovery `
  --target-batch-size 25 `
  --candidate-batch-size 50 `
  --revalidate-batch-size 50 `
  --max-concurrency 3 `
  --auto-promote `
  --ingest-system-feeds `
  --revalidate-promoted
```

The JSON summary includes Phase 6B counters such as:

```text
system_feeds_processed
system_feeds_failed
system_entries_seen
system_targets_queued
system_entries_existing
revalidation_selected
revalidated
revalidation_failed
```

## GitHub Actions

The existing workflow remains:

```text
.github/workflows/discovery.yml
```

It now performs three jobs in one scheduled run:

```text
1. ingest system-managed feeds
2. discover / validate / promote pending sources
3. revalidate due promoted sources
```

The daily cron remains approximately `03:23 UTC`, plus `workflow_dispatch` for manual testing.

Required repository secret:

```text
DATABASE_URL
```

Optional repository variable:

```text
DISCOVERY_SYSTEM_FEED_URLS
```

Telegram is still not required by the discovery workflow. Telegram belongs to the Phase 5 monitoring/notification path after jobs are collected and matched.

## Admin dashboard

The Discovery page now distinguishes user targets from system-feed targets. Administrators see an **Automatic registry growth** panel with:

```text
System targets
System-promoted sources
Revalidation warnings
```

System targets are labeled `System` and keep their feed/source label for auditability.

Normal users still see only their own requests.

## What zero-input means

After Phase 6B, a user can create a WIDE profile without submitting a company URL. Radar can expand the shared registry from its configured system catalogs/feeds and that profile automatically gains access to every newly validated active company.

It does **not** mean Radar can discover every company on the internet from nothing. Without a paid/general search index or provider-wide tenant directory, the discovery universe is bounded by the system catalogs/feeds Radar is configured to consume. The important improvement is that this seed management is now a system responsibility rather than an end-user requirement.

## User-facing ownership of registry growth

Bulk CSV/JSON ingestion is an internal system/admin mechanism, not a normal user workflow. Wide Search users should not be asked to upload hundreds of companies or understand ATS identifiers. The system discovery workflow owns shared-registry growth; the Discovery request form is only an optional way to suggest a specific missing company.
