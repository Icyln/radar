# Phase 7 — Profile-driven active-hiring discovery

Phase 7 changes Wide Search from **registry-only coverage** into **profile-driven discovery + registry monitoring**.

Ordinary users still do not upload company CSV files and do not need to know company career URLs, ATS providers, or ATS identifiers.

## Product behavior

A user creates an enabled Wide profile such as:

```text
Web Development
Titles:
- Frontend Engineer
- Full Stack Engineer
- Web Developer
Coverage: Wide Search
Freshness: Last 30 days
```

Radar turns those titles into bounded system discovery demand:

```text
enabled WIDE profiles
        |
        v
unique target job titles
        |
        v
fresh public hiring signals
        |
        v
company identity + signal metadata
        |
        v
exact ATS extraction / bounded tenant probes
        |
        v
collector validation
        |
        v
shared company registry
        |
        v
Phase 5 direct ATS monitoring
        |
        v
NormalizedJob -> matching -> Telegram
```

The public hiring indexes are discovery seeds only. They do not bypass the source validation pipeline and they do not write jobs directly to Radar's main job table.

### Phase 7.1 resolver hardening

Radar does **not** crawl aggregator job-detail pages as company discovery targets. In
particular, Himalayas documents `applicationLink` as the application page on Himalayas,
not the employer's direct careers URL. Those pages can also return HTTP 403 to automated
HTML clients.

Instead Radar now resolves each fresh signal in this order:

1. use an exact Greenhouse/Lever/Ashby URL when one is present in the signal or embedded payload;
2. infer an ATS family when the payload contains a supported ATS hostname;
3. generate a small bounded set of tenant identifiers from the provider's canonical company slug/name;
4. query the supported ATS APIs directly;
5. require the validated ATS board to contain the signal's normalized job title before promotion.

This makes aggregator pages provenance/evidence records rather than HTML crawl targets and
prevents a guessed tenant slug from promoting an unrelated company.

## Built-in discovery signal adapters

Phase 7 includes two no-key adapters:

- Arbeitnow Europe and UK job-board APIs. Radar reads a bounded number of newest pages and filters them locally against enabled Wide-profile titles.
- Himalayas public remote-jobs search API. Radar issues bounded title queries generated from enabled Wide profiles.

The adapters are intentionally bounded through configuration. Additional active-hiring/search providers can later implement the same `HiringSignalProvider` contract without changing the user profile model or the normalized job lifecycle.

## Relevance and freshness

A hiring signal is queued only when:

1. at least one active user has an enabled `WIDE` profile;
2. the signal title contains all normalized tokens of at least one profile title;
3. the signal exposes a posting/publication timestamp;
4. the timestamp is inside both the system Phase-7 maximum age and the matching profile's age window; and
5. the signal is not implausibly future-dated.

This means Phase 7 is intentionally about companies that have evidence of **current hiring for a user's target role**, rather than indiscriminately crawling arbitrary companies.

## Discovery target evidence

`discovery_targets` now stores optional Phase-7 evidence:

- `signal_external_id`
- `job_title_hint`
- `job_location_hint`
- `job_posted_at_hint`

Phase-7 targets remain `SYSTEM_FEED` targets so the existing PostgreSQL enum does not need a risky production rewrite. Their `source_label` begins with `hiring-signal:`.

Hiring-signal targets are marked complete after their direct ATS candidates are staged;
`pages_scanned = 0` is expected. User-submitted and Phase-6 system-feed targets still use
the normal HTML crawler when needed.

## Monitoring priority

A newly validated company discovered from a fresh hiring signal keeps `LOW` as its stored/base monitoring priority, but receives a temporary discovery boost. While `discovery_boost_until` is in the future, the Phase-5 scheduler treats that `LOW` company as effective `NORMAL`. The default boost window is 7 days and can be configured with `DISCOVERY_HIRING_PRIORITY_BOOST_DAYS`.

If an existing `LOW` source receives another fresh Phase-7 signal, Radar extends the boost only when the signal supports a later expiry. Radar does not overwrite an administrator's stored `HIGH` or `NORMAL` priority. After the boost expires, a base-`LOW` company automatically returns to the normal LOW rotation without a cleanup job.

This does not alter user watchlists. A Phase-7 discovery target always has `auto_watch = false` and no submitting user.

## Safe first-sync alert exception

Phase 6C correctly made the first synchronization of a newly discovered company silent. Without an exception, however, Phase 7 could discover a company because of a fresh role and then suppress the exact role that caused discovery.

Phase 7 therefore adds a narrow evidence bridge:

```text
fresh external hiring signal
        +
validated ATS source
        +
first ATS synchronization
        +
exact unambiguous role identity
        |
        v
job.discovery_signal_at
        |
        +--> secondary freshness evidence
        +--> that specific new match may notify
```

Safety rules:

- provider `posted_at` still has highest freshness authority;
- external signal time is used only when the signal can identify exactly one baseline job safely;
- exact normalized title is required;
- if multiple same-title baseline jobs exist, Radar requires a unique URL or location resolution; otherwise the signal is ignored for alert purposes;
- one signal never turns multiple ambiguous baseline jobs into fresh alerts;
- unrelated baseline inventory remains `UNKNOWN` when the ATS has no publication date;
- updated existing jobs still do not masquerade as newly posted alerts.

Freshness precedence is now:

```text
1. POSTED_AT
2. DISCOVERY_SIGNAL
3. FIRST_SEEN (post-baseline jobs only)
4. UNKNOWN
```

## Scaling model

Phase 7 is not a promise to enumerate every employer on the internet. The supported ATS APIs are organization/board scoped, so Radar needs independent discovery signals to learn which organizations to validate.

The scalable path is:

```text
more enabled profile demand
+ more bounded hiring-signal adapters
+ larger trustworthy system datasets
        |
        v
shared validated ATS registry
        |
        v
thousands of direct monitored sources
```

Users should never be required to maintain the registry themselves.

## Database migration

Phase 7 adds migration:

```text
0008_phase7
```

Upgrade with:

```powershell
cd backend
alembic upgrade head
```

The migration preserves all existing Phase 0–6C data.
