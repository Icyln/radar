# Radar — Master Engineering Specification

You are the **lead senior full-stack engineer and software architect** responsible for designing and implementing **Radar**, a personal job-intelligence and early-notification platform.

Your responsibility is not merely to generate code. You must design, implement, test, document, and prepare a production-quality application that is:

- reliable
- secure
- maintainable
- cost-efficient
- modular
- observable
- easy to deploy
- easy to extend

Treat this document as the primary engineering specification for the project.

When requirements are ambiguous, prefer the **simplest reliable implementation** consistent with this specification.

Do not introduce unnecessary infrastructure, frameworks, services, AI features, abstractions, or microservices.

---

# 1. PRODUCT VISION

Radar is a **personal job opportunity intelligence and early-warning system**.

Radar is **not**:

- a traditional job board
- a LinkedIn replacement
- an applicant tracking system
- an AI career coach
- a job recommendation social network
- a general web scraper

Radar continuously monitors job postings published directly through company recruiting systems and alerts users when relevant opportunities appear.

The core value proposition is:

> **Radar detects new job postings directly from company ATS systems and notifies users as early as possible, before those jobs become widely distributed across major job platforms.**

Freshness is the primary competitive advantage.

---

# 2. INITIAL OPERATING CONSTRAINTS

The first production version is intended for:

- personal use
- approximately 1–10 users
- zero or near-zero infrastructure cost
- monitoring a manageable set of companies
- frequent monitoring of selected high-priority companies
- reliable Telegram notifications

The architecture should be designed so the monitoring layer can later scale substantially without requiring a complete rewrite.

However:

**Do not prematurely optimize the initial free-tier deployment for thousands of companies.**

Prioritize correctness and maintainability first.

---

# 3. CORE PRODUCT FLOW

The expected user flow is:

1. User creates an account.
2. User connects Telegram.
3. User creates one or more job-monitoring profiles.
4. User selects job titles, locations, work modes, and exclusions.
5. Radar monitors configured companies.
6. ATS collectors retrieve current jobs.
7. Jobs are validated and normalized.
8. Radar determines whether jobs are new, existing, missing, or closed.
9. New jobs are stored.
10. Matching rules are evaluated against user profiles.
11. Matching jobs generate notification records.
12. Telegram alerts are sent.
13. User can open, save, or ignore jobs.
14. Dashboard provides monitoring status and job history.

The critical path is:

```
ATS Source
    ↓
Collector
    ↓
Normalization
    ↓
Deduplication
    ↓
Job Lifecycle Processing
    ↓
Database
    ↓
Matching Engine
    ↓
Notification Deduplication
    ↓
Telegram

```

---

# 4. NON-NEGOTIABLE ENGINEERING PRIORITIES

Always prioritize the following in this order:

1. Freshness
2. Correctness
3. Reliability
4. Duplicate prevention
5. Security
6. Simple architecture
7. Maintainability
8. Observability
9. Cost efficiency
10. Extensibility

Do not optimize primarily for:

- AI features
- machine-learning recommendations
- semantic search
- embeddings
- microservices
- Kubernetes
- Kafka
- Redis
- Celery
- paid infrastructure
- distributed systems
- scraping LinkedIn
- scraping Indeed
- scraping other large job boards
- premature scalability

AI is not required for the initial product.

Matching must remain deterministic unless explicitly changed later.

---

# 5. REQUIRED TECHNOLOGY STACK

Use the following architecture unless a serious technical blocker exists.

## Frontend

- Next.js
- TypeScript
- React
- Tailwind CSS
- responsive UI
- modern Next.js App Router patterns
- server components where appropriate
- client components only when interactivity requires them

Deployment:

**Vercel**

---

## Backend API

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic

Deployment:

**Render Free**

The backend API must remain lightweight.

Do not depend on Render remaining continuously awake.

---

## Database

PostgreSQL hosted on:

**Supabase**

The database is the authoritative source of truth.

All important monitoring state must survive worker termination.

---

## Monitoring Engine

Python monitoring workers executed using:

**GitHub Actions scheduled workflows**

Workers must be:

- stateless
- retry-safe
- idempotent
- independently executable
- database-driven

Workers must not depend on a continuously running backend server.

---

## Notifications

Use:

**Telegram Bot API**

Telegram is the primary real-time notification channel.

---

# 6. IMPORTANT RUNTIME ARCHITECTURE

The Render-hosted FastAPI API must **not** be part of the critical monitoring execution path.

The system should behave conceptually like this:

```
                    ┌─────────────────┐
                    │      Users      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Next.js Web App │
                    │     Vercel      │
                    └────────┬────────┘
                             │ HTTPS
                             ▼
                    ┌─────────────────┐
                    │     FastAPI     │
                    │     Render      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │    Supabase     │
                    └─────────────────┘

```

Monitoring runs independently:

```
                GitHub Actions Scheduler
                         │
                         ▼
                 Python Monitor Runner
                         │
               ┌─────────┴─────────┐
               ▼                   ▼
         Read Companies       Write Logs
               │
               ▼
          ATS Collectors
               │
      ┌────────┼────────┐
      ▼        ▼        ▼
 Greenhouse   Lever    Ashby
      │        │        │
      └────────┼────────┘
               ▼
       Normalization Pipeline
               │
               ▼
        PostgreSQL Database
               │
               ▼
          Matching Engine
               │
               ▼
      Notification Deduplication
               │
               ▼
          Telegram Bot API

```

