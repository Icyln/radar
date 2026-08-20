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
      const next = await clientRequest<WideSearchRefreshResult>("discovery/wide-search/refresh", { method: "POST" });
      setResult(next);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not check for new jobs");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mb-5 panel-soft p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div><p className="text-sm font-semibold text-main">Check for new jobs now</p><p className="mt-1 max-w-2xl text-xs leading-5 text-soft">Radar already checks automatically. Use this only when you want an extra search right now.</p></div>
        <button type="button" className="button-secondary shrink-0" disabled={busy} onClick={refresh}>{busy ? "Checking…" : "Check now"}</button>
      </div>
      {result ? <p className="mt-3 text-xs text-soft">Checked current sources. <strong className="text-main">{result.jobs_new}</strong> new job{result.jobs_new === 1 ? "" : "s"} added, <strong className="text-main">{result.matches_created}</strong> new match{result.matches_created === 1 ? "" : "es"}{result.notifications_sent > 0 ? `, and ${result.notifications_sent} Telegram alert${result.notifications_sent === 1 ? "" : "s"} sent` : ""}.</p> : null}
      {result && result.provider_failed > 0 ? <p className="mt-2 text-xs text-warning">One or more sources were temporarily unavailable. Radar continued with the others.</p> : null}
      {error ? <p className="mt-3 text-xs text-danger">{error}</p> : null}
    </section>
  );
}
