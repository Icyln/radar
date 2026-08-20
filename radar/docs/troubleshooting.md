# Troubleshooting

## Render backend will not start after upgrading

Check environment validation first. In production Radar requires:

- a non-default JWT secret of at least 32 characters
- `TELEGRAM_WEBHOOK_SECRET` if `TELEGRAM_BOT_TOKEN` is configured and webhook-secret enforcement is enabled

Also confirm the Supabase connection string is reachable from Render.

## Frontend says the API is unavailable

Confirm `RADAR_API_URL` on the Next.js host points to the Render service using HTTPS. The BFF returns a 502 when it cannot reach the backend and a 504 when the configured upstream timeout expires.

Use the `X-Request-ID` response header to correlate the request with backend logs.

## Login or manual actions return 429

Radar rate-limits high-abuse endpoints. Wait for the indicated window before retrying repeatedly. If normal 50–100 user traffic regularly hits limits, investigate the request pattern before simply raising the limits.

## Telegram is connected but no job notifications arrive

1. Use **Settings → Send test**.
2. Confirm the active Job Alert matches the job.
3. Confirm the job was not hidden.
4. Check **Admin → System status** for recent worker runs.
5. Check GitHub Actions logs for notification/provider failures.
6. Confirm `TELEGRAM_BOT_TOKEN` is present in the scheduled worker secrets.

## Company monitoring is stale

Check `.github/workflows/scheduled_monitor.yml` runs and the Admin system page. A failed individual company does not necessarily mean the whole workflow failed.

Repeated failures for one source usually indicate an ATS identifier/source change, provider outage, or upstream behavior change.

## A requested company never appears

Check the request in **Companies**. Administrators can inspect **Admin → Source discovery** for scan errors and source validation status.

A completed scan with zero sources is valid: Radar may not support the company's career platform or the submitted page may not expose a supported direct source.

## Broad-search results seem delayed for one title

Broad search has a global per-run query budget. Terms are deduplicated and rotated fairly when demand exceeds that budget. Direct monitored-company jobs are independent of this rotation and continue to be checked by Scheduled Monitoring.
