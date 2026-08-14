# Radar Phase 4 — Web Dashboard Setup and Deployment

Phase 4 turns the Next.js foundation into the management interface for the Phase 2/3 domain and API.

## What Phase 4 adds

- Register and sign in pages
- HttpOnly cookie session managed by Next.js Route Handlers
- Protected dashboard shell and responsive navigation
- Dashboard summary and recent matching jobs
- Job profile create/edit/enable/pause/delete
- Matched, saved, ignored, active, unknown, and closed job views
- Save / Ignore / clear-state actions
- Company monitoring status
- Administrator company creation and enable/pause controls
- Account settings
- Telegram status, one-time link generation, and disconnect
- Loading, error, and empty states

The Phase 4 frontend uses the existing Phase 3 FastAPI API. There is no new database migration for Phase 4.

---

## 1. Prerequisites

You should already have:

- Phase 0–3 code
- PostgreSQL/Supabase migration head `0002_phase2_phase3`
- Render FastAPI deployment working
- `https://YOUR-RENDER-SERVICE.onrender.com/health` returning HTTP 200
- `https://YOUR-RENDER-SERVICE.onrender.com/ready` returning HTTP 200
- Telegram webhook working if Telegram linking is required
- Node.js and npm installed locally

Check Node/npm:

```powershell
node --version
npm --version
```

---

## 2. Important Phase 4 authentication design

The browser does **not** store Radar's JWT in `localStorage`.

Flow:

```text
Browser
   |
   | POST /api/radar/auth/login
   v
Next.js Route Handler
   |
   | POST /api/v1/auth/login
   v
FastAPI / Render
   |
   | JWT response
   v
Next.js stores JWT in HttpOnly cookie
   |
   v
Browser receives session cookie, not the raw token
```

For protected browser actions:

```text
Browser -> /api/radar/... -> Next.js -> Authorization: Bearer <cookie JWT> -> FastAPI
```

For Server Components:

```text
Next.js Server Component -> reads HttpOnly cookie -> FastAPI
```

This preserves the Phase 3 FastAPI JWT model while keeping the token out of normal browser JavaScript.

---

## 3. Update the project files

Replace your current project with the Phase 0–4 package while preserving your real backend/root `.env`. The Next.js frontend uses its own `frontend/.env.local`.

Do not overwrite or commit your real secrets.

Your project should contain:

```text
radar/
├── backend/
├── frontend/
│   ├── app/
│   │   ├── (auth)/
│   │   ├── (dashboard)/
│   │   └── api/radar/
│   ├── components/
│   ├── lib/
│   └── types/
├── docs/
├── .env
└── frontend/.env.local
```

---

## 4. Local frontend environment

The frontend now prefers a private server-side variable:

```dotenv
RADAR_API_URL=http://localhost:8000
```

`NEXT_PUBLIC_API_URL` is retained only as a compatibility fallback.

For local frontend development, create `frontend/.env.local` (not the monorepo root `.env`):

```dotenv
RADAR_API_URL=http://localhost:8000
RADAR_SESSION_MAX_AGE_SECONDS=3600
```

To make the local frontend talk to the **deployed Render API / Supabase** instead of local FastAPI, put this in `frontend/.env.local`:

```dotenv
RADAR_API_URL=https://YOUR-RENDER-SERVICE.onrender.com
RADAR_SESSION_MAX_AGE_SECONDS=3600
```

Do not place the JWT itself in `.env`.

---

## 5. Install frontend dependencies

From PowerShell:

```powershell
cd C:\Users\User\radar\frontend
npm install
```

Then run all quality checks:

```powershell
npm run lint
npm run typecheck
npm run build
```

The generated `next-env.d.ts` remains excluded from ESLint so the Next.js route-types triple-slash directive does not fail lint.

All three commands should complete successfully before deployment.

---

## 6. Run the frontend locally against local FastAPI

Terminal 1:

