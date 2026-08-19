"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { Badge } from "@/components/badge";
import { clientRequest } from "@/lib/client-api";
import { formatDateTime, humanize } from "@/lib/format";
import type {
  ATSProvider,
  Company,
  CompanyPayload,
  CompanyWatchlistEntry,
  MonitoringPriority
} from "@/types/api";

const providers: ATSProvider[] = ["GREENHOUSE", "LEVER", "ASHBY"];
const priorities: MonitoringPriority[] = ["HIGH", "NORMAL", "LOW"];
const blank: CompanyPayload = {
  name: "",
  website: null,
  career_url: "",
  ats_provider: "GREENHOUSE",
  ats_identifier: "",
  monitoring_priority: "NORMAL",
  active: true
};

export function CompanyManager({
  initialCompanies,
  initialWatchlistIds,
  isAdmin
}: {
  initialCompanies: Company[];
  initialWatchlistIds: string[];
  isAdmin: boolean;
}) {
  const [companies, setCompanies] = useState(initialCompanies);
  const [watchlistIds, setWatchlistIds] = useState(initialWatchlistIds);
  const [form, setForm] = useState<CompanyPayload>(blank);
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [watchBusy, setWatchBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await clientRequest<Company>("companies", {
        method: "POST",
        body: JSON.stringify(form)
      });
      setCompanies((current) => [...current, created].sort((a, b) => a.name.localeCompare(b.name)));
      setForm(blank);
      setShowForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create company");
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive(company: Company) {
    setError(null);
    try {
      const updated = await clientRequest<Company>(`companies/${company.id}`, {
        method: "PATCH",
        body: JSON.stringify({ active: !company.active })
      });
      setCompanies((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update company");
    }
  }

  async function toggleWatch(company: Company) {
    const watched = watchlistIds.includes(company.id);
    setWatchBusy(company.id);
    setError(null);
    try {
      if (watched) {
        await clientRequest<void>(`companies/${company.id}/watchlist`, { method: "DELETE" });
        setWatchlistIds((current) => current.filter((id) => id !== company.id));
      } else {
        await clientRequest<CompanyWatchlistEntry>(`companies/${company.id}/watchlist`, { method: "PUT" });
        setWatchlistIds((current) => current.includes(company.id) ? current : [...current, company.id]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update watchlist");
    } finally {
      setWatchBusy(null);
    }
  }

  return <div className="space-y-5">
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-xs text-zinc-500">Watching {watchlistIds.length} {watchlistIds.length === 1 ? "company" : "companies"}. Watchlist-only profiles match only these sources.</p>
      <div className="flex gap-2">
        <Link className="button-secondary" href="/discovery">Request company</Link>
        {isAdmin ? <button className="button-primary" onClick={() => setShowForm((value) => !value)}>{showForm ? "Close form" : "Add company"}</button> : null}
      </div>
    </div>

    {showForm ? <form onSubmit={submit} className="panel p-5 sm:p-6">
      <h2 className="font-semibold text-zinc-100">Add ATS company</h2>
      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <label className="field-label">Company name<input className="input mt-2" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}/></label>
        <label className="field-label">ATS identifier<input className="input mt-2" required value={form.ats_identifier} onChange={(e) => setForm({ ...form, ats_identifier: e.target.value })}/></label>
        <label className="field-label">Website<input className="input mt-2" type="url" value={form.website ?? ""} onChange={(e) => setForm({ ...form, website: e.target.value || null })}/></label>
        <label className="field-label">Career URL<input className="input mt-2" type="url" required value={form.career_url} onChange={(e) => setForm({ ...form, career_url: e.target.value })}/></label>
        <label className="field-label">ATS provider<select className="input mt-2" value={form.ats_provider} onChange={(e) => setForm({ ...form, ats_provider: e.target.value as ATSProvider })}>{providers.map((provider) => <option key={provider}>{provider}</option>)}</select></label>
        <label className="field-label">Priority<select className="input mt-2" value={form.monitoring_priority} onChange={(e) => setForm({ ...form, monitoring_priority: e.target.value as MonitoringPriority })}>{priorities.map((priority) => <option key={priority}>{priority}</option>)}</select></label>
      </div>
      <label className="mt-4 flex items-center gap-2 text-sm text-zinc-300"><input type="checkbox" className="accent-emerald-400" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })}/>Active monitoring</label>
      {error ? <p className="mt-4 text-sm text-rose-400">{error}</p> : null}
      <button className="button-primary mt-5" disabled={busy}>{busy ? "Adding…" : "Add company"}</button>
    </form> : null}

    {error && !showForm ? <p className="text-sm text-rose-400">{error}</p> : null}
    <div className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950/50">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-zinc-800 bg-zinc-900/50 text-xs text-zinc-500">
            <tr><th className="px-4 py-3 font-medium">Company</th><th className="px-4 py-3 font-medium">Source</th><th className="px-4 py-3 font-medium">Watchlist</th><th className="px-4 py-3 font-medium">Priority</th><th className="px-4 py-3 font-medium">Last success</th><th className="px-4 py-3 font-medium">Health</th>{isAdmin ? <th className="px-4 py-3"></th> : null}</tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/70">
            {companies.length === 0 ? <tr><td colSpan={isAdmin ? 7 : 6} className="px-4 py-10 text-center text-sm text-zinc-600">No monitored companies configured yet.</td></tr> : companies.map((company) => {
              const watched = watchlistIds.includes(company.id);
              return <tr key={company.id} className="text-zinc-300">
                <td className="px-4 py-4"><a href={company.career_url} target="_blank" rel="noreferrer" className="font-medium text-zinc-100 hover:text-emerald-300">{company.name}</a><p className="mt-1 text-xs text-zinc-600">{company.ats_identifier}</p></td>
                <td className="px-4 py-4">{humanize(company.ats_provider)}</td>
                <td className="px-4 py-4"><button className={watched ? "button-secondary border-emerald-800 text-emerald-300" : "button-ghost"} disabled={watchBusy === company.id} onClick={() => toggleWatch(company)}>{watchBusy === company.id ? "Updating…" : watched ? "Watching" : "Watch"}</button></td>
                <td className="px-4 py-4"><Badge>{humanize(company.monitoring_priority)}</Badge>{company.discovery_boost_until ? <p className="mt-1 max-w-40 text-xs text-amber-300">Signal boost until {formatDateTime(company.discovery_boost_until)}</p> : null}</td>
                <td className="px-4 py-4 whitespace-nowrap text-xs text-zinc-500">{formatDateTime(company.last_successful_check_at)}</td>
                <td className="px-4 py-4"><Badge tone={!company.active ? "neutral" : company.consecutive_failures > 0 ? "warning" : "success"}>{!company.active ? "Paused" : company.consecutive_failures > 0 ? `${company.consecutive_failures} failures` : "Healthy"}</Badge></td>
                {isAdmin ? <td className="px-4 py-4 text-right"><button className="button-ghost" onClick={() => toggleActive(company)}>{company.active ? "Pause" : "Enable"}</button></td> : null}
              </tr>;
            })}
          </tbody>
        </table>
      </div>
    </div>
  </div>;
}
