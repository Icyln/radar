"use client";

import { FormEvent, useMemo, useState } from "react";
import { Badge } from "@/components/badge";
import { TagInput } from "@/components/tag-input";
import { clientRequest } from "@/lib/client-api";
import { humanize } from "@/lib/format";
import type { JobProfile, JobProfilePayload, ProfileCoverageMode, WorkMode } from "@/types/api";

const modes: WorkMode[] = ["REMOTE", "HYBRID", "ONSITE"];
const MAX_TITLES = 5;
const MAX_ACTIVE_ALERTS = 5;
const MAX_TOTAL_ALERTS = 10;

interface Draft {
  name: string;
  titles: string[];
  locations: string[];
  workModes: WorkMode[];
  excluded: string[];
  enabled: boolean;
  coverageMode: ProfileCoverageMode;
  maxJobAgeDays: number | null;
  includeUnknownPostedAt: boolean;
}

function toDraft(profile: JobProfile | null): Draft {
  if (!profile) return { name: "", titles: [], locations: [], workModes: [], excluded: [], enabled: true, coverageMode: "WIDE", maxJobAgeDays: 30, includeUnknownPostedAt: false };
  return {
    name: profile.name,
    titles: profile.job_titles,
    locations: profile.locations,
    workModes: profile.work_modes.filter((mode) => mode !== "UNKNOWN"),
    excluded: profile.excluded_keywords,
    enabled: profile.enabled,
    coverageMode: profile.coverage_mode,
    maxJobAgeDays: profile.max_job_age_days,
    includeUnknownPostedAt: profile.include_unknown_posted_at
  };
}