```powershell
cd C:\Users\User\radar\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Terminal 2:

```powershell
cd C:\Users\User\radar\frontend
npm run dev
```

Open:

```text
http://localhost:3000
```

Radar redirects unauthenticated users to:

```text
http://localhost:3000/login
```

---

## 7. Run the frontend locally against Render + Supabase

This is useful before Vercel deployment because it tests the UI against production data.

Set this in `frontend/.env.local`:

```dotenv
RADAR_API_URL=https://YOUR-RENDER-SERVICE.onrender.com
RADAR_SESSION_MAX_AGE_SECONDS=3600
```

Restart Next.js after changing environment variables:

```powershell
npm run dev
```

Then open:

```text
http://localhost:3000
```

Register/sign in using an account that exists in the Render/Supabase production database.

Because Next.js talks to Render server-to-server, the browser does not need to call Render directly for normal dashboard API requests.

---

## 8. Phase 4 local acceptance test

### Authentication

1. Open `/register` or `/login`.
2. Authenticate successfully.
3. Confirm redirect to `/dashboard`.
4. Refresh the page.
5. Confirm you remain signed in.
6. Use `Sign out` and confirm redirect to `/login`.

### Dashboard

Confirm the overview shows:

- Active profiles
- Monitored companies
- Jobs discovered today
- Matches today
- Alerts sent today
- Last successful crawler run
- Recent matching jobs

### Job profiles

Open `/profiles`.

Create a profile such as:

```text
Name: Backend jobs
Titles: Backend Engineer, Python Developer
Locations: Remote, Singapore
Work modes: Remote, Hybrid
Excluded: Senior, Staff, Manager
```

Verify you can:

- create
- edit
- pause/enable
- delete

### Jobs

Open `/jobs`.

Verify filters:

```text
Matched
Saved
Ignored
```

and lifecycle filters:

```text
Active
Unknown
Closed
```

For a matched job:

1. click Save
2. open Saved
3. verify it appears
4. click Ignore to switch state or Unsave to clear state

Saved and Ignored are mutually exclusive because the backend uses the unified `user_job_states` model.

### Companies

Open `/companies`.

All authenticated users can inspect monitored companies.

If your user is an administrator, also verify:

- Add company
- Pause monitoring
- Enable monitoring

### Telegram

Open `/settings`.

If already linked, connection status should display `Connected`.

If not linked:

1. click `Connect Telegram`
2. Radar requests a new one-time link token
3. Telegram opens in a new tab/window
4. press Start in the bot
5. Telegram should reply that it is connected
6. refresh `/settings`
7. connection status should now be `Connected`

Also test Disconnect if desired.

---

## 9. Commit Phase 4 to GitHub

From repository root:

```powershell
cd C:\Users\User\radar
git status
git add .
git commit -m "Complete Radar Phase 4 dashboard"
git push
```

Check carefully that `.env` is not staged:

```powershell
git status
```

Never push real Telegram, database, JWT, or webhook secrets.

---

## 10. Create the Vercel project

In Vercel:

```text
Add New
→ Project
→ Import your Radar GitHub repository
```

Configure:

```text
Framework Preset: Next.js
Root Directory: frontend
```

Vercel should detect the normal commands from `frontend/package.json`.

Build command can remain the Next.js default:

```text
next build
```

No Docker is required.

---

## 11. Vercel environment variables

Add these to the Vercel **Production** environment:

```text
RADAR_API_URL=https://YOUR-RENDER-SERVICE.onrender.com
RADAR_SESSION_MAX_AGE_SECONDS=3600
```

`RADAR_API_URL` is intentionally **not** prefixed `NEXT_PUBLIC_`; it is used by Next.js server code and the Route Handler proxy.

You may leave `NEXT_PUBLIC_API_URL` unset in Vercel.

Do not add:

- `DATABASE_URL`
- `JWT_SECRET`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET`

Those belong to the backend/worker environments, not the frontend.

---

## 12. Deploy Vercel

Click Deploy.

After a successful build, Vercel provides a URL similar to:

```text
https://radar-example.vercel.app
```

Open it. You should be redirected to `/login` unless you already have a cookie for that domain.

---

## 13. Update Render `FRONTEND_URL`

Once you know the final Vercel URL, go to:

```text
Render
→ radar-api
→ Environment
```

Change:

```text
FRONTEND_URL=http://localhost:3000
```

to:

```text
FRONTEND_URL=https://radar-example.vercel.app
```

Save/deploy Render.

Although Phase 4 normally uses a same-origin Next.js proxy, keeping the correct frontend origin in FastAPI CORS is still the correct production configuration and preserves direct API compatibility where explicitly needed later.

---

## 14. Production acceptance test

Use only the Vercel URL for this test.

Verify:

```text
Vercel Next.js
   ↓
Render FastAPI
   ↓
Supabase PostgreSQL
```

and for Telegram linking:

```text
Vercel
   ↓ request link token
Render
   ↓ stores token
Supabase

Telegram /start token
   ↓
Render webhook
   ↓
Supabase connection
```

Test in this order:

1. Login
2. Dashboard
3. Create/edit profile
4. Jobs filters
5. Save/Ignore
6. Companies
7. Settings
8. Telegram connection
9. Sign out and sign back in

---

## 15. Troubleshooting

### Login says `invalid credentials`

Make sure the account exists in the same database used by the Render API referenced by `RADAR_API_URL`.

Local PostgreSQL users and Supabase users are separate unless you deliberately migrated them.

### Dashboard gives an API error after Render has been idle

Render Free can sleep. Retry after the service wakes. The Phase 4 error screen includes a retry action.

### Vercel build cannot reach Render

The build itself should not need live Radar data because protected pages use request cookies and dynamic rendering. Confirm `RADAR_API_URL` is set for runtime anyway.

### Login succeeds but refresh returns to login

Check:

- browser cookies are enabled
- Vercel uses HTTPS
- `RADAR_SESSION_MAX_AGE_SECONDS` is positive
- the backend JWT lifetime has not already expired

A sensible pair is:

```text
Render: JWT_ACCESS_TOKEN_MINUTES=60
Vercel: RADAR_SESSION_MAX_AGE_SECONDS=3600
```

### Telegram Connect opens nothing

Allow popups/new tabs for the Radar site, then try again. The API must also have `TELEGRAM_BOT_USERNAME` configured on Render.

### Telegram says token invalid or expired

Generate a new link from Settings. Link tokens are deliberately short-lived and single-use.

### Company creation returns administrator required

Your logged-in production user is not an admin. Set the account as admin using the existing backend admin procedure and the production database.

---

## 16. Phase 4 definition of done

Phase 4 is complete when a user can perform the normal Radar management flow without Swagger or PowerShell:

```text
Register/Login
    ↓
Dashboard
    ↓
Create monitoring profile
    ↓
View matching jobs
    ↓
Save / Ignore jobs
    ↓
Inspect monitored companies
    ↓
Connect Telegram
    ↓
Manage account from web UI
```

The next project phase is Phase 5: automated GitHub Actions monitoring, CI hardening, batching/concurrency protection, and production worker configuration.