A sleeping Render instance must **not prevent job detection or Telegram notifications**.

---

# 7. REPOSITORY STRUCTURE

Use a clean monorepo.

Recommended structure:

```
radar/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── hooks/
│   ├── types/
│   ├── public/
│   └── tests/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── collectors/
│   │   ├── matching/
│   │   ├── notifications/
│   │   └── workers/
│   │
│   ├── alembic/
│   ├── tests/
│   └── scripts/
│
├── .github/
│   └── workflows/
│
├── docs/
│
├── .env.example
├── README.md
└── docker-compose.yml

```

The exact structure may be improved if justified, but maintain clear separation between:

- API
- database
- collectors
- processing
- matching
- notifications
- scheduled workers

---

# 8. DOMAIN MODEL

The following entities are required.

## User

Represents an authenticated Radar user.

Minimum fields:

```
id
email
password_hash
is_active
created_at
updated_at

```

Use UUIDs unless there is a compelling reason not to.

Emails must be unique.

Passwords must never be stored directly.

---

# 9. JOB PROFILES

A user can create multiple monitoring profiles.

Example profiles:

```
Backend Engineering
Remote Python Jobs
Singapore Engineering Roles

```

Minimum profile information:

```
id
user_id
name
enabled
job_titles
locations
work_modes
excluded_keywords
created_at
updated_at

```

Supported work modes:

```
REMOTE
HYBRID
ONSITE
UNKNOWN

```

Use a clean PostgreSQL representation for multi-value preferences.

Do not over-normalize if PostgreSQL arrays or JSONB provide a simpler and maintainable solution.

---

# 10. COMPANIES

Companies represent organizations monitored by Radar.

Minimum fields:

```
id
name
website
career_url
ats_provider
ats_identifier
monitoring_priority
active
last_checked_at
last_successful_check_at
last_error_at
consecutive_failures
created_at
updated_at

```

Supported ATS providers initially:

```
GREENHOUSE
LEVER
ASHBY

```

Monitoring priority should support at least:

```
HIGH
NORMAL
LOW

```

Add appropriate indexes.

---

# 11. JOBS

Jobs are normalized records independent of ATS provider.

Minimum fields:

```
id
company_id
ats_provider
external_job_id
title
description
location
work_mode
employment_type
apply_url
source_url
posted_at
first_seen_at
last_seen_at
missing_count
status
closed_at
fingerprint
created_at
updated_at

```

Statuses:

```
ACTIVE
UNKNOWN
CLOSED

```

`external_job_id` should be used when the ATS supplies a stable identifier.

Create a deterministic `fingerprint` as a fallback identity mechanism.

Possible fingerprint inputs include:

```
provider
company
external_job_id
title
location
apply_url

```

The implementation must prevent the same job from being inserted repeatedly.

Use database constraints in addition to application-level duplicate checking.

Do not rely exclusively on fuzzy title comparison for deduplication.

---

# 12. JOB MATCHES

Create a persistent record when a job matches a user's job profile.

Minimum fields:

```
id
user_id
job_profile_id
job_id
matched_at
match_reason
created_at

```

Enforce a uniqueness constraint preventing the same profile/job combination from being matched repeatedly.

---

# 13. SAVED AND IGNORED JOBS

Users must be able to:

- save jobs
- ignore jobs

Implement this cleanly.

You may use:

```
saved_jobs
ignored_jobs

```

or a unified user-job-state model if that results in a cleaner relational design.

Do not allow contradictory states.

---

# 14. TELEGRAM CONNECTIONS

Store Telegram linkage separately from the core user table.

Minimum information:

```
id
user_id
telegram_user_id
telegram_chat_id
username
verified
connected_at
created_at
updated_at

```

Telegram linking must use a secure one-time token or equivalent verification mechanism.

Do not allow a user to arbitrarily claim another Telegram account.

---

# 15. NOTIFICATION RECORDS

Notification delivery must be idempotent.

Create a notification/outbox-style table.

Minimum fields:

```
id
user_id
job_id
channel
status
attempt_count
last_attempt_at
sent_at
error_message
created_at
updated_at

```

Example statuses:

```
PENDING
SENDING
SENT
FAILED

```

Create an appropriate uniqueness constraint so a user cannot receive the exact same job alert repeatedly unless a future explicit retry policy requires it.

The database, not process memory, must determine whether a notification has already been sent.

---

# 16. CRAWLER LOGS

Monitoring executions must be observable.

Create `crawler_logs` or an equivalent run model.

Track at minimum:

```
id
company_id
ats_provider
started_at
completed_at
status
jobs_received
jobs_new
jobs_updated
jobs_closed
matches_created
notifications_sent
error_type
error_message
duration_ms

```

Possible statuses:

```
SUCCESS
PARTIAL
FAILED
SKIPPED

```

Do not store sensitive secrets in logs.

---

# 17. ATS COLLECTOR ARCHITECTURE

Implement ATS integrations using a shared collector contract.

Conceptually:

```
class BaseCollector:
    async def fetch_jobs(self, company) -> list[NormalizedJob]:
        ...

```

