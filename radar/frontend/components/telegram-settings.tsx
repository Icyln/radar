"use client";

import { useState } from "react";
import { Badge } from "@/components/badge";
import { clientRequest } from "@/lib/client-api";
import { formatDateTime } from "@/lib/format";
import type { TelegramConnection, TelegramLink } from "@/types/api";

export function TelegramSettings({ initialConnection }: { initialConnection: TelegramConnection | null }) {
  const [connection, setConnection] = useState(initialConnection);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function connect() {
    setBusy(true); setMessage(null);
    try {
      const link = await clientRequest<TelegramLink>("telegram/link-token", { method: "POST" });
      window.open(link.deep_link, "_blank", "noopener,noreferrer");
      setMessage(`Telegram link opened. Complete it before ${formatDateTime(link.expires_at)}, then refresh this page.`);
    } catch (err) { setMessage(err instanceof Error ? err.message : "Could not create Telegram link"); }
    finally { setBusy(false); }
  }

  async function disconnect() {
    if (!window.confirm("Disconnect Telegram from this Radar account?")) return;
    setBusy(true); setMessage(null);
    try { await clientRequest<void>("telegram/connection", { method: "DELETE" }); setConnection(null); setMessage("Telegram disconnected."); }
    catch (err) { setMessage(err instanceof Error ? err.message : "Could not disconnect Telegram"); }
    finally { setBusy(false); }
  }

  return <section className="panel p-5 sm:p-6"><div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div><div className="flex items-center gap-2"><h2 className="font-semibold text-zinc-100">Telegram alerts</h2><Badge tone={connection?.verified ? "success" : "neutral"}>{connection?.verified ? "Connected" : "Not connected"}</Badge></div><p className="mt-2 max-w-xl text-sm leading-6 text-zinc-500">Radar sends matching job alerts to your verified Telegram chat. Linking uses a short-lived one-time token.</p></div>{connection ? <button className="button-secondary" onClick={disconnect} disabled={busy}>Disconnect</button> : <button className="button-primary" onClick={connect} disabled={busy}>{busy ? "Creating link…" : "Connect Telegram"}</button>}</div>{connection ? <dl className="mt-5 grid gap-3 border-t border-zinc-800 pt-5 text-xs sm:grid-cols-2"><div><dt className="text-zinc-600">Username</dt><dd className="mt-1 text-zinc-300">{connection.username ? `@${connection.username}` : "Not provided"}</dd></div><div><dt className="text-zinc-600">Connected</dt><dd className="mt-1 text-zinc-300">{formatDateTime(connection.connected_at)}</dd></div></dl> : null}{message ? <p className="mt-4 rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-2 text-xs leading-5 text-zinc-400">{message}</p> : null}</section>;
}