export function ProfileManager({ initialProfiles, watchlistCount }: { initialProfiles: JobProfile[]; watchlistCount: number }) {
  const [profiles, setProfiles] = useState(initialProfiles);
  const [editing, setEditing] = useState<JobProfile | null>(null);
  const [showForm, setShowForm] = useState(initialProfiles.length === 0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>(toDraft(null));
  const activeCount = profiles.filter((profile) => profile.enabled).length;

  function openCreate() {
    setEditing(null);
    setDraft(toDraft(null));
    setShowForm(true);
    setError(null);
  }
  function openEdit(profile: JobProfile) {
    setEditing(profile);
    setDraft(toDraft(profile));
    setShowForm(true);
    setError(null);
  }

  const payload = useMemo<JobProfilePayload>(() => ({
    name: draft.name.trim(),
    enabled: draft.enabled,
    coverage_mode: draft.coverageMode,
    job_titles: draft.titles,
    locations: draft.locations,
    work_modes: draft.workModes,
    excluded_keywords: draft.excluded,
    max_job_age_days: draft.maxJobAgeDays,
    include_unknown_posted_at: draft.includeUnknownPostedAt
  }), [draft]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const saved = await clientRequest<JobProfile>(editing ? `job-profiles/${editing.id}` : "job-profiles", { method: editing ? "PATCH" : "POST", body: JSON.stringify(payload) });
      setProfiles((current) => editing ? current.map((profile) => profile.id === saved.id ? saved : profile) : [...current, saved]);
      setShowForm(false);
      setEditing(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save this job alert");
    } finally {
      setBusy(false);
    }
  }

  async function toggle(profile: JobProfile) {
    setError(null);
    try {
      const updated = await clientRequest<JobProfile>(`job-profiles/${profile.id}`, { method: "PATCH", body: JSON.stringify({ enabled: !profile.enabled }) });
      setProfiles((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update this job alert");
    }
  }

  async function remove(profile: JobProfile) {
    if (!window.confirm(`Delete “${profile.name}”?`)) return;
    setError(null);
    try {
      await clientRequest<void>(`job-profiles/${profile.id}`, { method: "DELETE" });
      setProfiles((current) => current.filter((item) => item.id !== profile.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete this job alert");
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-soft">{activeCount} of {MAX_ACTIVE_ALERTS} active alerts · {profiles.length} of {MAX_TOTAL_ALERTS} total</p>
        <button className="button-primary" onClick={openCreate} disabled={profiles.length >= MAX_TOTAL_ALERTS}>New Job Alert</button>
      </div>
      {error && !showForm ? <p className="text-sm text-danger">{error}</p> : null}

      {showForm ? (
        <form onSubmit={submit} className="panel p-5 sm:p-6">
          <div className="flex items-start justify-between gap-4">
            <div><h2 className="text-base font-semibold text-main">{editing ? "Edit Job Alert" : "Create Job Alert"}</h2><p className="mt-1 text-xs leading-5 text-soft">Keep each alert focused on one role family. Radar searches broadly by default.</p></div>
            <button type="button" className="button-ghost" onClick={() => setShowForm(false)}>Cancel</button>
          </div>

          <div className="mt-5 grid gap-5 md:grid-cols-2">
            <label className="field-label">Alert name<input className="input mt-2" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} required placeholder="Frontend roles" /></label>
            <label className="field-label">Posted within<select className="input mt-2" value={draft.maxJobAgeDays === null ? "any" : String(draft.maxJobAgeDays)} onChange={(e) => setDraft({ ...draft, maxJobAgeDays: e.target.value === "any" ? null : Number(e.target.value) })}><option value="1">Last 24 hours</option><option value="3">Last 3 days</option><option value="7">Last 7 days</option><option value="14">Last 14 days</option><option value="30">Last 30 days</option><option value="60">Last 60 days</option><option value="90">Last 90 days</option><option value="any">Any time</option></select></label>
            <div className="md:col-span-2"><p className="field-label">Job titles <span className="font-normal text-faint">(up to {MAX_TITLES})</span></p><div className="mt-2"><TagInput ariaLabel="Job titles" values={draft.titles} onChange={(titles) => setDraft({ ...draft, titles })} maxItems={MAX_TITLES} placeholder="Frontend Engineer" /></div></div>
            <div className="md:col-span-2"><p className="field-label">Locations <span className="font-normal text-faint">(leave empty for any)</span></p><div className="mt-2"><TagInput ariaLabel="Locations" values={draft.locations} onChange={(locations) => setDraft({ ...draft, locations })} placeholder="Singapore, Remote" /></div></div>
          </div>

          <fieldset className="mt-5"><legend className="field-label">Work style <span className="font-normal text-faint">(leave all unchecked for any)</span></legend><div className="mt-2 flex flex-wrap gap-2">{modes.map((mode) => <label key={mode} className="chip-check"><input type="checkbox" className="accent-emerald-600" checked={draft.workModes.includes(mode)} onChange={(e) => setDraft({ ...draft, workModes: e.target.checked ? [...draft.workModes, mode] : draft.workModes.filter((item) => item !== mode) })} />{mode === "ONSITE" ? "On-site" : humanize(mode)}</label>)}</div></fieldset>

          <details className="mt-5 rounded-xl border border-ui surface-soft p-4" open={draft.coverageMode === "WATCHLIST" || draft.excluded.length > 0 || draft.includeUnknownPostedAt}>
            <summary className="cursor-pointer text-sm font-semibold text-main">More options</summary>
            <div className="mt-4 space-y-5">
              <div><p className="field-label">Words to exclude</p><div className="mt-2"><TagInput ariaLabel="Excluded words" values={draft.excluded} onChange={(excluded) => setDraft({ ...draft, excluded })} placeholder="Senior, Manager" /></div></div>
              <label className="flex items-start gap-3 rounded-xl border border-ui surface p-4 text-sm text-soft"><input type="checkbox" className="mt-1 accent-emerald-600" checked={draft.coverageMode === "WATCHLIST"} onChange={(e) => setDraft({ ...draft, coverageMode: e.target.checked ? "WATCHLIST" : "WIDE" })} /><span><strong className="block text-main">Only search companies I follow</strong><span className="mt-1 block text-xs leading-5 text-soft">Normally Radar searches everywhere it can. Turn this on only when you want this alert limited to your followed companies ({watchlistCount} currently).</span></span></label>
              {draft.coverageMode === "WATCHLIST" && watchlistCount === 0 ? <p className="text-xs text-warning">You are not following any companies yet, so this alert cannot match jobs until you follow at least one.</p> : null}
              <label className="flex items-start gap-3 text-sm text-soft"><input type="checkbox" className="mt-1 accent-emerald-600" checked={draft.includeUnknownPostedAt} disabled={draft.maxJobAgeDays === null} onChange={(e) => setDraft({ ...draft, includeUnknownPostedAt: e.target.checked })} /><span>Include jobs when the posting date is unavailable. These can be older than your selected time range.</span></label>
            </div>
          </details>

          <label className="mt-5 flex items-center gap-2 text-sm text-main"><input type="checkbox" className="accent-emerald-600" checked={draft.enabled} onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })} />Keep this alert active</label>
          {error ? <p className="mt-4 text-sm text-danger">{error}</p> : null}
          <div className="mt-6"><button className="button-primary" disabled={busy || payload.job_titles.length === 0}>{busy ? "Saving…" : editing ? "Save changes" : "Create Job Alert"}</button></div>
        </form>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        {profiles.map((profile) => (
          <article key={profile.id} className="panel p-5">
            <div className="flex items-start justify-between gap-3">
              <div><div className="flex flex-wrap items-center gap-2"><h2 className="font-semibold text-main">{profile.name}</h2><Badge tone={profile.enabled ? "success" : "neutral"}>{profile.enabled ? "Active" : "Paused"}</Badge><Badge tone={profile.coverage_mode === "WIDE" ? "info" : "neutral"}>{profile.coverage_mode === "WIDE" ? "Search everywhere" : "Followed companies only"}</Badge></div><p className="mt-2 text-xs text-soft">{profile.job_titles.join(" · ")}</p></div>
              <button className="button-ghost" onClick={() => openEdit(profile)}>Edit</button>
            </div>
            <dl className="mt-5 grid gap-3 text-xs sm:grid-cols-2"><div><dt className="text-faint">Locations</dt><dd className="mt-1 text-main">{profile.locations.join(", ") || "Any"}</dd></div><div><dt className="text-faint">Work style</dt><dd className="mt-1 text-main">{profile.work_modes.filter((mode) => mode !== "UNKNOWN").map((mode) => mode === "ONSITE" ? "On-site" : humanize(mode)).join(", ") || "Any"}</dd></div><div><dt className="text-faint">Posted within</dt><dd className="mt-1 text-main">{profile.max_job_age_days === null ? "Any time" : `${profile.max_job_age_days} days`}</dd></div><div><dt className="text-faint">Excluded words</dt><dd className="mt-1 text-main">{profile.excluded_keywords.join(", ") || "None"}</dd></div></dl>
            <div className="mt-5 flex gap-2 border-t border-ui pt-4"><button className="button-secondary" onClick={() => toggle(profile)}>{profile.enabled ? "Pause" : "Activate"}</button><button className="button-ghost text-danger" onClick={() => remove(profile)}>Delete</button></div>
          </article>
        ))}
      </div>
    </div>
  );
}