Each provider implementation must translate provider-specific data into the common normalized domain model.

Initial collectors:

```
GreenhouseCollector
LeverCollector
AshbyCollector

```

Collectors belong in a modular structure such as:

```
backend/app/collectors/
    base.py
    greenhouse.py
    lever.py
    ashby.py
    registry.py

```

Do not duplicate shared HTTP, retry, parsing, or normalization logic unnecessarily.

---

# 18. COLLECTOR RESPONSIBILITIES

Every collector must:

1. Receive company configuration.
2. Fetch jobs from the ATS.
3. Use reasonable HTTP timeouts.
4. Handle non-200 responses.
5. Handle malformed responses.
6. Handle temporary network failures.
7. Parse provider-specific fields safely.
8. Return normalized job objects.
9. Preserve provider identifiers when available.
10. Log failures without leaking secrets.
11. Distinguish source failure from a legitimate empty job list.

This distinction is critical:

```
ATS request failed

```

must never be interpreted as:

```
company currently has zero jobs

```

Otherwise temporary provider failures could incorrectly close every job.

---

# 19. NORMALIZED JOB CONTRACT

All collectors must return a common structure conceptually similar to:

```
{
  "external_job_id": "provider-job-id",
  "company_id": "uuid",
  "title": "Backend Engineer",
  "description": "...",
  "location": "Remote",
  "work_mode": "REMOTE",
  "employment_type": "FULL_TIME",
  "apply_url": "https://...",
  "source_url": "https://...",
  "posted_at": "2026-08-13T00:00:00Z"
}

```

Fields unavailable from a provider may be nullable where appropriate.

Never invent provider data.

---

# 20. JOB PROCESSING PIPELINE

Every successful collector result must go through a consistent processing pipeline.

```
Collector Response
      ↓
Schema Validation
      ↓
Provider Normalization
      ↓
Text Normalization
      ↓
Identity/Fingerprint Calculation
      ↓
Duplicate Detection
      ↓
Insert or Update
      ↓
Lifecycle Processing
      ↓
Matching
      ↓
Notification Creation
      ↓
Telegram Delivery

```

Each stage should have a clear responsibility.

Avoid giant functions.

---

# 21. JOB IDENTITY AND DUPLICATION

Duplicate alerts are unacceptable.

Use multiple levels of protection:

### Level 1 — Provider identity

Prefer:

```
ats_provider + company_id + external_job_id

```

when a reliable external ID exists.

### Level 2 — Fingerprint fallback

Generate a deterministic fingerprint when provider identity is unavailable or unreliable.

### Level 3 — Database uniqueness

Use unique database indexes or constraints.

### Level 4 — Notification uniqueness

Even if processing occurs twice because of retries or overlapping workers, the same alert must not be sent twice.

All important write operations must therefore be idempotent.

---

# 22. JOB LIFECYCLE AND EXPIRATION

Never intentionally show known closed jobs as active.

Lifecycle:

```
Newly discovered
    ↓
ACTIVE

```

When an existing job disappears from a successful ATS response:

```
ACTIVE
    ↓
UNKNOWN

```

Do not immediately close it after one missing observation.

Increment a missing counter.

After a configurable number of consecutive successful source checks where the job remains absent:

```
UNKNOWN
    ↓
CLOSED

```

When closed:

```
closed_at = current timestamp

```

If a previously missing job reappears:

```
UNKNOWN → ACTIVE

```

Reset its missing counter.

A failed collector request must not increment the missing count.

Use a configurable threshold rather than hardcoding lifecycle policy throughout the codebase.

---

# 23. MATCHING ENGINE

Initial matching must be deterministic.

Do not use AI, embeddings, LLMs, or vector databases.

Primary criteria:

1. job title
2. location
3. work mode
4. excluded keywords

Normalize strings before comparing.

Matching should be case-insensitive.

Handle common differences safely, for example:

```
Backend Engineer
backend engineer
Backend Software Engineer

```

However, do not create an overengineered NLP system.

Keep matching understandable and testable.

---

# 24. MATCHING BEHAVIOR

A reasonable initial rule is:

### Title

At least one configured title should match using deterministic normalized matching.

### Location

The job must satisfy at least one configured location when location restrictions exist.

### Work mode

The job must satisfy an allowed work mode when modes are configured.

### Exclusions

If an excluded keyword matches the job title or relevant normalized text, reject the job.

Return structured match information such as:

```
matched_title
matched_location
matched_work_mode
rejection_reason

```

This information should help debugging.

---

# 25. TELEGRAM NOTIFICATIONS

Telegram is the primary alert channel.

A new matching job should produce a concise notification such as:

```
🚨 NEW JOB FOUND

Backend Engineer
Example Company

📍 Remote Worldwide
🏠 Remote
🕒 Posted: 10 minutes ago
📡 Detected: 30 seconds ago

Apply:
https://...

```

Avoid excessive text.

Do not send the entire job description.

---

# 26. TELEGRAM INTERACTION BUTTONS

Provide inline buttons for:

```
Open Job
Save
Ignore

```

Expected behavior:

### Open Job

Open the original application URL.

### Save

Persist the saved state for the authenticated/link-associated Radar user.

### Ignore

Persist the ignored state.

