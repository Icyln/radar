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
      setError(err instanceof Error ? err.message : "Could not update job");
    } finally {
      setBusy(null);
    }
  }

  return (
    <article className="panel p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={statusTone(job.status)}>{humanize(job.status)}</Badge>
            <Badge>{humanize(job.work_mode)}</Badge>
            <Badge tone={job.source_kind === "WIDE_DISCOVERY" ? "info" : "neutral"}>
              {job.source_kind === "WIDE_DISCOVERY" ? `Wide discovery${job.source_provider ? ` · ${humanize(job.source_provider)}` : ""}` : "Direct ATS"}
            </Badge>
            {state ? <Badge tone={state === "SAVED" ? "info" : "neutral"}>{humanize(state)}</Badge> : null}
          </div>
          <h2 className="mt-3 text-base font-semibold leading-6 text-zinc-50 sm:text-lg">{job.title}</h2>
          <p className="mt-1 text-sm text-zinc-400">{job.company_name}</p>
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-500">
            <span>{job.location || "Location not specified"}</span>
            {job.employment_type ? <span>{humanize(job.employment_type)}</span> : null}
            <span>Detected {relativeTime(job.first_seen_at)}</span>
            {job.freshness_source === "POSTED_AT" && job.freshness_at ? <span>Posted {relativeTime(job.freshness_at)}</span> : null}
            {job.freshness_source === "DISCOVERY_SIGNAL" && job.freshness_at ? <span>Fresh hiring signal {relativeTime(job.freshness_at)}</span> : null}
            {job.freshness_source === "FIRST_SEEN" && job.freshness_at ? <span>Freshness from detection {relativeTime(job.freshness_at)}</span> : null}
            {job.freshness_source === "UNKNOWN" ? <span>Posting date unavailable</span> : null}
          </div>
        </div>
        <a href={job.apply_url} target="_blank" rel="noreferrer" className="button-primary shrink-0">Open job ↗</a>
      </div>

      {!compact ? (
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-zinc-800/80 pt-4">
          <button className={state === "SAVED" ? "button-secondary border-sky-800 text-sky-300" : "button-secondary"} disabled={busy !== null} onClick={() => update(state === "SAVED" ? null : "SAVED")}>{busy === "SAVED" ? "Saving…" : state === "SAVED" ? "Unsave" : "Save"}</button>
          <button className={state === "IGNORED" ? "button-secondary border-zinc-600 text-zinc-200" : "button-secondary"} disabled={busy !== null} onClick={() => update(state === "IGNORED" ? null : "IGNORED")}>{busy === "IGNORED" ? "Ignoring…" : state === "IGNORED" ? "Unignore" : "Ignore"}</button>
          {error ? <span className="text-xs text-rose-400">{error}</span> : null}
        </div>
      ) : null}
    </article>
  );
}
