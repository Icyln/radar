# Phase 7D — Wide Search Telegram delivery

Phase 7D completes the user-facing alert loop for Phase 7C.

## What changes

A fresh Wide Search job is no longer only visible in the dashboard:

```text
Fresh hiring signal
→ WIDE job stored
→ profile match created
→ per-user Telegram notification queued
→ immediate delivery when triggered from Refresh Wide Search
→ scheduled discovery can also deliver in the same worker run
```

Direct ATS monitoring continues to use the same outbox and delivery worker.

## User-side test

1. Open **Settings**.
2. Connect Telegram if it is not already connected.
3. Click **Send test alert**.
4. Confirm a Radar preview arrives in Telegram. If you already have matched jobs, the preview uses your latest match and shows whether its source is **Wide discovery** or **Direct ATS**.
5. Open **Jobs**.
6. Click **Refresh Wide Search**.
7. If fresh new matching jobs are found, the result panel shows **Telegram: N sent**.
8. Confirm those job alerts arrive in Telegram.
9. Click **Refresh Wide Search** again. Already-known jobs should move into Existing jobs and should not be alerted again.
10. Open **Settings** again and use **Refresh** under Job alert delivery today to verify Sent / Pending / Failed counts.

## Scheduled delivery

The Source Discovery GitHub Actions workflow now receives `TELEGRAM_BOT_TOKEN`. When a scheduled discovery run creates fresh WIDE matches, it attempts to deliver those new notification IDs immediately. Scheduled Monitoring still flushes any remaining pending/failed alerts as a fallback.

## Duplicate safety

Notification uniqueness already protects the same user/job from repeated alerts. Phase 7C also upgrades an unambiguous WIDE job to Direct ATS in place, preserving the Radar job ID and existing match. Therefore a successful source-quality upgrade does not intentionally create a second alert for the same Radar job.

## Database

No new migration is required for Phase 7D. The migration head remains:

```text
0009_phase7c
```