Telegram callback handling must:

- validate callback data
- identify the linked Telegram user
- prevent unauthorized state changes
- handle repeated clicks safely
- answer callback queries appropriately
- remain idempotent

---

# 27. TELEGRAM LINKING

Provide a secure dashboard flow such as:

```
Dashboard
    ↓
Connect Telegram
    ↓
Generate short-lived one-time token
    ↓
User opens Telegram deep link
    ↓
/start <token>
    ↓
Radar validates token
    ↓
Telegram account linked

```

Tokens must:

- be random
- expire
- be single-use
- be tied to a user

Never place permanent credentials in the deep link.

---

# 28. WEB DASHBOARD

The web dashboard is primarily a management interface.

Telegram remains the primary notification interface.

The dashboard should be clean, responsive, and minimal.

Do not build unnecessary social or job-board features.

---

# 29. DASHBOARD PAGE

Display useful operational information.

Examples:

```
Active monitoring profiles
Monitored companies
Jobs discovered today
Matches today
Alerts sent today
Last successful crawler run
Recent matching jobs

```

Display useful empty states.

Do not show fake analytics.

---

# 30. JOB PROFILES PAGE

Users must be able to:

- create profiles
- edit profiles
- enable/disable profiles
- delete profiles

Manage:

```
Profile name
Job titles
Locations
Work modes
Excluded keywords

```

Validation must exist both client-side where useful and server-side always.

---

# 31. JOBS PAGE

Provide filtering for at least:

```
New/Matched
Saved
Ignored
Active
Closed

```

Job cards or rows should show:

```
Title
Company
Location
Work mode
Posted time
Detected time
Status
Apply link

```

Allow Save and Ignore actions from the dashboard.

---

# 32. COMPANIES PAGE

Provide a simple management interface for monitored companies.

Users/admin can inspect:

```
Company
ATS provider
ATS identifier
Priority
Active status
Last checked
Last successful check

```

For the initial personal-use version, company management may be restricted to an administrator if that simplifies security.

---

# 33. SETTINGS PAGE

Include:

```
Account information
Telegram connection
Telegram connection status
Disconnect Telegram

```

Additional settings should only be added when required.

---

# 34. API DESIGN

Use REST endpoints with consistent response patterns.

Potential route groups:

```
/api/v1/auth
/api/v1/users
/api/v1/job-profiles
/api/v1/jobs
/api/v1/companies
/api/v1/telegram
/api/v1/dashboard

```

Use versioned APIs.

Separate:

- router
- schema
- service
- persistence concerns

Do not place all logic directly in FastAPI route handlers.

---

# 35. AUTHENTICATION

Implement secure email/password authentication appropriate for this small application.

Requirements:

- secure password hashing
- unique email addresses
- authenticated protected endpoints
- token expiration
- reasonable token validation
- no plaintext password storage
- no sensitive auth data in logs

Prefer a proven password hashing algorithm such as Argon2id where supported.

If using JWTs, implement them carefully and minimally.

Do not build a custom cryptographic protocol.

---

# 36. AUTHORIZATION

Every user-specific resource must be ownership-checked.

For example:

A user must not be able to access another user's profile by changing:

```
/job-profiles/{id}

```

The backend must enforce ownership.

Never depend only on frontend hiding.

---

# 37. DATABASE ENGINEERING

Use:

- foreign keys
- unique constraints
- indexes
- explicit enums where appropriate
- UTC timestamps
- transactions where consistency matters

Create Alembic migrations.

Do not modify production schema manually.

Important indexes should include fields frequently used for:

- job identity
- company monitoring
- active jobs
- job status
- matches
- notification state
- user ownership

Avoid excessive indexing.

---

# 38. TIME HANDLING

Store timestamps in UTC.

Convert to the user's display timezone only in the presentation layer where necessary.

Never store relative strings such as:

```
"10 minutes ago"

```

Store timestamps and derive human-readable relative time at display time.

---

# 39. MONITORING SCHEDULER

Use GitHub Actions scheduled workflows.

Initial workflows:

```
.github/workflows/high_priority_monitor.yml
.github/workflows/normal_monitor.yml
.github/workflows/discovery.yml

```

---

# 40. HIGH-PRIORITY MONITOR

Purpose:

Monitor high-value companies frequently.

Target schedule:

```
approximately every 5 minutes

```

GitHub Actions scheduling must not be assumed to execute with real-time guarantees.

The system should tolerate scheduler delays.

Query companies where:

```
active = true
monitoring_priority = HIGH

```

---

# 41. NORMAL MONITOR

Monitor normal-priority companies less frequently.

The exact schedule should be configurable or clearly documented.

Avoid wasting GitHub Actions runtime unnecessarily.

---

# 42. DISCOVERY WORKFLOW

Run periodically, initially approximately daily.

Purpose:

- discover candidate ATS-backed companies
- validate known ATS identifiers
- update metadata where appropriate

Do not turn the initial discovery system into a general internet crawler.

A manually seeded company registry is acceptable for MVP.

Automatic discovery belongs to a later stage after monitoring reliability is established.

---

# 43. WORKER EXECUTION MODEL

Workers must:

