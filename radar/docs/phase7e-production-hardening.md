# Phase 7E — Final Production Hardening

Phase 7E is the finishing phase for the current Radar release. It does not add a new user workflow or a scraping service. It hardens the Phase 7C/7D architecture so Wide Search, direct ATS monitoring, and Telegram delivery can run unattended.

## What changed

### 1. Deeper bounded Wide Search coverage

Radar now reads more than the first Himalayas page for each enabled Wide-profile title and increases the bounded Arbeitnow page window. Defaults:

```env
DISCOVERY_HIRING_ARBEITNOW_PAGES=4
DISCOVERY_HIRING_HIMALAYAS_PAGES=3
DISCOVERY_HIRING_MAX_SIGNALS_PER_RUN=1000
```

The user-facing **Refresh Wide Search** result now shows **Feed pages** and **Sources reached**, making the deeper search visible without terminal diagnostics.

### 2. Per-source failure isolation and health

Each public hiring source records its own successes, pages, and warnings. One provider can fail while remaining providers continue. The final worker run is marked `PARTIAL`/degraded instead of crashing useful discovery.

The Overview page now shows separate health cards for:

- **Direct ATS monitoring**
- **Wide Search automation**

States are `Healthy`, `Degraded`, `Failed`, `Needs attention` (stale), `Running`, or `Waiting for run`.

### 3. Persistent Wide Search run history

Migration `0010_phase7e` adds `discovery_runs`. Scheduled GitHub discovery and manual UI refreshes record useful run metadata including signals, new jobs, duplicates merged, provider failures, notifications, and lifecycle changes.

GitHub Source Discovery sets:

```env
DISCOVERY_RUN_TRIGGER=github-actions
DISCOVERY_EXTERNAL_RUN_ID=<github run id>.<attempt>
```

The dashboard prefers GitHub-run health when available, so manual testing does not hide production automation state.

### 4. Cross-source job deduplication

Migration `0010_phase7e` also adds `job_source_observations`.

One Radar job can now retain multiple source observations. Conservative identity matching uses:

- normalized company identity,
- exact normalized job title,
- compatible location,
- publication date proximity when both sources expose a date.

Ambiguous roles are not merged.

This handles both:

```text
Himalayas job
+ Arbeitnow copy
→ one Radar card
```

and:

```text
Direct ATS job already exists
+ later Wide discovery copy
→ keep one Direct ATS card
→ retain Wide observation as provenance
```

The Jobs refresh panel exposes **Duplicates merged** for visible testing.

### 5. Wide-job lifecycle

Discovery-feed jobs are not allowed to remain Active indefinitely just because Radar retains history.

Default lifecycle:

```env
DISCOVERY_WIDE_UNKNOWN_AFTER_DAYS=14
DISCOVERY_WIDE_CLOSE_AFTER_DAYS=45
```

A WIDE job not observed for 14 days becomes `UNKNOWN`. After 45 days without fresh evidence (or when its freshness evidence is older than that window), it becomes `CLOSED`. A later credible Wide observation can reactivate a WIDE row.

Direct ATS jobs keep their existing authoritative missing-snapshot lifecycle.

No history is deleted. Saved/ignored history remains available through the existing status views.

### 6. Automation stale detection

Defaults:

```env
MONITOR_HEALTH_STALE_MINUTES=90
DISCOVERY_HEALTH_STALE_MINUTES=480
```

If GitHub automation stops running, the Overview page stops presenting an unconditional green indicator and instead surfaces **Needs attention**.

## Migration

From `backend`:

```powershell
alembic upgrade head
```

Expected head:

```text
0010_phase7e
```

No database reset is required.

## Production behavior

```text
Scheduled Monitoring (~30 min)
        ↓
known direct ATS companies
        ↓
PostgreSQL
        ↓
match + Telegram

Source Discovery (6-hour workflow)
        ↓
configured Wide discovery providers
        ↓
job-first ingestion
        ↓
cross-source dedup
        ↓
match + Telegram
        ↓
parallel ATS resolution / registry growth
```

The midnight UTC Source Discovery run enables Himalayas. Manual workflow dispatch also enables it. Other scheduled discovery runs can continue using other enabled providers.

## Final user-side acceptance test

1. Upgrade to `0010_phase7e` and restart the backend/frontend.
2. Open **Jobs** and click **Refresh Wide Search**.
3. Confirm the result visibly includes **Signals checked**, **Relevant**, **New jobs**, **Existing jobs**, **New matches**, **Duplicates merged**, **Feed pages**, and **Telegram**.
4. Confirm **Sources reached** appears when at least one public discovery source succeeds.
5. Open **Matched** and verify Wide discovery jobs remain visible even for employers outside the watchlist/registry.
6. Open **Overview**. Confirm two automation cards exist: **Direct ATS monitoring** and **Wide Search automation**.
7. In GitHub → Actions, manually run **Scheduled Monitoring** and **Source Discovery** once.
8. Return to Radar Overview and reload. The cards should show recent run times and a meaningful state rather than one generic crawler dot.
9. If one discovery provider fails but another succeeds, Wide Search should show `Degraded`, not `Failed`, and matching jobs from the successful provider should remain usable.
10. Confirm Telegram still receives a new matching job once and repeated refreshes do not resend the same job.

## Optional Arbeitnow switch

If Arbeitnow consistently returns HTTP 403 from GitHub runners as well as locally, create this GitHub Actions repository variable:

```text
DISCOVERY_HIRING_ARBEITNOW_ENABLED=false
```

The workflow defaults it to enabled when the variable is absent. Disabling a persistently unavailable provider removes repeated degraded warnings; Himalayas remains available on its scheduled/manual refresh window.
