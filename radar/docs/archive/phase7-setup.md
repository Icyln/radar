# Phase 7 setup and acceptance test

## 1. Upgrade the code and database

From the backend directory:

```powershell
python -m pip install -e ".[dev]"
alembic upgrade head
alembic current
```

Expected head:

```text
0008_phase7
```

## 2. Phase-7 environment settings

The defaults work without API keys:

```dotenv
DISCOVERY_HIRING_SIGNALS_ENABLED=true
DISCOVERY_HIRING_MAX_AGE_DAYS=30
DISCOVERY_HIRING_MAX_QUERIES=25
DISCOVERY_HIRING_MAX_SIGNALS_PER_RUN=500
DISCOVERY_HIRING_MAX_IDENTIFIER_GUESSES=3
DISCOVERY_HIRING_MAX_PROBE_CANDIDATES_PER_RUN=150
DISCOVERY_HIRING_REQUEST_TOTAL_TIMEOUT_SECONDS=25
DISCOVERY_HIRING_ARBEITNOW_ENABLED=true
DISCOVERY_HIRING_ARBEITNOW_PAGES=2
DISCOVERY_HIRING_HIMALAYAS_ENABLED=true
DISCOVERY_HIRING_PRIORITY_BOOST_DAYS=7
```

Keep `DISCOVERY_SYSTEM_FEED_URLS` if you already use curated Phase-6B feeds. Phase 7 complements those feeds; it does not replace them.

## 3. Create an enabled Wide profile

For a useful acceptance test, create something like:

```text
Name: Web Development
Coverage: Wide Search
Titles:
- Frontend Engineer
- Full Stack Engineer
- Web Developer
Freshness: Last 30 days
Unknown dates: excluded
```

No company URL and no CSV are required.

## 4. Run discovery locally

```powershell
cd backend
python -m app.workers.discovery --auto-promote --ingest-system-feeds --ingest-hiring-signals --revalidate-promoted
```

The JSON summary now includes:

```text
hiring_profiles
hiring_queries
hiring_signals_seen
hiring_signals_relevant
hiring_targets_queued
hiring_targets_existing
hiring_targets_resolved
hiring_probe_candidates_staged
hiring_probe_candidates_existing
hiring_provider_failed
```

Expected behavior:

- `hiring_profiles` is greater than zero when at least one active enabled Wide profile exists;
- `hiring_queries` reflects unique profile titles, bounded by configuration;
- only fresh title-relevant signals are queued;
- repeated runs deduplicate the same external signal;
- Himalayas/Arbeitnow listing pages are not crawled as HTML discovery targets;
- Radar stages exact or bounded guessed Greenhouse/Lever/Ashby tenants and validates their APIs directly;
- guessed tenants must contain the external signal title before they can be promoted;
- a fresh signal-discovered company retains base `LOW` priority and receives a temporary effective-`NORMAL` discovery boost (7 days by default).

A signal target can legitimately finish with no valid ATS candidate. That means the
employer is on an unsupported ATS or none of the bounded tenant probes validated. Radar
does not promote an unvalidated source merely because an external index listed a job.

If you upgraded from the original Phase 7 build and already have failed Himalayas targets
with HTTP 403, simply run the command above once. Matching signal records are repaired in
place: the old failed target becomes a completed provenance record and direct ATS probes
are staged instead of retrying the Himalayas HTML page.

## 5. GitHub Actions

`.github/workflows/discovery.yml` now runs at 00:23, 06:23, 12:23, and 18:23 UTC:

```text
23 0 * * *
23 6 * * *
23 12 * * *
23 18 * * *
```

The 00:23 UTC run enables Himalayas; the other scheduled runs skip it because Himalayas documents a 24-hour refresh window. Manual workflow dispatch enables it for an explicit test.

It includes:

```text
--ingest-hiring-signals
```

The Phase-5 monitor remains on its existing 30-minute schedule. Discovery and monitoring stay independent of Render.

You can still manually test in GitHub:

```text
Repository -> Actions -> Source Discovery -> Run workflow
```

## 6. Dashboard checks

On the Discovery page, an administrator can see:

- Fresh hiring targets
- Signal-promoted sources
- Fresh baseline roles identified
- All system targets
- System-promoted sources
- Revalidation warnings

Normal users see that registry growth is automatic and the company-request form remains optional.

## 7. First-sync Telegram acceptance test

The intended behavior is:

```text
Phase 7 sees a fresh "Frontend Engineer" signal
        |
        v
Radar discovers + validates Company X ATS
        |
        v
Company X first ATS sync contains:
- Frontend Engineer      <- uniquely tied to signal
- Senior Frontend Engineer (undated baseline)
- Accountant             (undated baseline)
        |
        v
Frontend Engineer may match + notify
other undated baseline inventory remains baseline/UNKNOWN
```

If the external signal cannot uniquely identify one same-title baseline job, Radar refuses to use it as first-sync notification evidence.

## 8. Automated verification

Run:

```powershell
cd backend
pytest
ruff check .

cd ..\frontend
npm run lint
npm run typecheck
npm run build
```

The Phase-7 tests cover profile-driven signal ingestion, title/freshness filtering, system target creation, temporary signal-based monitoring boosts, freshness precedence, safe baseline evidence, initial-sync alert isolation, summary metrics, and the six-hour workflow trigger.