1. start
2. establish database connection
3. determine eligible companies
4. process companies in bounded batches
5. record run data
6. handle individual company failures without crashing the entire run
7. perform matching
8. create notification records
9. deliver pending notifications
10. update crawler/run statistics
11. exit cleanly

No worker may rely on local filesystem state persisting between executions.

---

# 44. CONCURRENCY SAFETY

Scheduled jobs may occasionally overlap.

Design for this.

Prevent duplicate processing using database-backed mechanisms where necessary.

Possible techniques include:

- transactional updates
- unique constraints
- row locking
- PostgreSQL advisory locks
- short database leases

Choose the simplest mechanism appropriate to the operation.

Do not introduce Redis solely for locking.

---

# 45. HTTP ENGINEERING

Collectors must use a shared HTTP client strategy.

Include:

- connect timeout
- read timeout
- limited retries
- exponential or bounded backoff for temporary errors
- sensible User-Agent
- explicit error handling

Do not retry permanent 4xx failures indefinitely.

Respect source systems.

Do not create abusive traffic.

---

# 46. FAILURE HANDLING

The system must tolerate:

- network timeout
- ATS downtime
- malformed ATS response
- database connection error
- Telegram temporary error
- duplicate workflow execution
- Render sleeping
- partial worker failure
- a single broken company configuration

A failure for one company should generally not terminate monitoring for unrelated companies.

---

# 47. RETRIES

Retries must be bounded.

Never create infinite retry loops.

Classify errors where practical:

```
temporary
permanent
configuration
authentication
rate-limit
parsing
database
notification

```

Store enough information for debugging.

---

# 48. CONFIGURATION

Use environment variables for deployment-specific configuration.

Create:

```
.env.example

```

Possible values include:

```
DATABASE_URL
JWT_SECRET
TELEGRAM_BOT_TOKEN
TELEGRAM_BOT_USERNAME
FRONTEND_URL
BACKEND_URL
ENVIRONMENT
LOG_LEVEL

```

Never commit actual secrets.

---

# 49. GITHUB ACTIONS SECRETS

Scheduled workers must receive required secrets through GitHub Actions secrets.

Never:

- print secrets
- echo database credentials
- commit service credentials
- embed Telegram tokens in workflow files

---

# 50. LOGGING

Use structured, useful application logging.

Include contextual information such as:

```
company_id
provider
worker_run_id
job_id
notification_id

```

when appropriate.

Never log:

- passwords
- JWT secrets
- Telegram bot tokens
- database passwords
- private credentials

---

# 51. OBSERVABILITY

For the MVP, database run records and structured logs are sufficient.

Do not introduce expensive monitoring platforms.

The dashboard should be able to derive operational signals such as:

```
Last successful monitoring run
Companies currently failing
Recent crawler failures
Jobs detected today
Notifications sent today

```

---

# 52. FRONTEND QUALITY

The dashboard should feel like a polished modern developer/productivity tool.

Design principles:

- simple
- information-dense without clutter
- fast
- responsive
- accessible
- clear empty states
- clear loading states
- clear error states

Avoid excessive animations.

Avoid decorative complexity.

Use reusable components.

---

# 53. FRONTEND DATA ACCESS

Centralize backend API access.

Do not scatter hardcoded URLs or raw fetch logic throughout many components.

Provide:

- typed API models
- reusable API client functions
- centralized error handling where practical

Ensure loading and error states are handled.

---

# 54. SECURITY REQUIREMENTS

Implement at minimum:

- secure password hashing
- authenticated API endpoints
- authorization/ownership checks
- input validation
- ORM parameterization
- CORS configuration
- secret management
- Telegram account verification
- short-lived connection tokens
- safe error messages
- secure production configuration

Do not expose stack traces to end users in production.

---

# 55. DO NOT HARDCODE

Never hardcode:

```
DATABASE_URL
Telegram token
JWT secret
API credentials
production domains
passwords
private keys

```

---

# 56. TESTING STRATEGY

Testing is mandatory.

Do not consider a phase complete simply because code compiles.

Use automated tests for critical behavior.

---

# 57. BACKEND UNIT TESTS

At minimum test:

### Job fingerprinting

```
same source job → same identity
different source jobs → different identities

```

### Deduplication

Processing the same ATS payload twice must not create duplicate jobs.

### Matching

Test:

```
matching title
wrong title
matching location
wrong location
remote matching
excluded keyword
case normalization
multiple preferences

```

### Lifecycle

Test:

```
new → ACTIVE
missing → UNKNOWN
reappearing → ACTIVE
repeated missing → CLOSED
failed collector → no missing increment

```

### Notification idempotency

Processing a matching job twice must not produce two successful notifications.

### Collector parsing

Use stored mock responses.

Tests must not depend on live ATS services.

---

# 58. API TESTING

Test at least:

- authentication
- unauthorized access
- resource ownership
- job profile CRUD
- jobs filtering
- save
- ignore
- Telegram connection token behavior

---

# 59. FRONTEND TESTING

At minimum ensure:

- TypeScript type checking passes
- linting passes
- production build succeeds

Add focused component or end-to-end tests where they provide meaningful value.

Do not build an enormous test suite before core functionality exists.

---

# 60. CI

Create a CI workflow separate from monitoring workflows.

On appropriate pull requests/pushes run:

Backend:

```
lint
type/static checks where configured
tests

```

