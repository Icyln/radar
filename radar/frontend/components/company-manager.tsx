"use client";

import { FormEvent, useState } from "react";
import { Badge } from "@/components/badge";
import { clientRequest } from "@/lib/client-api";
import { formatDateTime, humanize } from "@/lib/format";
import type { ATSProvider, Company, CompanyPayload, CompanyWatchlistEntry, MonitoringPriority } from "@/types/api";

const providers: ATSProvider[] = ["GREENHOUSE", "LEVER", "ASHBY"];
const priorities: MonitoringPriority[] = ["HIGH", "NORMAL", "LOW"];
const blank: CompanyPayload = { name: "", website: null, career_url: "", ats_provider: "GREENHOUSE", ats_identifier: "", monitoring_priority: "NORMAL", active: true };

export function CompanyManager({ initialCompanies, initialWatchlistIds, isAdmin }: { initialCompanies: Company[]; initialWatchlistIds: string[]; isAdmin: boolean }) {
  const [companies, setCompanies] = useState(initialCompanies);
  const [watchlistIds, setWatchlistIds] = useState(initialWatchlistIds);
  const [form, setForm] = useState<CompanyPayload>(blank);
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [watchBusy, setWatchBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(null);
    try { const created = await clientRequest<Company>("companies", { method: "POST", body: JSON.stringify(form) }); setCompanies((current) => [...current, created].sort((a, b) => a.name.localeCompare(b.name))); setForm(blank); setShowForm(false); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not add company"); }
    finally { setBusy(false); }
  }
  async function toggleActive(company: Company) {
    setError(null);
    try { const updated = await clientRequest<Company>(`companies/${company.id}`, { method: "PATCH", body: JSON.stringify({ active: !company.active }) }); setCompanies((current) => current.map((item) => item.id === updated.id ? updated : item)); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not update company"); }
  }
  async function toggleWatch(company: Company) {
    const watched = watchlistIds.includes(company.id); setWatchBusy(company.id); setError(null);
    try { if (watched) { await clientRequest<void>(`companies/${company.id}/watchlist`, { method: "DELETE" }); setWatchlistIds((current) => current.filter((id) => id !== company.id)); } else { await clientRequest<CompanyWatchlistEntry>(`companies/${company.id}/watchlist`, { method: "PUT" }); setWatchlistIds((current) => current.includes(company.id) ? current : [...current, company.id]); } }
    catch (err) { setError(err instanceof Error ? err.message : "Could not update followed companies"); }
    finally { setWatchBusy(null); }
  }

  return <div className="space-y-5">
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><p className="text-xs text-soft">You follow {watchlistIds.length} {watchlistIds.length === 1 ? "company" : "companies"}.</p>{isAdmin ? <button className="button-primary" onClick={() => setShowForm((value) => !value)}>{showForm ? "Close form" : "Add monitored company"}</button> : null}</div>
    {showForm ? <form onSubmit={submit} className="panel p-5 sm:p-6"><h2 className="font-semibold text-main">Add monitored company</h2><p className="mt-1 text-xs text-soft">Admin-only source configuration.</p><div className="mt-5 grid gap-4 md:grid-cols-2"><label className="field-label">Company name<input className="input mt-2" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}/></label><label className="field-label">Source identifier<input className="input mt-2" required value={form.ats_identifier} onChange={(e) => setForm({ ...form, ats_identifier: e.target.value })}/></label><label className="field-label">Website<input className="input mt-2" type="url" value={form.website ?? ""} onChange={(e) => setForm({ ...form, website: e.target.value || null })}/></label><label className="field-label">Careers URL<input className="input mt-2" type="url" required value={form.career_url} onChange={(e) => setForm({ ...form, career_url: e.target.value })}/></label><label className="field-label">Source system<select className="input mt-2" value={form.ats_provider} onChange={(e) => setForm({ ...form, ats_provider: e.target.value as ATSProvider })}>{providers.map((provider) => <option key={provider}>{provider}</option>)}</select></label><label className="field-label">Monitoring priority<select className="input mt-2" value={form.monitoring_priority} onChange={(e) => setForm({ ...form, monitoring_priority: e.target.value as MonitoringPriority })}>{priorities.map((priority) => <option key={priority}>{priority}</option>)}</select></label></div><label className="mt-4 flex items-center gap-2 text-sm text-main"><input type="checkbox" className="accent-emerald-600" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })}/>Active monitoring</label>{error ? <p className="mt-4 text-sm text-danger">{error}</p> : null}<button className="button-primary mt-5" disabled={busy}>{busy ? "Adding…" : "Add company"}</button></form> : null}
    {error && !showForm ? <p className="text-sm text-danger">{error}</p> : null}

    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {companies.length === 0 ? <div className="panel p-6 text-sm text-soft md:col-span-2 xl:col-span-3">No companies match this search.</div> : companies.map((company) => { const watched = watchlistIds.includes(company.id); return <article key={company.id} className="panel p-5"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><a href={company.career_url} target="_blank" rel="noreferrer" className="font-semibold text-main hover:text-accent">{company.name}</a>{isAdmin ? <p className="mt-1 text-[11px] text-faint">{humanize(company.ats_provider)} · {company.ats_identifier}</p> : <p className="mt-1 text-xs text-soft">Company careers source</p>}</div><Badge tone={company.active && company.consecutive_failures === 0 ? "success" : company.active ? "warning" : "neutral"}>{company.active && company.consecutive_failures === 0 ? "Available" : company.active ? "Checking" : "Paused"}</Badge></div><div className="mt-4 flex flex-wrap gap-2"><button className={watched ? "button-secondary status-success" : "button-secondary"} disabled={watchBusy === company.id} onClick={() => toggleWatch(company)}>{watchBusy === company.id ? "Updating…" : watched ? "Following" : "Follow"}</button>{isAdmin ? <button className="button-ghost" onClick={() => toggleActive(company)}>{company.active ? "Pause source" : "Enable source"}</button> : null}</div>{isAdmin ? <div className="mt-4 border-t border-ui pt-3 text-[11px] text-faint"><p>Priority: {humanize(company.monitoring_priority)}</p><p className="mt-1">Last successful check: {formatDateTime(company.last_successful_check_at)}</p></div> : null}</article>; })}
    </div>
  </div>;
}
