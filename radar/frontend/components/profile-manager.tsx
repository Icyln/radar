"use client";

import { FormEvent, useMemo, useState } from "react";
import { Badge } from "@/components/badge";
import { clientRequest } from "@/lib/client-api";
import { humanize } from "@/lib/format";
import type { JobProfile, JobProfilePayload, WorkMode } from "@/types/api";

const modes: WorkMode[] = ["REMOTE", "HYBRID", "ONSITE", "UNKNOWN"];
const blank: JobProfilePayload = { name: "", enabled: true, job_titles: [], locations: [], work_modes: [], excluded_keywords: [] };
const split = (value: string) => value.split(",").map((v) => v.trim()).filter(Boolean);

export function ProfileManager({ initialProfiles }: { initialProfiles: JobProfile[] }) {
  const [profiles, setProfiles] = useState(initialProfiles);
  const [editing, setEditing] = useState<JobProfile | null>(null);
  const [showForm, setShowForm] = useState(initialProfiles.length === 0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const source = editing ?? blank;
  const [draft, setDraft] = useState({ name: source.name, titles: source.job_titles.join(", "), locations: source.locations.join(", "), workModes: source.work_modes as WorkMode[], excluded: source.excluded_keywords.join(", "), enabled: source.enabled });

  function openCreate() {
    setEditing(null);
    setDraft({ name: "", titles: "", locations: "", workModes: [], excluded: "", enabled: true });
    setShowForm(true);
    setError(null);
  }
  function openEdit(profile: JobProfile) {
    setEditing(profile);
    setDraft({ name: profile.name, titles: profile.job_titles.join(", "), locations: profile.locations.join(", "), workModes: profile.work_modes, excluded: profile.excluded_keywords.join(", "), enabled: profile.enabled });
    setShowForm(true);
    setError(null);
  }
  const payload = useMemo<JobProfilePayload>(() => ({ name: draft.name.trim(), enabled: draft.enabled, job_titles: split(draft.titles), locations: split(draft.locations), work_modes: draft.workModes, excluded_keywords: split(draft.excluded) }), [draft]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError(null);
    try {
      const saved = await clientRequest<JobProfile>(editing ? `job-profiles/${editing.id}` : "job-profiles", { method: editing ? "PATCH" : "POST", body: JSON.stringify(payload) });
      setProfiles((current) => editing ? current.map((p) => p.id === saved.id ? saved : p) : [...current, saved]);
      setShowForm(false); setEditing(null);
    } catch (err) { setError(err instanceof Error ? err.message : "Could not save profile"); }
    finally { setBusy(false); }
  }

  async function toggle(profile: JobProfile) {
    try {
      const updated = await clientRequest<JobProfile>(`job-profiles/${profile.id}`, { method: "PATCH", body: JSON.stringify({ enabled: !profile.enabled }) });
      setProfiles((current) => current.map((p) => p.id === updated.id ? updated : p));
    } catch (err) { setError(err instanceof Error ? err.message : "Could not update profile"); }
  }

  async function remove(profile: JobProfile) {
    if (!window.confirm(`Delete “${profile.name}”? Existing job matches are kept in history.`)) return;
    try {
      await clientRequest<void>(`job-profiles/${profile.id}`, { method: "DELETE" });
      setProfiles((current) => current.filter((p) => p.id !== profile.id));
    } catch (err) { setError(err instanceof Error ? err.message : "Could not delete profile"); }
  }

  return (
    <div className="space-y-5">
      <div className="flex justify-end"><button className="button-primary" onClick={openCreate}>New profile</button></div>
      {error && !showForm ? <p className="text-sm text-rose-400">{error}</p> : null}
      {showForm ? (
        <form onSubmit={submit} className="panel p-5 sm:p-6">
          <div className="flex items-start justify-between gap-4"><div><h2 className="text-base font-semibold text-zinc-100">{editing ? "Edit profile" : "Create monitoring profile"}</h2><p className="mt-1 text-xs text-zinc-500">Use comma-separated values for titles, locations, and exclusions.</p></div><button type="button" className="button-ghost" onClick={() => setShowForm(false)}>Cancel</button></div>
          <div className="mt-5 grid gap-5 md:grid-cols-2">
            <label className="field-label">Profile name<input className="input mt-2" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} required /></label>
            <label className="field-label">Job titles<input className="input mt-2" value={draft.titles} onChange={(e) => setDraft({ ...draft, titles: e.target.value })} required placeholder="Backend Engineer, Python Developer" /></label>
            <label className="field-label">Locations<input className="input mt-2" value={draft.locations} onChange={(e) => setDraft({ ...draft, locations: e.target.value })} placeholder="Singapore, Remote" /></label>
            <label className="field-label">Excluded keywords<input className="input mt-2" value={draft.excluded} onChange={(e) => setDraft({ ...draft, excluded: e.target.value })} placeholder="Senior, Staff, Manager" /></label>
          </div>
          <fieldset className="mt-5"><legend className="field-label">Work modes</legend><div className="mt-2 flex flex-wrap gap-2">{modes.map((mode) => <label key={mode} className="chip-check"><input type="checkbox" className="accent-emerald-400" checked={draft.workModes.includes(mode)} onChange={(e) => setDraft({ ...draft, workModes: e.target.checked ? [...draft.workModes, mode] : draft.workModes.filter((m) => m !== mode) })} />{humanize(mode)}</label>)}</div></fieldset>
          <label className="mt-5 flex items-center gap-2 text-sm text-zinc-300"><input type="checkbox" className="accent-emerald-400" checked={draft.enabled} onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })} />Enable monitoring profile</label>
          {error ? <p className="mt-4 text-sm text-rose-400">{error}</p> : null}
          <div className="mt-6"><button className="button-primary" disabled={busy || payload.job_titles.length === 0}>{busy ? "Saving…" : editing ? "Save changes" : "Create profile"}</button></div>
        </form>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        {profiles.map((profile) => (
          <article key={profile.id} className="panel p-5">
            <div className="flex items-start justify-between gap-3"><div><div className="flex items-center gap-2"><h2 className="font-semibold text-zinc-100">{profile.name}</h2><Badge tone={profile.enabled ? "success" : "neutral"}>{profile.enabled ? "Enabled" : "Paused"}</Badge></div><p className="mt-2 text-xs text-zinc-500">{profile.job_titles.join(" · ")}</p></div><button className="button-ghost" onClick={() => openEdit(profile)}>Edit</button></div>
            <dl className="mt-5 grid gap-3 text-xs sm:grid-cols-2"><div><dt className="text-zinc-600">Locations</dt><dd className="mt-1 text-zinc-300">{profile.locations.join(", ") || "Any"}</dd></div><div><dt className="text-zinc-600">Work modes</dt><dd className="mt-1 text-zinc-300">{profile.work_modes.map(humanize).join(", ") || "Any"}</dd></div><div className="sm:col-span-2"><dt className="text-zinc-600">Excluded</dt><dd className="mt-1 text-zinc-300">{profile.excluded_keywords.join(", ") || "None"}</dd></div></dl>
            <div className="mt-5 flex gap-2 border-t border-zinc-800 pt-4"><button className="button-secondary" onClick={() => toggle(profile)}>{profile.enabled ? "Pause" : "Enable"}</button><button className="button-ghost text-rose-400 hover:text-rose-300" onClick={() => remove(profile)}>Delete</button></div>
          </article>
        ))}
      </div>
    </div>
  );
}