Frontend:

```
install
lint
typecheck
build
tests where configured

```

CI must fail when important validation fails.

---

# 61. LOCAL DEVELOPMENT

Provide a straightforward development setup.

A developer should be able to:

1. clone repository
2. copy `.env.example`
3. configure variables
4. install dependencies
5. run database migrations
6. start backend
7. start frontend
8. execute a monitor manually
9. run tests

Document every required command in `README.md`.

A lightweight Docker Compose PostgreSQL setup may be supplied for local development even though production PostgreSQL is hosted on Supabase.

---

# 62. MANUAL WORKER COMMANDS

Do not make GitHub Actions the only way to run workers.

Workers should be executable locally using commands conceptually similar to:

```
python -m app.workers.monitor --priority high
python -m app.workers.monitor --priority normal

```

Exact commands may differ based on project structure.

This greatly improves debugging.

---

# 63. DEPLOYMENT TARGETS

Production deployment:

```
Frontend
Next.js
↓
Vercel

```

```
Backend API
FastAPI
↓
Render Free

```

```
Database
PostgreSQL
↓
Supabase

```

```
Monitoring
GitHub Actions
↓
Python workers

```

```
Notifications
Telegram Bot API

```

Do not add another paid infrastructure dependency without explicit approval.

---

# 64. RENDER FREE-TIER CONSTRAINT

Assume the Render backend may sleep after inactivity.

Therefore:

**Monitoring must never depend on the Render process remaining active.**

GitHub Action workers should be able to access the database and Telegram directly using shared backend/domain modules.

The API exists primarily for:

- dashboard operations
- authentication
- user management
- settings
- Telegram callbacks/webhooks where appropriate

A cold API must not stop scheduled job collection.

---

# 65. DEVELOPMENT PHASES

Implement the product incrementally.

Do not attempt to create an enormous unverified codebase in one uncontrolled step.

---

# PHASE 0 — FOUNDATION

Create:

- monorepo structure
- Python project
- Next.js project
- configuration system
- database connection
- SQLAlchemy setup
- Alembic
- initial testing configuration
- linting
- `.env.example`
- README foundation

Definition of done:

- backend starts locally
- frontend starts locally
- database connection works
- migration command works
- test command works
- build/lint commands work

---

# PHASE 1 — MINIMUM JOB DETECTION SYSTEM

Implement:

- Company model
- Job model
- crawler run/log model
- Greenhouse collector
- normalized job schema
- deduplication
- lifecycle basics
- job persistence
- manual monitor command
- Telegram client
- basic notification delivery

At this stage, user/profile matching may temporarily use a simple test configuration if necessary.

Definition of done:

A manually triggered monitor can:

```
fetch a real configured Greenhouse company
↓
normalize jobs
↓
store new jobs
↓
run again without duplicating them
↓
detect newly added jobs
↓
send a Telegram notification

```

Tests must cover the critical pipeline using mocks.

---

# PHASE 2 — COMPLETE MONITORING CORE

Add:

- Lever collector
- Ashby collector
- User model
- Job Profile model
- Matching engine
- Job Match records
- Saved/ignored state
- Telegram connections
- notification outbox/idempotency
- complete lifecycle handling
- monitoring priorities

Definition of done:

Multiple provider responses can enter the same pipeline and produce consistent normalized job records and reliable matching notifications.

---

# PHASE 3 — BACKEND API

Implement:

- authentication
- authorization
- job profile CRUD
- jobs API
- saved/ignored actions
- dashboard summary endpoint
- company API as appropriate
- Telegram linking
- Telegram callback handling
- health endpoint

Definition of done:

The complete Radar domain can be managed through authenticated API calls.

---

# PHASE 4 — WEB DASHBOARD

Implement:

- authentication UI
- dashboard
- profile management
- jobs view
- saved jobs
- ignored jobs
- company monitoring status
- settings
- Telegram connection UI
- responsive navigation
- loading/error/empty states

Definition of done:

A user can fully configure Radar from the web interface and receive jobs through Telegram.

---

# PHASE 5 — AUTOMATED MONITORING

Implement GitHub Actions:

```
high_priority_monitor.yml
normal_monitor.yml
discovery.yml
ci.yml

```

Add:

- concurrency protection
- run logging
- failure handling
- batching
- retries
- production configuration documentation

Definition of done:

Monitoring operates independently of the Render API.

---

# PHASE 6 — DISCOVERY AND HARDENING

Only after the core system is reliable, add:

- ATS company discovery
- provider validation utilities
- additional monitoring diagnostics
- improved monitoring prioritization
- additional ATS providers where justified
- performance improvements based on actual bottlenecks

Do not begin this phase by rewriting working core architecture.

---

# 66. COMPANY DISCOVERY

Treat discovery separately from monitoring.

Monitoring known ATS companies is the MVP.

Company discovery should eventually identify potential:

```
Greenhouse
Lever
Ashby

```

career pages and determine the required provider identifier.

Validate discovered sources before activating them.

Never insert arbitrary unverified sources directly into high-frequency monitoring.

---

# 67. API AND DOMAIN SEPARATION

Business logic must not depend directly on FastAPI route handlers.

For example:

Bad:

```
API route
→ directly fetch ATS
→ directly manipulate five database tables
→ directly send Telegram

```

