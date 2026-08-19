"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { clientRequest } from "@/lib/client-api";
import type { WideSearchRefreshResult } from "@/types/api";

export function WideSearchRefresh() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<WideSearchRefreshResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setBusy(true);
    setError(null);
    try {
      const next = await clientRequest<WideSearchRefreshResult>("discovery/wide-search/refresh", {
        method: "POST"
      });
      setResult(next);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Wide Search refresh failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mb-5 rounded-xl border border-emerald-900/70 bg-emerald-950/10 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-zinc-100">Wide Search live test</p>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-zinc-500">
            Pull fresh jobs for your enabled Wide profiles now. Jobs can appear even when the employer is not in your registry or watchlist.
          </p>
        </div>
        <button type="button" className="button-primary shrink-0" disabled={busy} onClick={refresh}>
          {busy ? "Searching fresh jobs…" : "Refresh Wide Search"}
        </button>
      </div>

      {result ? (
        <div className="mt-4 grid gap-2 text-xs sm:grid-cols-2 xl:grid-cols-6">
          <div className="rounded-lg border border-zinc-800 bg-zinc-950/50 p-3"><span className="text-zinc-500">Signals checked</span><strong className="mt-1 block text-base text-zinc-100">{result.signals_seen}</strong></div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-950/50 p-3"><span className="text-zinc-500">Relevant</span><strong className="mt-1 block text-base text-zinc-100">{result.signals_relevant}</strong></div>
          <div className="rounded-lg border border-emerald-900/70 bg-zinc-950/50 p-3"><span className="text-zinc-500">New jobs</span><strong className="mt-1 block text-base text-emerald-300">{result.jobs_new}</strong></div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-950/50 p-3"><span className="text-zinc-500">Existing jobs</span><strong className="mt-1 block text-base text-zinc-100">{result.jobs_existing + result.jobs_updated}</strong></div>
          <div className="rounded-lg border border-sky-900/70 bg-zinc-950/50 p-3"><span className="text-zinc-500">New matches</span><strong className="mt-1 block text-base text-sky-300">{result.matches_created}</strong></div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-950/50 p-3">
            <span className="text-zinc-500">Telegram</span>
            <strong className={`mt-1 block text-base ${result.notifications_sent > 0 ? "text-emerald-300" : "text-zinc-100"}`}>
              {result.telegram_ready ? `${result.notifications_sent} sent` : "Not connected"}
            </strong>
            {result.telegram_ready && result.notifications_queued > result.notifications_sent ? (
              <span className="mt-1 block text-[11px] text-amber-300">{result.notifications_queued - result.notifications_sent} queued</span>
            ) : null}
          </div>
        </div>
      ) : null}

      {result && result.probe_candidates_staged > 0 ? (
        <p className="mt-3 text-xs text-zinc-500">Radar also seeded {result.probe_candidates_staged} direct ATS upgrade candidate{result.probe_candidates_staged === 1 ? "" : "s"} in the background.</p>
      ) : null}

      {result && result.provider_failed > 0 ? (
        <p className="mt-3 text-xs text-amber-300">
          {result.provider_failed} discovery source{result.provider_failed === 1 ? "" : "s"} unavailable; Radar continued with the remaining sources.
        </p>
      ) : null}
      {result && result.signals_relevant > 0 && result.jobs_new === 0 ? (
        <p className="mt-3 text-xs text-zinc-400">No new rows were needed — those matching jobs were already in Radar. Check Matched or filter Detected to “Wide discovery”.</p>
      ) : null}
      {error ? <p className="mt-3 text-xs text-rose-400">{error}</p> : null}
    </section>
  );
}
