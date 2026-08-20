# Radar Phase 4 — Jobs and Telegram Troubleshooting

## 1. Use a frontend-specific environment file

Next.js runs from `frontend/`, so create:

```text
radar/frontend/.env.local
```

For local UI testing against the deployed Render/Supabase environment:

```dotenv
RADAR_API_URL=https://YOUR-RENDER-SERVICE.onrender.com
RADAR_SESSION_MAX_AGE_SECONDS=3600
```

Do not add a trailing space. Normally omit `NEXT_PUBLIC_API_URL`.

After changing this file, stop `npm run dev` and start it again. Sign out or clear the `radar_access_token` cookie, then log in again so the JWT is issued by the same Render backend the UI now uses.

## 2. Why a Telegram link can become invalid

The one-time link token is stored in the database used by the API that creates it. Telegram sends `/start TOKEN` to the deployed webhook on Render. Therefore both operations must use the same production database:

```text
Local browser -> Next.js -> Render -> Supabase (create token)
Telegram -> Render webhook -> Supabase (consume token)
```

If the frontend silently points to local FastAPI/local PostgreSQL, Render cannot find the token and replies that it is invalid, expired, or already used.

## 3. Check which Radar account owns Telegram

Run in Supabase SQL Editor:

```sql
SELECT
    u.email,
    tc.username,
    tc.verified,
    tc.connected_at
FROM telegram_connections tc
JOIN users u ON u.id = tc.user_id
ORDER BY tc.connected_at DESC;
```

A Telegram account can belong to only one Radar user. If it is already linked to a different email, sign into that Radar account and disconnect first, or continue using that account.

## 4. Why the Jobs page can be empty

`/jobs` is user-scoped. The `Matched` tab does not display every row in `jobs`; it displays jobs with a `job_matches` row for the signed-in user.

Check production data in Supabase:

```sql
SELECT COUNT(*) AS companies FROM companies;
SELECT status, COUNT(*) FROM jobs GROUP BY status ORDER BY status;
SELECT COUNT(*) AS active_jobs FROM jobs WHERE status = 'ACTIVE';
```

Then inspect profiles and matches:

```sql
SELECT
    u.email,
    jp.name,
    jp.enabled,
    jp.job_titles,
    jp.locations,
    jp.work_modes,
    jp.excluded_keywords,
    COUNT(jm.id) AS match_count
FROM users u
JOIN job_profiles jp ON jp.user_id = u.id
LEFT JOIN job_matches jm ON jm.job_profile_id = jp.id
GROUP BY u.email, jp.id
ORDER BY u.email, jp.created_at;
```

If `active_jobs` is zero, seed/run the monitor against the Supabase database. If active jobs exist but `match_count` is zero, use an exact current job title with no location/work-mode/exclusion restrictions as a smoke-test profile. Creating or updating an enabled profile backfills matches against existing ACTIVE jobs.
