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
        body: JSON.stringify({
          url,
          company_name_hint: companyName.trim() || null,
          auto_watch: autoWatch
        })
      });
      setTargets((current) => [created, ...current.filter((item) => item.id !== created.id)]);
      setUrl("");
      setCompanyName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not queue discovery request");
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
      setError(err instanceof Error ? err.message : "Could not retry discovery target");
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
      setError(err instanceof Error ? err.message : "Could not retry source validation");
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
      setError(err instanceof Error ? err.message : "Could not promote validated source");
    } finally {
      setActionBusy(null);
    }
  }

  return <div className="space-y-6">
    {!isAdmin ? <section className="panel p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><h2 className="font-semibold text-zinc-100">Automatic Wide Search coverage</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-500">Radar grows the shared company registry through system-managed discovery. You do not need to upload company lists or know ATS identifiers. Use the request form below only for a specific company you want Radar to check.</p></div>
        <Badge tone="success">Automatic</Badge>
      </div>
    </section> : null}

    {isAdmin && initialSummary ? <section className="panel p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><h2 className="font-semibold text-zinc-100">Automatic registry growth</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-500">Phase 7 uses enabled Wide profiles as discovery demand: Radar checks fresh public hiring signals for those job titles, validates supported ATS sources, and grows the shared registry automatically. Bundled/system feeds remain supplemental infrastructure.</p></div>
        <Badge tone="success">System discovery active</Badge>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-lg border border-zinc-800 p-4"><p className="text-xs text-zinc-500">Fresh hiring targets</p><p className="mt-1 text-2xl font-semibold text-zinc-100">{initialSummary.hiring_signal_targets}</p></div>
        <div className="rounded-lg border border-zinc-800 p-4"><p className="text-xs text-zinc-500">Signal-promoted sources</p><p className="mt-1 text-2xl font-semibold text-zinc-100">{initialSummary.hiring_signal_promoted_sources}</p></div>
        <div className="rounded-lg border border-zinc-800 p-4"><p className="text-xs text-zinc-500">Fresh baseline roles identified</p><p className="mt-1 text-2xl font-semibold text-zinc-100">{initialSummary.fresh_signal_jobs}</p></div>
        <div className="rounded-lg border border-zinc-800 p-4"><p className="text-xs text-zinc-500">All system targets</p><p className="mt-1 text-2xl font-semibold text-zinc-100">{initialSummary.system_targets}</p></div>
        <div className="rounded-lg border border-zinc-800 p-4"><p className="text-xs text-zinc-500">System-promoted sources</p><p className="mt-1 text-2xl font-semibold text-zinc-100">{initialSummary.system_promoted_candidates}</p></div>
        <div className="rounded-lg border border-zinc-800 p-4"><p className="text-xs text-zinc-500">Revalidation warnings</p><p className="mt-1 text-2xl font-semibold text-zinc-100">{initialSummary.revalidation_failures}</p></div>
      </div>
    </section> : null}

    <section className="panel p-5 sm:p-6">
      <h2 className="font-semibold text-zinc-100">Request a company source</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-500">Wide Search automatically expands Radar’s registry from fresh hiring signals for your profile titles. This form is optional: use it only when you want to suggest a specific company Radar may not know yet. Requests are queued for bounded public-page scanning and ATS validation.</p>
      <form onSubmit={submit} className="mt-5 grid gap-4 md:grid-cols-2">
        <label className="field-label md:col-span-2">Company or careers URL<input className="input mt-2" type="url" required placeholder="https://company.example/careers" value={url} onChange={(event) => setUrl(event.target.value)} /></label>
        <label className="field-label">Company name <span className="text-zinc-600">(optional)</span><input className="input mt-2" placeholder="Example Company" value={companyName} onChange={(event) => setCompanyName(event.target.value)} /></label>
        <label className="flex items-center gap-3 self-end rounded-lg border border-zinc-800 px-4 py-3 text-sm text-zinc-300"><input type="checkbox" className="accent-emerald-400" checked={autoWatch} onChange={(event) => setAutoWatch(event.target.checked)} /><span>Automatically add the source to my watchlist after successful validation</span></label>
        <div className="md:col-span-2"><button className="button-primary" disabled={busy}>{busy ? "Queuing…" : "Queue discovery"}</button></div>
      </form>
      {error ? <p className="mt-4 text-sm text-rose-400">{error}</p> : null}
    </section>

    <section>
      <div className="mb-3 flex items-end justify-between gap-4"><div><h2 className="font-semibold text-zinc-100">{isAdmin ? "Discovery requests" : "My discovery requests"}</h2><p className="mt-1 text-xs text-zinc-500">A completed request may find zero supported ATS sources; that means the bounded scan did not find Greenhouse, Lever, or Ashby on the submitted pages.</p></div></div>
      <div className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950/50">
        <div className="overflow-x-auto"><table className="min-w-full text-left text-sm">
          <thead className="border-b border-zinc-800 bg-zinc-900/50 text-xs text-zinc-500"><tr><th className="px-4 py-3 font-medium">Target</th><th className="px-4 py-3 font-medium">Status</th><th className="px-4 py-3 font-medium">Scan</th><th className="px-4 py-3 font-medium">Sources</th><th className="px-4 py-3 font-medium">Last scan</th><th className="px-4 py-3"></th></tr></thead>
          <tbody className="divide-y divide-zinc-800/70">{targets.length === 0 ? <tr><td className="px-4 py-10 text-center text-zinc-600" colSpan={6}>No discovery requests yet.</td></tr> : targets.map((target) => <tr key={target.id}>
            <td className="max-w-md px-4 py-4"><div className="flex items-center gap-2"><p className="font-medium text-zinc-200">{target.company_name_hint || "Company source"}</p>{target.origin === "SYSTEM_FEED" ? <Badge tone="neutral">System</Badge> : null}</div>{target.source_label ? <p className="mt-1 text-[11px] text-zinc-600">{target.source_label}</p> : null}{target.job_title_hint ? <p className="mt-1 text-xs text-emerald-400/80">Hiring signal: {target.job_title_hint}</p> : null}<a className="mt-1 block truncate text-xs text-zinc-600 hover:text-emerald-300" href={target.url} target="_blank" rel="noreferrer">{target.url}</a>{target.error_message ? <p className="mt-2 text-xs text-rose-400">{target.error_message}</p> : null}</td>
            <td className="px-4 py-4"><Badge tone={targetTone(target.status)}>{humanize(target.status)}</Badge></td>
            <td className="px-4 py-4 text-xs text-zinc-500">{target.pages_scanned} pages · {target.scan_attempt_count} attempts</td>
            <td className="px-4 py-4 text-zinc-300">{target.sources_found}</td>
            <td className="px-4 py-4 whitespace-nowrap text-xs text-zinc-500">{formatDateTime(target.last_scanned_at)}</td>
            <td className="px-4 py-4 text-right">{target.status === "FAILED" ? <button className="button-ghost" disabled={actionBusy === target.id} onClick={() => retryTarget(target)}>{actionBusy === target.id ? "Queuing…" : "Retry"}</button> : null}</td>
          </tr>)}</tbody>
        </table></div>
      </div>
    </section>

    {isAdmin ? <section className="space-y-3">
      <div><h2 className="font-semibold text-zinc-100">Validation queue</h2>{initialSummary ? <p className="mt-1 text-xs text-zinc-500">Pending targets {initialSummary.pending_targets} · Discovered candidates {initialSummary.discovered_candidates} · Valid {initialSummary.valid_candidates} · Invalid {initialSummary.invalid_candidates} · Promoted {initialSummary.promoted_candidates} · Revalidation warnings {initialSummary.revalidation_failures}</p> : null}</div>
      <div className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950/50"><div className="overflow-x-auto"><table className="min-w-full text-left text-sm">
        <thead className="border-b border-zinc-800 bg-zinc-900/50 text-xs text-zinc-500"><tr><th className="px-4 py-3 font-medium">Source</th><th className="px-4 py-3 font-medium">Provider</th><th className="px-4 py-3 font-medium">Status</th><th className="px-4 py-3 font-medium">Jobs seen</th><th className="px-4 py-3 font-medium">Validation</th><th className="px-4 py-3"></th></tr></thead>
        <tbody className="divide-y divide-zinc-800/70">{candidates.length === 0 ? <tr><td className="px-4 py-10 text-center text-zinc-600" colSpan={6}>No ATS candidates discovered yet.</td></tr> : candidates.map((candidate) => <tr key={candidate.id}>
          <td className="px-4 py-4"><p className="font-medium text-zinc-200">{candidate.name_hint || candidate.ats_identifier}</p><a className="mt-1 block max-w-sm truncate text-xs text-zinc-600 hover:text-emerald-300" href={candidate.career_url} target="_blank" rel="noreferrer">{candidate.ats_identifier}</a></td>
          <td className="px-4 py-4 text-zinc-300">{humanize(candidate.ats_provider)}</td>
          <td className="px-4 py-4"><Badge tone={candidateTone(candidate.status)}>{candidate.promoted_company_id ? "Promoted" : humanize(candidate.status)}</Badge></td>
          <td className="px-4 py-4 text-zinc-300">{candidate.jobs_seen ?? "—"}</td>
          <td className="px-4 py-4 text-xs text-zinc-500">{candidate.validation_attempt_count} attempts<br />{formatDateTime(candidate.last_validated_at)}{candidate.last_revalidated_at ? <><br />Rechecked {formatDateTime(candidate.last_revalidated_at)}</> : null}{candidate.revalidation_failure_count > 0 ? <><br /><span className="text-amber-400">{candidate.revalidation_failure_count} revalidation failures</span></> : null}</td>
          <td className="px-4 py-4 text-right"><div className="flex justify-end gap-2">{candidate.status === "INVALID" ? <button className="button-ghost" disabled={actionBusy === candidate.id} onClick={() => retryCandidate(candidate)}>Retry</button> : null}{candidate.status === "VALID" && !candidate.promoted_company_id ? <button className="button-secondary" disabled={actionBusy === candidate.id} onClick={() => promoteCandidate(candidate)}>Promote</button> : null}</div></td>
        </tr>)}</tbody>
      </table></div></div>
    </section> : null}
  </div>;
}
