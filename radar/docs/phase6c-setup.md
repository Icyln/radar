# Radar Phase 6C — Upgrade, Freshness, and Acceptance Test

Phase 6C makes Radar freshness-aware and keeps company-registry growth user-friendly.

## 1. Product decision: users do not upload company CSVs

Ordinary users should not need to understand ATS catalogs or upload hundreds of companies. Wide Search uses Radar's shared registry, which Phase 6B grows automatically from system-managed catalogs/feeds. CSV/JSON remains an admin/engineering ingestion mechanism only. Users may optionally request one missing company from Discovery, but company submission is not required for Wide Search.

## 2. What Phase 6C adds

Each Job Profile has:

- Maximum job age: 1 / 3 / 7 / 14 / 30 / 60 / 90 days or Any age
- Default: Last 30 days
- `include_unknown_posted_at`: disabled by default

Radar also records whether a job was imported during a company's initial baseline.

Freshness evidence:

```text
ATS posted_at exists
  -> use posted_at

ATS posted_at missing + job discovered after baseline
  -> use first_seen_at

ATS posted_at missing + job imported during initial baseline
  -> UNKNOWN
```

This prevents old undated board inventory from appearing fresh just because Radar discovered the company today.

## 3. Upgrade Supabase

From PowerShell:

```powershell
cd C:\Users\User\radar\backend
.\.venv\Scripts\Activate.ps1
```

Make sure `DATABASE_URL` points to your production Supabase database. Then:

```powershell
alembic upgrade head
alembic current
```

Expected:

```text
0007_phase6c
```

Do not recreate the database.

Migration 0007 adds:

```text
job_profiles.max_job_age_days
job_profiles.include_unknown_posted_at
jobs.baseline_imported
ix_jobs_status_posted_at
```

Existing profiles become strict 30-day profiles. Existing jobs are conservatively considered baseline inventory; jobs that already have `posted_at` still use that timestamp.

## 4. Run backend tests

```powershell
pytest
```

This build's expected backend suite is:

```text
54 passed
```

## 5. Frontend validation

```powershell
cd C:\Users\User\radar\frontend
npm install
npm run lint
npm run typecheck
npm run build
npm run dev
```

## 6. Profile test

Open `/profiles` and edit a profile.

Recommended test:

```text
Coverage: Wide Search
Freshness: Last 30 days
Unknown posting dates: unchecked
```

Save the profile.

Old jobs with reliable posting timestamps older than 30 days should disappear from the current Matched view. Historical job/match rows remain stored.

## 7. Unknown date behavior

Strict freshness does not blindly use `first_seen_at` for the initial board snapshot.

- If an undated job came from the company's first sync: it is `UNKNOWN` and excluded by default.
- If an undated job first appears on a later monitor run: Radar treats first detection as freshness evidence, because it is genuinely new relative to Radar's established baseline.
- If you enable “Include baseline jobs when posting date is unavailable,” unknown baseline jobs may appear even though their real age cannot be guaranteed.

## 8. Detected filter test

Open:

```text
/jobs?view=detected
```

The Detected UI defaults to Last 30 days and supports:

```text
Last 24 hours
Last 3 days
Last 7 days
Last 14 days
Last 30 days
Last 60 days
Last 90 days
Posting date unknown
Any time
```

Choose `Any time` to inspect all retained jobs.

## 9. Telegram semantics

Phase 6C distinguishes dashboard matching from a fresh-job alert.

```text
Initial source sync
  -> may create fresh matches when a reliable posted_at is within the profile window
  -> never sends historical Telegram alerts

Existing job changes title/details
  -> may become a dashboard match
  -> does not create a “new job” Telegram alert

New job identity appears after baseline
  -> must pass profile coverage/title/location/work mode/exclusions/freshness
  -> may enqueue exactly one Telegram notification
```

This preserves Radar's early-warning behavior instead of treating old inventory or edited postings as newly published.

## 10. Useful SQL checks

Profiles:

```sql
SELECT
    name,
    coverage_mode,
    max_job_age_days,
    include_unknown_posted_at,
    enabled
FROM job_profiles
ORDER BY created_at;
```

Job freshness evidence:

```sql
SELECT
    c.name,
    j.title,
    j.posted_at,
    j.first_seen_at,
    j.baseline_imported,
    j.status
FROM jobs j
JOIN companies c ON c.id = j.company_id
ORDER BY j.first_seen_at DESC
LIMIT 100;
```

Jobs with a reliable posting timestamp older than 30 days:

```sql
SELECT c.name, j.title, j.posted_at
FROM jobs j
JOIN companies c ON c.id = j.company_id
WHERE j.posted_at IS NOT NULL
  AND j.posted_at < now() - interval '30 days'
ORDER BY j.posted_at DESC;
```

Undated baseline inventory:

```sql
SELECT c.name, j.title, j.first_seen_at
FROM jobs j
JOIN companies c ON c.id = j.company_id
WHERE j.posted_at IS NULL
  AND j.baseline_imported = true
ORDER BY j.first_seen_at DESC;
```

## 11. GitHub Actions

No new GitHub secret is required for Phase 6C. Existing Phase 5 scheduled monitoring and Phase 6B discovery workflows continue to use the same production database and Telegram configuration.

After pushing the code/migration, manually run Scheduled Monitoring once after upgrading Supabase. New source synchronizations will then persist the baseline marker correctly.

## 12. Acceptance result

Phase 6C is successful when:

```text
system registry grows without user CSV uploads
→ profile defaults to Last 30 days
→ old dated jobs are not current matches
→ undated baseline jobs do not look fresh
→ genuinely new undated post-baseline jobs can still match
→ Detected can inspect 30-day / unknown / any-time inventory
→ initial baseline and updated existing jobs do not cause Telegram “new job” alerts
```
