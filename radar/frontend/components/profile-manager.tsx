"use client";

import { FormEvent, useMemo, useState } from "react";
import { Badge } from "@/components/badge";
import { clientRequest } from "@/lib/client-api";
import { humanize } from "@/lib/format";
import type {
  JobProfile,
  JobProfilePayload,
  ProfileCoverageMode,
  WorkMode
} from "@/types/api";

const modes: WorkMode[] = ["REMOTE", "HYBRID", "ONSITE", "UNKNOWN"];
const split = (value: string) => value.split(",").map((v) => v.trim()).filter(Boolean);

interface Draft {
  name: string;
  titles: string;
  locations: string;
  workModes: WorkMode[];
  excluded: string;
  enabled: boolean;
  coverageMode: ProfileCoverageMode;
  maxJobAgeDays: number | null;
  includeUnknownPostedAt: boolean;
}

function toDraft(profile: JobProfile | null): Draft {
  if (!profile) {
    return {
      name: "",
      titles: "",
      locations: "",
      workModes: [],
      excluded: "",
      enabled: true,
      coverageMode: "WIDE",
      maxJobAgeDays: 30,
      includeUnknownPostedAt: false
    };
  }
  return {
    name: profile.name,
    titles: profile.job_titles.join(", "),
    locations: profile.locations.join(", "),
    workModes: profile.work_modes,
    excluded: profile.excluded_keywords.join(", "),
    enabled: profile.enabled,
    coverageMode: profile.coverage_mode,
    maxJobAgeDays: profile.max_job_age_days,
    includeUnknownPostedAt: profile.include_unknown_posted_at
  };
}

