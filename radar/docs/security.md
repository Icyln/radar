# Security

## Authentication and browser session

FastAPI issues short-lived JWT access tokens. The Next.js BFF stores the token in an HttpOnly, Secure-in-production, SameSite=Lax cookie so normal browser JavaScript cannot read it.

State-changing BFF requests are restricted to same-origin browser contexts. This supplements SameSite cookies as CSRF protection.

## Abuse controls

The backend applies in-process sliding-window limits to high-abuse endpoints such as login, registration, manual broad-search refresh, discovery requests, and Telegram test messages.

These limits are intentionally simple for a single Render web instance and a 50–100 user target. If the API is later scaled to multiple independent Render instances, move rate-limit counters to a shared store or edge/WAF layer.

## Request and response hardening

- Backend and BFF request-body limits reduce accidental/hostile oversized payloads.
- API responses are `no-store` where appropriate.
- Request IDs are generated/propagated for incident correlation.
- Next.js sends CSP, anti-framing, MIME-sniffing, referrer, permissions, and HSTS headers in production.
- FastAPI production docs are disabled.

## Telegram webhook

Production configuration requires `TELEGRAM_WEBHOOK_SECRET` whenever Telegram is enabled. The webhook checks Telegram's secret-token header before processing updates.

Bot tokens and webhook secrets must exist only in server/worker secret stores.

## Source-discovery SSRF controls

User-supplied career URLs are treated as untrusted input. Discovery:

- allows only public HTTP/HTTPS destinations
- resolves and rejects non-global/private addresses before requests
- revalidates redirects
- checks the connected peer IP when the HTTP transport exposes it
- caps total pages and request time
- caps HTML response size

These controls make the discovery crawler inappropriate for arbitrary generic web crawling by design.

## Database safety

Ownership filters are applied to user resources. Unique constraints and transactions enforce notification/job identities. Worker concurrency remains bounded to reduce connection pressure and provider load.

## Secrets

Never commit `.env`, `.env.local`, Supabase credentials, Telegram bot tokens, JWT secrets, or webhook secrets. Rotate a credential immediately if it is exposed.
