# Phase 7C — Wide Job Ingestion

Phase 7C changes Wide Search from **company-first** discovery to **job-first** discovery.

## User-visible behavior

For an enabled WIDE profile, a credible fresh job from a configured public hiring provider is now stored, matched, and displayed immediately even when the employer is not yet in Radar's company registry or watchlist.

The Jobs page now includes **Refresh Wide Search**. Clicking it runs the fast discovery path for the signed-in user's enabled WIDE profiles and shows:

- hiring signals checked;
- relevant signals;
- new WIDE jobs;
- existing/updated jobs;
- new profile matches;
- ATS-upgrade candidates staged.

Job cards show either **Wide discovery · <provider>** or **Direct ATS**. The Detected tab can filter to **Wide discovery**.

## Architecture

```text
WIDE profile titles
      ↓
public hiring APIs / feeds
      ↓
fresh matching job signal
      ↓
store Job immediately
(company_id and ats_provider may still be NULL)
      ↓
profile matching + dashboard + optional Telegram
      ↓
parallel ATS resolution
      ↓
Greenhouse / Lever / Ashby verified?
      ↓ yes
attach verified company
      ↓
direct monitor upgrades the same unambiguous job row
```

Registry membership is therefore an optimization and verification layer, not a visibility gate.

## Migration

Run:

```powershell
cd backend
alembic upgrade head
```

The new revision is `0009_phase7c`.

It makes `jobs.company_id` and `jobs.ats_provider` nullable for unresolved WIDE jobs and adds explicit provenance fields:

- `source_kind`
- `source_provider`
- `source_external_id`
- `source_company_name`

Existing ATS jobs are backfilled as `DIRECT_ATS` by the migration default.

## Fast user-side acceptance test

1. Start backend and frontend normally.
2. Open **Profiles** and enable a **Wide Search** profile, for example `Frontend Engineer, Full Stack Engineer, Web Developer` with a 30-day freshness window.
3. Do not add test companies to your watchlist.
4. Open **Jobs**.
5. Click **Refresh Wide Search**.
6. Wait for the result counters to appear.
7. Confirm **Relevant > 0** and preferably **New jobs > 0** on the first run.
8. Stay on **Matched**. Fresh matching jobs from previously unknown employers should appear with a blue **Wide discovery** badge.
9. Open **Detected** and select **Source scope → Wide discovery** to see all currently retained feed jobs.
10. Click **Refresh Wide Search** again. Existing jobs should be reused instead of duplicated.

A provider such as Arbeitnow may be unavailable from a particular network. Phase 7C records the provider warning and continues with other sources instead of aborting the refresh.

## Expected first-run example

If the discovery provider returns 59 signals and 29 are relevant to the profile, Phase 7C can now make those relevant jobs usable immediately. ATS resolution may still promote only a subset of employers; that no longer suppresses the remaining jobs.

## Direct ATS upgrade / deduplication

When a hiring signal later resolves to a verified ATS company, Radar attaches the WIDE job to that company. On the company's direct ATS sync, an unambiguous same-title/location WIDE row is upgraded in place to `DIRECT_ATS`, retaining its existing job ID/matches rather than creating an obvious duplicate.

Ambiguous roles are not force-merged.
