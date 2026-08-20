"use client";

import { FormEvent, useState } from "react";
import { Badge } from "@/components/badge";
import { clientRequest } from "@/lib/client-api";
import { formatDateTime } from "@/lib/format";
import type { DiscoveryTarget } from "@/types/api";

function label(status: DiscoveryTarget["status"]) {
  if (status === "PENDING") return "Queued";
  if (status === "SCANNING") return "Checking";
  if (status === "COMPLETE") return "Checked";
  return "Needs retry";
}
function tone(status: DiscoveryTarget["status"]): "success" | "warning" | "neutral" {
  if (status === "COMPLETE") return "success";
  if (status === "FAILED") return "warning";
  return "neutral";
}

export function CompanyRequest({ initialTargets }: { initialTargets: DiscoveryTarget[] }) {
  const [targets, setTargets] = useState(initialTargets);
  const [url, setUrl] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [autoWatch, setAutoWatch] = useState(true);
  const [busy, setBusy] = useState(false);
  const [retryBusy, setRetryBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      const created = await clientRequest<DiscoveryTarget>("discovery/targets", { method: "POST", body: JSON.stringify({ url, company_name_hint: companyName.trim() || null, auto_watch: autoWatch }) });
      setTargets((current) => [created, ...current.filter((item) => item.id !== created.id)]);
      setUrl("");
      setCompanyName("");
      setMessage("Request added. Radar will check the public careers page in the background.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not request this company");
    } finally {
      setBusy(false);
    }
  }

  async function retry(target: DiscoveryTarget) {
    setRetryBusy(target.id);
    setMessage(null);
    try {
      const updated = await clientRequest<DiscoveryTarget>(`discovery/targets/${target.id}/retry`, { method: "POST" });
      setTargets((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not retry this request");
    } finally {
      setRetryBusy(null);
    }
  }

  return (
    <section id="request-company" className="panel p-5 sm:p-6 scroll-mt-24">
      <h2 className="font-semibold text-main">Can’t find a company?</h2>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-soft">Paste the company’s careers page. Radar will check whether it can monitor that company automatically.</p>
      <form onSubmit={submit} className="mt-5 grid gap-4 md:grid-cols-2">
        <label className="field-label md:col-span-2">Careers page URL<input className="input mt-2" type="url" required placeholder="https://company.example/careers" value={url} onChange={(event) => setUrl(event.target.value)} /></label>
        <label className="field-label">Company name <span className="font-normal text-faint">(optional)</span><input className="input mt-2" placeholder="Example Company" value={companyName} onChange={(event) => setCompanyName(event.target.value)} /></label>
        <label className="flex items-center gap-3 self-end rounded-xl border border-ui surface-soft px-4 py-3 text-sm text-soft"><input type="checkbox" className="accent-emerald-600" checked={autoWatch} onChange={(event) => setAutoWatch(event.target.checked)} /><span>Follow the company automatically if Radar can add it</span></label>
        <div className="md:col-span-2"><button className="button-primary" disabled={busy}>{busy ? "Submitting…" : "Request company"}</button></div>
      </form>
      {message ? <p className="mt-4 text-xs leading-5 text-soft">{message}</p> : null}

      {targets.length ? <div className="mt-6 border-t border-ui pt-5"><h3 className="text-sm font-semibold text-main">Recent requests</h3><div className="mt-3 space-y-2">{targets.slice(0, 8).map((target) => <div key={target.id} className="flex flex-col gap-2 rounded-xl border border-ui surface-soft p-3 sm:flex-row sm:items-center sm:justify-between"><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><p className="truncate text-sm font-medium text-main">{target.company_name_hint || "Company request"}</p><Badge tone={tone(target.status)}>{label(target.status)}</Badge></div><p className="mt-1 truncate text-xs text-faint">{target.url}</p>{target.last_scanned_at ? <p className="mt-1 text-[11px] text-faint">Last checked {formatDateTime(target.last_scanned_at)}</p> : null}</div>{target.status === "FAILED" ? <button className="button-ghost shrink-0" disabled={retryBusy === target.id} onClick={() => retry(target)}>{retryBusy === target.id ? "Retrying…" : "Retry"}</button> : null}</div>)}</div></div> : null}
    </section>
  );
}
