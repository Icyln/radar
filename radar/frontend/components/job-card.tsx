"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Badge } from "@/components/badge";
import { clientRequest } from "@/lib/client-api";
import { humanize, relativeTime } from "@/lib/format";
import type { JobListItem, UserJobState } from "@/types/api";

function statusTone(status: JobListItem["status"]) {
  if (status === "ACTIVE") return "success" as const;
  if (status === "CLOSED") return "danger" as const;
  return "warning" as const;
}

function statusLabel(status: JobListItem["status"]) {
  if (status === "ACTIVE") return "Open";
  if (status === "CLOSED") return "Closed";
  return "Unclear";
}

function sourceLabel(job: JobListItem) {
  return job.source_verified ? "Verified company source" : "Found by Radar";
}

export function JobCard({ job, compact = false }: { job: JobListItem; compact?: boolean }) {
  const router = useRouter();
  const [state, setState] = useState<UserJobState>(job.user_state);
  const [busy, setBusy] = useState<UserJobState | "CLEAR" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function update(next: UserJobState) {
    setBusy(next ?? "CLEAR");
    setError(null);
    try {
      const updated = await clientRequest<JobListItem>(`jobs/${job.id}/state`, {
        method: "PUT",
        body: JSON.stringify({ state: next })
      });
      setState(updated.user_state);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update this job");
    } finally {
      setBusy(null);
    }
  }

  return (
    <article className="panel p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={statusTone(job.status)}>{statusLabel(job.status)}</Badge>
            {job.work_mode !== "UNKNOWN" ? <Badge>{humanize(job.work_mode)}</Badge> : null}
            <Badge tone={job.source_verified ? "neutral" : "info"}>{sourceLabel(job)}</Badge>
            {state === "SAVED" ? <Badge tone="info">Saved</Badge> : null}
            {state === "IGNORED" ? <Badge>Hidden</Badge> : null}
          </div>
          <h2 className="mt-3 text-base font-semibold leading-6 text-main sm:text-lg">{job.title}</h2>
          <p className="mt-1 text-sm text-soft">{job.company_name}</p>
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-faint">
            <span>{job.location || "Location not listed"}</span>
            {job.employment_type ? <span>{humanize(job.employment_type)}</span> : null}
            {job.freshness_at ? <span>{job.freshness_source === "POSTED_AT" ? "Posted" : "Found"} {relativeTime(job.freshness_at)}</span> : <span>Posting date not available</span>}
          </div>
        </div>
        <a href={job.apply_url} target="_blank" rel="noreferrer" className="button-primary shrink-0">Open job</a>
      </div>

      {!compact ? (
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-ui pt-4">
          <button className="button-secondary" disabled={busy !== null} onClick={() => update(state === "SAVED" ? null : "SAVED")}>{busy === "SAVED" ? "Saving…" : state === "SAVED" ? "Remove from saved" : "Save"}</button>
          <button className="button-ghost" disabled={busy !== null} onClick={() => update(state === "IGNORED" ? null : "IGNORED")}>{busy === "IGNORED" ? "Hiding…" : state === "IGNORED" ? "Show again" : "Hide"}</button>
          {error ? <span className="text-xs text-danger">{error}</span> : null}
        </div>
      ) : null}
    </article>
  );
}