export function ProfileManager({
  initialProfiles,
  watchlistCount
}: {
  initialProfiles: JobProfile[];
  watchlistCount: number;
}) {
  const [profiles, setProfiles] = useState(initialProfiles);
  const [editing, setEditing] = useState<JobProfile | null>(null);
  const [showForm, setShowForm] = useState(initialProfiles.length === 0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>(toDraft(null));

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
    job_titles: split(draft.titles),
    locations: split(draft.locations),
    work_modes: draft.workModes,
    excluded_keywords: split(draft.excluded),
    max_job_age_days: draft.maxJobAgeDays,
    include_unknown_posted_at: draft.includeUnknownPostedAt
  }), [draft]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const saved = await clientRequest<JobProfile>(
        editing ? `job-profiles/${editing.id}` : "job-profiles",
        {
          method: editing ? "PATCH" : "POST",
          body: JSON.stringify(payload)
        }
      );
      setProfiles((current) => editing
        ? current.map((profile) => profile.id === saved.id ? saved : profile)
        : [...current, saved]);
      setShowForm(false);
      setEditing(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile");
    } finally {
      setBusy(false);
    }
  }

  async function toggle(profile: JobProfile) {
    try {
      const updated = await clientRequest<JobProfile>(`job-profiles/${profile.id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !profile.enabled })
      });
      setProfiles((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update profile");
    }
  }

  async function remove(profile: JobProfile) {
    if (!window.confirm(`Delete “${profile.name}”?`)) return;
    try {
      await clientRequest<void>(`job-profiles/${profile.id}`, { method: "DELETE" });
      setProfiles((current) => current.filter((item) => item.id !== profile.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete profile");
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex justify-end">
        <button className="button-primary" onClick={openCreate}>New profile</button>
      </div>
      {error && !showForm ? <p className="text-sm text-rose-400">{error}</p> : null}

      {showForm ? (
        <form onSubmit={submit} className="panel p-5 sm:p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-base font-semibold text-zinc-100">
                {editing ? "Edit profile" : "Create monitoring profile"}
              </h2>
              <p className="mt-1 text-xs text-zinc-500">
                Matching stays deterministic; Wide Search can match fresh jobs even before Radar adds the employer to its registry.
              </p>
            </div>
            <button type="button" className="button-ghost" onClick={() => setShowForm(false)}>Cancel</button>
          </div>

          <div className="mt-5 grid gap-5 md:grid-cols-2">
            <label className="field-label">Profile name
              <input className="input mt-2" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} required />
            </label>
            <label className="field-label">Job titles
              <input className="input mt-2" value={draft.titles} onChange={(e) => setDraft({ ...draft, titles: e.target.value })} required placeholder="Backend Engineer, Python Developer" />
            </label>
            <label className="field-label">Locations
              <input className="input mt-2" value={draft.locations} onChange={(e) => setDraft({ ...draft, locations: e.target.value })} placeholder="Singapore, Remote" />
            </label>
            <label className="field-label">Excluded keywords
              <input className="input mt-2" value={draft.excluded} onChange={(e) => setDraft({ ...draft, excluded: e.target.value })} placeholder="Senior, Staff, Manager" />
            </label>
          </div>

          <fieldset className="mt-5">
            <legend className="field-label">Coverage</legend>
            <div className="mt-2 grid gap-3 md:grid-cols-2">
              <label className={`cursor-pointer rounded-xl border p-4 ${draft.coverageMode === "WIDE" ? "border-emerald-700 bg-emerald-950/20" : "border-zinc-800 bg-zinc-950/40"}`}>
                <div className="flex items-start gap-3">
                  <input type="radio" name="coverage" className="mt-1 accent-emerald-400" checked={draft.coverageMode === "WIDE"} onChange={() => setDraft({ ...draft, coverageMode: "WIDE" })} />
                  <div><p className="text-sm font-medium text-zinc-100">Wide Search</p><p className="mt-1 text-xs leading-5 text-zinc-500">Find fresh matching jobs across Radar’s discovery feeds and direct ATS registry. Employers do not need to be on your watchlist or already registered.</p></div>
                </div>
              </label>
              <label className={`cursor-pointer rounded-xl border p-4 ${draft.coverageMode === "WATCHLIST" ? "border-emerald-700 bg-emerald-950/20" : "border-zinc-800 bg-zinc-950/40"}`}>
                <div className="flex items-start gap-3">
                  <input type="radio" name="coverage" className="mt-1 accent-emerald-400" checked={draft.coverageMode === "WATCHLIST"} onChange={() => setDraft({ ...draft, coverageMode: "WATCHLIST" })} />
                  <div><p className="text-sm font-medium text-zinc-100">Watchlist only</p><p className="mt-1 text-xs leading-5 text-zinc-500">Match only companies you explicitly watch. Currently watching {watchlistCount}.</p></div>
                </div>
              </label>
            </div>
            {draft.coverageMode === "WATCHLIST" && watchlistCount === 0 ? (
              <p className="mt-2 text-xs text-amber-300">Your watchlist is empty. Add companies on the Companies page before this profile can match jobs.</p>
            ) : null}
          </fieldset>

          <fieldset className="mt-5">
            <legend className="field-label">Freshness</legend>
            <div className="mt-2 grid gap-3 md:grid-cols-2">
              <label className="field-label">Maximum job age
                <select
                  className="input mt-2"
                  value={draft.maxJobAgeDays === null ? "any" : String(draft.maxJobAgeDays)}
                  onChange={(e) => setDraft({ ...draft, maxJobAgeDays: e.target.value === "any" ? null : Number(e.target.value) })}
                >
                  <option value="1">Last 24 hours</option>
                  <option value="3">Last 3 days</option>
                  <option value="7">Last 7 days</option>
                  <option value="14">Last 14 days</option>
                  <option value="30">Last 30 days</option>
                  <option value="60">Last 60 days</option>
                  <option value="90">Last 90 days</option>
                  <option value="any">Any age</option>
                </select>
              </label>
              <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-4">
                <p className="text-sm font-medium text-zinc-100">Unknown posting dates</p>
                <label className="mt-3 flex items-start gap-2 text-xs leading-5 text-zinc-400">
                  <input
                    type="checkbox"
                    className="mt-1 accent-emerald-400"
                    checked={draft.includeUnknownPostedAt}
                    disabled={draft.maxJobAgeDays === null}
                    onChange={(e) => setDraft({ ...draft, includeUnknownPostedAt: e.target.checked })}
                  />
                  Include baseline jobs when the ATS does not expose a reliable posting date. These may be older than your freshness window.
                </label>
              </div>
            </div>
            <p className="mt-2 text-xs text-zinc-500">New jobs detected after Radar has baselined a company can use their first-seen time when the ATS omits a posting timestamp. Baseline inventory with no date stays unknown.</p>
          </fieldset>

          <fieldset className="mt-5">
            <legend className="field-label">Work modes</legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {modes.map((mode) => (
                <label key={mode} className="chip-check">
                  <input type="checkbox" className="accent-emerald-400" checked={draft.workModes.includes(mode)} onChange={(e) => setDraft({ ...draft, workModes: e.target.checked ? [...draft.workModes, mode] : draft.workModes.filter((item) => item !== mode) })} />
                  {humanize(mode)}
                </label>
              ))}
            </div>
          </fieldset>

          <label className="mt-5 flex items-center gap-2 text-sm text-zinc-300">
            <input type="checkbox" className="accent-emerald-400" checked={draft.enabled} onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })} />
            Enable monitoring profile
          </label>
          {error ? <p className="mt-4 text-sm text-rose-400">{error}</p> : null}
          <div className="mt-6"><button className="button-primary" disabled={busy || payload.job_titles.length === 0}>{busy ? "Saving…" : editing ? "Save changes" : "Create profile"}</button></div>
        </form>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        {profiles.map((profile) => (
          <article key={profile.id} className="panel p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-semibold text-zinc-100">{profile.name}</h2>
                  <Badge tone={profile.enabled ? "success" : "neutral"}>{profile.enabled ? "Enabled" : "Paused"}</Badge>
                  <Badge tone={profile.coverage_mode === "WIDE" ? "info" : "neutral"}>{profile.coverage_mode === "WIDE" ? "Wide search" : "Watchlist"}</Badge>
                  <Badge>{profile.max_job_age_days === null ? "Any age" : `≤ ${profile.max_job_age_days}d`}</Badge>
                </div>
                <p className="mt-2 text-xs text-zinc-500">{profile.job_titles.join(" · ")}</p>
              </div>
              <button className="button-ghost" onClick={() => openEdit(profile)}>Edit</button>
            </div>
            <dl className="mt-5 grid gap-3 text-xs sm:grid-cols-2">
              <div><dt className="text-zinc-600">Locations</dt><dd className="mt-1 text-zinc-300">{profile.locations.join(", ") || "Any"}</dd></div>
              <div><dt className="text-zinc-600">Work modes</dt><dd className="mt-1 text-zinc-300">{profile.work_modes.map(humanize).join(", ") || "Any"}</dd></div>
              <div className="sm:col-span-2"><dt className="text-zinc-600">Excluded</dt><dd className="mt-1 text-zinc-300">{profile.excluded_keywords.join(", ") || "None"}</dd></div>
            </dl>
            <div className="mt-5 flex gap-2 border-t border-zinc-800 pt-4">
              <button className="button-secondary" onClick={() => toggle(profile)}>{profile.enabled ? "Pause" : "Enable"}</button>
              <button className="button-ghost text-rose-400 hover:text-rose-300" onClick={() => remove(profile)}>Delete</button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
