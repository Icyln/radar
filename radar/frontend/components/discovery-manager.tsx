"use client";

import { FormEvent, useState } from "react";
import { Badge } from "@/components/badge";
import { clientRequest } from "@/lib/client-api";
import { formatDateTime, humanize } from "@/lib/format";
import type { DiscoverySummary, DiscoveryTarget, SourceCandidate } from "@/types/api";

function targetTone(status: DiscoveryTarget["status"]): "success" | "warning" | "neutral" {
  if (status === "COMPLETE") return "success";
  if (status === "FAILED") return "warning";
  return "neutral";
}

function candidateTone(status: SourceCandidate["status"]): "success" | "warning" | "neutral" {
  if (status === "VALID") return "success";
  if (status === "INVALID") return "warning";
  return "neutral";
}

function SummaryMetric({ label, value }: { label: string; value: number }) {
  return <div className="panel-soft p-4"><p className="text-xs text-faint">{label}</p><p className="mt-1 text-2xl font-semibold text-main">{value}</p></div>;
}

export function DiscoveryManager({
  initialTargets,
  initialCandidates,
  initialSummary,
  isAdmin
}: {
  initialTargets: DiscoveryTarget[];
  initialCandidates: SourceCandidate[];
  initialSummary: DiscoverySummary | null;
  isAdmin: boolean;
}) {
  const [targets, setTargets] = useState(initialTargets);
  const [candidates, setCandidates] = useState(initialCandidates);
  const [url, setUrl] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [autoWatch, setAutoWatch] = useState(true);
  const [busy, setBusy] = useState(false);
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await clientRequest<DiscoveryTarget>("discovery/targets", {
        method: "POST",
        body: JSON.stringify({ url, company_name_hint: companyName.trim() || null, auto_watch: autoWatch })
      });
      setTargets((current) => [created, ...current.filter((item) => item.id !== created.id)]);
      setUrl("");
      setCompanyName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not queue source discovery.");
    } finally {
      setBusy(false);
    }
  }

  async function retryTarget(target: DiscoveryTarget) {
    setActionBusy(target.id);
    setError(null);
    try {
      const updated = await clientRequest<DiscoveryTarget>(`discovery/targets/${target.id}/retry`, { method: "POST" });
      setTargets((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not retry discovery target.");
    } finally {
      setActionBusy(null);
    }
  }

  async function retryCandidate(candidate: SourceCandidate) {
    setActionBusy(candidate.id);
    setError(null);
    try {
      const updated = await clientRequest<SourceCandidate>(`discovery/candidates/${candidate.id}/retry`, { method: "POST" });
      setCandidates((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not retry source validation.");
    } finally {
      setActionBusy(null);
    }
  }

  async function promoteCandidate(candidate: SourceCandidate) {
    setActionBusy(candidate.id);
    setError(null);
    try {
      const updated = await clientRequest<SourceCandidate>(`discovery/candidates/${candidate.id}/promote`, { method: "POST" });
      setCandidates((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not promote validated source.");
    } finally {
      setActionBusy(null);
    }
  }

  if (!isAdmin) return null;

  return <div className="space-y-6">
    {initialSummary ? <section className="panel p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><h2 className="font-semibold text-main">Automated discovery health</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-soft">Radar uses active job-alert demand and bounded public hiring signals to find candidate company career sources. Candidate sources are validated before they are promoted into the monitored registry.</p></div>
        <Badge tone="success">Automation enabled</Badge>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <SummaryMetric label="Hiring-signal targets" value={initialSummary.hiring_signal_targets} />
        <SummaryMetric label="Signal-promoted sources" value={initialSummary.hiring_signal_promoted_sources} />
        <SummaryMetric label="Fresh signal jobs" value={initialSummary.fresh_signal_jobs} />
        <SummaryMetric label="All system targets" value={initialSummary.system_targets} />
        <SummaryMetric label="System-promoted sources" value={initialSummary.system_promoted_candidates} />
        <SummaryMetric label="Revalidation warnings" value={initialSummary.revalidation_failures} />
      </div>
    </section> : null}

    <section className="panel p-5 sm:p-6">
      <h2 className="font-semibold text-main">Queue a company source</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-soft">Administratively submit a public careers URL for bounded scanning and supported ATS validation. Normal users can submit the same kind of request from the Companies page without seeing these technical details.</p>
      <form onSubmit={submit} className="mt-5 grid gap-4 md:grid-cols-2">
        <label className="field-label md:col-span-2">Careers URL<input className="input mt-2" type="url" required placeholder="https://company.example/careers" value={url} onChange={(event) => setUrl(event.target.value)} /></label>
        <label className="field-label">Company name <span className="font-normal text-faint">(optional)</span><input className="input mt-2" placeholder="Example Company" value={companyName} onChange={(event) => setCompanyName(event.target.value)} /></label>
        <label className="flex items-center gap-3 self-end rounded-xl border border-ui surface-soft px-4 py-3 text-sm text-soft"><input type="checkbox" checked={autoWatch} onChange={(event) => setAutoWatch(event.target.checked)} /><span>Follow it for this account after successful validation</span></label>
        <div className="md:col-span-2"><button className="button-primary" disabled={busy}>{busy ? "Queuing…" : "Queue source"}</button></div>
      </form>
      {error ? <p className="status-danger mt-4 rounded-lg px-3 py-2 text-sm">{error}</p> : null}
    </section>

    <section>
      <div className="mb-3"><h2 className="font-semibold text-main">Discovery targets</h2><p className="mt-1 text-xs text-soft">Public pages queued for bounded scanning. A completed scan may legitimately find zero supported sources.</p></div>
      <div className="overflow-hidden rounded-xl border border-ui surface">
        <div className="overflow-x-auto"><table className="min-w-full text-left text-sm">
          <thead className="border-b border-ui surface-soft text-xs text-faint"><tr><th className="px-4 py-3 font-medium">Target</th><th className="px-4 py-3 font-medium">Status</th><th className="px-4 py-3 font-medium">Scan</th><th className="px-4 py-3 font-medium">Sources</th><th className="px-4 py-3 font-medium">Last scan</th><th className="px-4 py-3"></th></tr></thead>
          <tbody className="divide-y divide-[var(--border)]">{targets.length === 0 ? <tr><td className="px-4 py-10 text-center text-faint" colSpan={6}>No discovery targets yet.</td></tr> : targets.map((target) => <tr key={target.id}>
            <td className="max-w-md px-4 py-4"><div className="flex items-center gap-2"><p className="font-medium text-main">{target.company_name_hint || "Company source"}</p>{target.origin === "SYSTEM_FEED" ? <Badge tone="neutral">System</Badge> : null}</div>{target.source_label ? <p className="mt-1 text-[11px] text-faint">{target.source_label}</p> : null}{target.job_title_hint ? <p className="mt-1 text-xs text-info">Hiring signal: {target.job_title_hint}</p> : null}<a className="mt-1 block truncate text-xs text-faint hover:text-accent" href={target.url} target="_blank" rel="noreferrer">{target.url}</a>{target.error_message ? <p className="mt-2 text-xs text-danger">{target.error_message}</p> : null}</td>
            <td className="px-4 py-4"><Badge tone={targetTone(target.status)}>{humanize(target.status)}</Badge></td>
            <td className="px-4 py-4 text-xs text-soft">{target.pages_scanned} pages · {target.scan_attempt_count} attempts</td>
            <td className="px-4 py-4 text-main">{target.sources_found}</td>
            <td className="whitespace-nowrap px-4 py-4 text-xs text-soft">{formatDateTime(target.last_scanned_at)}</td>
            <td className="px-4 py-4 text-right">{target.status === "FAILED" ? <button className="button-ghost" disabled={actionBusy === target.id} onClick={() => retryTarget(target)}>{actionBusy === target.id ? "Queuing…" : "Retry"}</button> : null}</td>
          </tr>)}</tbody>
        </table></div>
      </div>
    </section>

    <section className="space-y-3">
      <div><h2 className="font-semibold text-main">Source validation</h2>{initialSummary ? <p className="mt-1 text-xs text-soft">Pending targets {initialSummary.pending_targets} · Candidates {initialSummary.discovered_candidates} · Valid {initialSummary.valid_candidates} · Invalid {initialSummary.invalid_candidates} · Promoted {initialSummary.promoted_candidates}</p> : null}</div>
      <div className="overflow-hidden rounded-xl border border-ui surface"><div className="overflow-x-auto"><table className="min-w-full text-left text-sm">
        <thead className="border-b border-ui surface-soft text-xs text-faint"><tr><th className="px-4 py-3 font-medium">Source</th><th className="px-4 py-3 font-medium">Provider</th><th className="px-4 py-3 font-medium">Status</th><th className="px-4 py-3 font-medium">Jobs seen</th><th className="px-4 py-3 font-medium">Validation</th><th className="px-4 py-3"></th></tr></thead>
        <tbody className="divide-y divide-[var(--border)]">{candidates.length === 0 ? <tr><td className="px-4 py-10 text-center text-faint" colSpan={6}>No source candidates discovered yet.</td></tr> : candidates.map((candidate) => <tr key={candidate.id}>
          <td className="px-4 py-4"><p className="font-medium text-main">{candidate.name_hint || candidate.ats_identifier}</p><a className="mt-1 block max-w-sm truncate text-xs text-faint hover:text-accent" href={candidate.career_url} target="_blank" rel="noreferrer">{candidate.ats_identifier}</a>{candidate.error_message ? <p className="mt-2 text-xs text-danger">{candidate.error_message}</p> : null}</td>
          <td className="px-4 py-4 text-main">{humanize(candidate.ats_provider)}</td>
          <td className="px-4 py-4"><Badge tone={candidateTone(candidate.status)}>{candidate.promoted_company_id ? "Promoted" : humanize(candidate.status)}</Badge></td>
          <td className="px-4 py-4 text-main">{candidate.jobs_seen ?? "—"}</td>
          <td className="px-4 py-4 text-xs text-soft">{candidate.validation_attempt_count} attempts<br />{formatDateTime(candidate.last_validated_at)}{candidate.last_revalidated_at ? <><br />Rechecked {formatDateTime(candidate.last_revalidated_at)}</> : null}{candidate.revalidation_failure_count > 0 ? <><br /><span className="text-warning">{candidate.revalidation_failure_count} revalidation failures</span></> : null}</td>
          <td className="px-4 py-4 text-right"><div className="flex justify-end gap-2">{candidate.status === "INVALID" ? <button className="button-ghost" disabled={actionBusy === candidate.id} onClick={() => retryCandidate(candidate)}>Retry</button> : null}{candidate.status === "VALID" && !candidate.promoted_company_id ? <button className="button-secondary" disabled={actionBusy === candidate.id} onClick={() => promoteCandidate(candidate)}>Promote</button> : null}</div></td>
        </tr>)}</tbody>
      </table></div></div>
    </section>
  </div>;
}