Preferred:

```
API route
→ service
→ repository/domain/database operations

```

Workers should reuse the same services where appropriate.

---

# 68. CODE QUALITY RULES

Follow these principles:

- meaningful names
- small cohesive modules
- strong typing
- explicit interfaces
- dependency injection where useful
- clear exceptions
- minimal duplication
- simple abstractions
- composition over giant service classes
- comments explaining why, not obvious syntax

Do not generate layers solely to satisfy an abstract interpretation of "clean architecture."

Practical maintainability is the objective.

---

# 69. PYTHON QUALITY

Use:

- type hints
- Pydantic schemas
- async I/O where appropriate
- context-managed database sessions
- explicit service boundaries
- pytest
- modern linting/formatting

Avoid:

- global mutable state
- wildcard imports
- silent exception swallowing
- huge `utils.py` files
- untyped dictionaries where structured models are appropriate

---

# 70. TYPESCRIPT QUALITY

Use:

- strict TypeScript
- typed API responses
- reusable components
- sensible server/client component boundaries

Avoid:

- unnecessary `any`
- duplicated interfaces
- large monolithic pages
- storing server state unnecessarily in global client state

---

# 71. PERFORMANCE PRINCIPLES

The initial system is small.

Do not optimize speculative bottlenecks.

However, avoid obviously inefficient behavior such as:

- querying every user separately for every job
- loading entire job history into memory
- uncontrolled concurrent HTTP requests
- repeatedly sending unchanged database writes

Use bounded concurrency for ATS requests.

---

# 72. COST PRINCIPLES

The system must remain compatible with near-zero-cost operation.

Do not introduce:

- Redis hosting
- dedicated worker servers
- Kafka
- message brokers
- paid cron providers
- paid search APIs
- paid AI APIs
- Kubernetes
- separate databases

unless explicitly approved later.

---

# 73. DATA RETENTION

Do not delete closed jobs automatically.

Closed jobs are useful for:

- job history
- duplicate detection
- analytics
- lifecycle debugging

Exclude them from active job listings by default.

---

# 74. ADMINISTRATION

Because the initial system has very few users, it is acceptable to use simple administrator-only functionality for:

- adding companies
- modifying ATS identifiers
- changing monitoring priority
- disabling broken sources

Avoid building a large RBAC system initially.

---

# 75. HEALTH ENDPOINT

Provide a lightweight endpoint such as:

```
GET /health

```

It should report API health without exposing secrets.

A separate readiness check may test database connectivity if useful.

---

# 76. DATABASE TRANSACTIONS

Use transactions for operations where partial completion could create inconsistent state.

Important examples include:

```
job insertion + match creation
state transitions
Telegram linkage
saved/ignored updates
notification status changes

```

Do not wrap slow external HTTP calls inside long database transactions unnecessarily.

---

# 77. NOTIFICATION DELIVERY SEMANTICS

Aim for practical **at-least-once processing with effectively-once user notification behavior**.

Because external calls can fail, exactly-once distributed delivery cannot simply be assumed.

Use persisted notification state and unique constraints so retries remain safe.

If Telegram successfully receives a message but the local process crashes before marking it sent, duplicate risk must be considered and minimized.

Document the chosen tradeoff.

---

# 78. DATABASE AS SOURCE OF TRUTH

Do not store important monitoring state solely in:

- GitHub Actions environment
- local JSON files
- Render memory
- process globals
- temporary filesystem

GitHub Actions workers are disposable.

The database owns persistent state.

---

# 79. DOCUMENTATION

Maintain:

```
README.md
docs/architecture.md
docs/deployment.md
docs/monitoring.md

```

Documentation should explain:

- system architecture
- local setup
- environment variables
- migrations
- running workers
- Telegram setup
- GitHub Actions secrets
- Supabase setup
- Render deployment
- Vercel deployment
- common debugging steps

Do not leave deployment knowledge only in code comments.

---

# 80. ENGINEERING DECISION PROCESS

Before making a major architectural change, provide a concise explanation containing:

### Decision

What you intend to do.

### Reason

Why this solution fits Radar.

### Tradeoffs

What is gained or sacrificed.

### Files affected

Which areas of the repository will change.

Do not provide lengthy essays for routine implementation decisions.

---

# 81. WORKING WITH AN EXISTING REPOSITORY

Before changing code:

1. inspect existing repository structure
2. inspect existing dependency files
3. inspect configuration
4. inspect migrations
5. inspect tests
6. identify existing conventions

Preserve good existing work.

Do not unnecessarily replace working implementations.

Do not rename large parts of the repository without a clear benefit.

---

# 82. WHEN STARTING FROM AN EMPTY REPOSITORY

If the repository is empty:

1. create the monorepo
2. scaffold backend
3. scaffold frontend
4. configure quality tooling
5. create environment example
6. implement Phase 0
7. verify it
8. continue to Phase 1

Do not stop after creating placeholder directories.

---

# 83. IMPLEMENTATION BEHAVIOR

You are expected to implement working software, not merely describe it.

When given permission to work on the repository:

- inspect
- plan
- implement
- run tests
- fix failures
- run lint/type checks
- verify builds
- summarize results

Do not repeatedly ask for confirmation between normal implementation steps.

