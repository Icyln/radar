# Radar Phase 6C — Freshness-aware matching

Phase 6C makes Radar's early-warning behavior explicit: a job can be stored for history without being considered a current match.

## User-facing policy

Normal users do **not** upload company CSVs. Wide Search uses the automatically maintained shared source registry created by Phase 6B. Bulk CSV/JSON feeds remain an admin/system ingestion mechanism. A user may optionally request one missing company from Discovery, but this is not required for Wide Search.

Every profile now has:

- `max_job_age_days`: default `30`; nullable for `Any age`
- `include_unknown_posted_at`: default `false`

UI presets: 1, 3, 7, 14, 30, 60, 90 days, or Any age.

## Safe freshness evidence

Radar does not equate `first_seen_at` with `posted_at` blindly.

1. If the provider supplies `posted_at`, use it.
2. If no provider timestamp exists and the job first appears **after** the company's initial baseline, use `first_seen_at` as freshness evidence.
3. If no provider timestamp exists and the job was imported during the company's initial baseline, freshness is `UNKNOWN`.

This prevents a newly discovered company's old inventory from becoming “fresh” simply because Radar first saw it today.

## Matching

The deterministic order includes freshness in addition to coverage/title/location/work mode/exclusions. Under a 30-day strict profile:

- posted 3 days ago -> eligible
- posted 45 days ago -> rejected
- no posting date, initial baseline -> rejected by default
- no posting date, first detected after baseline 2 days ago -> eligible
- Any age -> freshness does not reject

Historical `job_matches` remain persisted. Current Matched/dashboard views re-evaluate active profiles, so an old job naturally drops out of the current view without deleting history.

## Telegram semantics

Phase 6C keeps baseline suppression and tightens updated-job behavior:

- initial source sync: matches may appear in the dashboard, but no user alert
- genuinely new post-baseline job: may create a match and Telegram alert
- existing job update: may create a dashboard match if its title/details become relevant, but it is not treated as a newly posted job alert
- notification uniqueness still prevents repeated alerts for the same user/job/channel

## Detected browsing

Detected adds a `Freshness` filter:

- Last 24 hours
- Last 3 / 7 / 14 / 30 / 60 / 90 days
- Posting date unknown
- Any time

Detected defaults to Last 30 days in the UI. Old jobs are not deleted; choose Any time to inspect the full retained history.

## Migration

```text
0006_phase6b -> 0007_phase6c
```

Adds:

```text
job_profiles.max_job_age_days
job_profiles.include_unknown_posted_at
jobs.baseline_imported
ix_jobs_status_posted_at
```

Existing jobs are conservatively marked as baseline imports. Existing and new profiles default to 30-day strict freshness.