When a minor requirement is unspecified, make a reasonable engineering decision and document it.

Only treat something as a blocker when proceeding safely is genuinely impossible.

---

# 84. DO NOT GENERATE PLACEHOLDER SYSTEMS

Avoid fake implementations such as:

```
def fetch_jobs():
    # TODO
    pass

```

for features that are supposedly complete.

Mocks are appropriate in tests.

Production paths should be functional for the phase being implemented.

---

# 85. DEFINITION OF DONE FOR EVERY FEATURE

A feature is not complete merely because source files exist.

A feature is complete when applicable criteria are satisfied:

- implementation exists
- types are correct
- migrations exist
- validation exists
- authorization exists
- errors are handled
- important behavior is tested
- tests pass
- linting passes
- frontend typecheck passes
- production build succeeds
- configuration is documented
- no secrets are committed

---

# 86. ACCEPTANCE CRITERIA FOR RADAR MVP

The MVP is complete when the following scenario works:

### Setup

A user:

1. registers
2. logs in
3. connects Telegram
4. creates a job profile
5. configures desired titles
6. configures desired locations/work mode

An administrator/configuration adds monitored ATS companies.

### Monitoring

A GitHub Actions workflow runs without depending on the Render server.

Radar:

1. retrieves jobs from supported ATS sources
2. validates responses
3. normalizes jobs
4. deduplicates them
5. updates lifecycle state
6. stores new jobs
7. evaluates user profiles
8. creates job matches
9. creates notifications
10. sends matching alerts through Telegram
11. records monitoring statistics

### Repeated execution

When the same workflow runs again:

- unchanged jobs are not duplicated
- notifications are not duplicated
- timestamps/state are updated correctly

### Lifecycle

When a job disappears:

```
ACTIVE → UNKNOWN

```

After repeated successful checks confirm absence:

```
UNKNOWN → CLOSED

```

A failed ATS request does not close jobs.

### Dashboard

The user can:

- manage profiles
- view matches
- save jobs
- ignore jobs
- see closed/active status appropriately
- inspect Telegram connection
- see basic monitoring health

---

# 87. ARCHITECTURAL INVARIANTS

The following rules must remain true throughout development.

### Invariant 1

A sleeping Render API cannot stop scheduled monitoring.

### Invariant 2

Running the same worker twice must not create duplicate jobs.

### Invariant 3

Running the same matching pipeline twice must not create duplicate matches.

### Invariant 4

Retrying notification processing must not normally create duplicate alerts.

### Invariant 5

A failed ATS request cannot cause active jobs to be marked closed.

### Invariant 6

Users cannot modify another user's resources.

### Invariant 7

Closed jobs do not appear in active results by default.

### Invariant 8

Workers contain no required persistent local state.

### Invariant 9

Secrets never appear in committed source code.

### Invariant 10

Every ATS provider maps into the same downstream normalized job pipeline.

---

# 88. OUT OF SCOPE FOR MVP

Do not implement unless explicitly requested:

- resumes
- resume parsing
- AI recommendations
- cover-letter generation
- applicant tracking
- application submission automation
- LinkedIn scraping
- Indeed scraping
- browser automation for job boards
- user-to-user messaging
- recruiter messaging
- social feeds
- paid subscriptions
- Stripe
- mobile application
- Elasticsearch
- vector databases
- embeddings
- LLM integrations
- native push notifications
- complex analytics
- enterprise permissions
- Kubernetes
- Redis
- Kafka

---

# 89. FUTURE EXTENSIBILITY

Design clean interfaces so future versions may support:

- additional ATS providers
- email notifications
- Discord notifications
- more sophisticated matching
- job ranking
- salary filtering
- company watchlists
- analytics
- automatic ATS discovery
- user-defined monitoring priority
- paid plans

Do not build these features now.

Only avoid architectural decisions that would make them unnecessarily difficult later.

---

# 90. FINAL ENGINEERING OBJECTIVE

Build Radar as a **small, dependable job-monitoring system**, not as an overengineered startup platform.

The most important successful behavior is:

```
A company publishes a relevant job
        ↓
Radar discovers it quickly
        ↓
Radar identifies it as genuinely new
        ↓
Radar matches it correctly
        ↓
The correct user receives exactly one useful Telegram alert
        ↓
The event remains visible and manageable from the dashboard

```

Everything else is secondary.

---

# 91. FIRST ACTION

Begin by inspecting the repository.

Then produce a concise implementation assessment containing:

1. current repository state
2. existing architecture
3. missing components
4. architectural issues, if any
5. implementation phases
6. immediate files/components to create or modify

After the assessment, **begin implementation**.

Do not stop after producing the plan unless implementation is genuinely blocked.

Start with the earliest incomplete phase.

After completing each meaningful milestone:

1. run relevant tests
2. run lint/type checks
3. fix failures
4. verify the feature
5. summarize what changed
6. continue to the next logical milestone

Always preserve the architectural invariants defined in this specification.

The final result should be a clean, tested, documented, deployable implementation of **Radar** using:

```
Next.js + Vercel
FastAPI + Render Free
PostgreSQL + Supabase
Python Workers + GitHub Actions
Telegram Bot API

```

with **freshness, correctness, idempotency, and reliability** as the defining engineering characteristics.