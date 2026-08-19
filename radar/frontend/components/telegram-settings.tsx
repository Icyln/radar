"use client";

import { useState } from "react";
import { Badge } from "@/components/badge";
import { clientRequest } from "@/lib/client-api";
import { formatDateTime } from "@/lib/format";
import type {
  TelegramConnection,
  TelegramDeliveryStatus,
  TelegramLink,
  TelegramTestResult
} from "@/types/api";

export function TelegramSettings({
  initialConnection,
  initialDeliveryStatus
}: {
  initialConnection: TelegramConnection | null;
  initialDeliveryStatus: TelegramDeliveryStatus;
}) {
  const [connection, setConnection] = useState(initialConnection);
  const [deliveryStatus, setDeliveryStatus] = useState(initialDeliveryStatus);
  const [busy, setBusy] = useState(false);
  const [testBusy, setTestBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function connect() {
    setBusy(true);
    setMessage(null);
    try {
      const link = await clientRequest<TelegramLink>("telegram/link-token", { method: "POST" });
      window.open(link.deep_link, "_blank", "noopener,noreferrer");
      setMessage(`Telegram link opened. Complete it before ${formatDateTime(link.expires_at)}, then refresh this page.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not create Telegram link");
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    if (!window.confirm("Disconnect Telegram from this Radar account?")) return;
    setBusy(true);
    setMessage(null);
    try {
      await clientRequest<void>("telegram/connection", { method: "DELETE" });
      setConnection(null);
      setDeliveryStatus({ sent_today: 0, pending: 0, failed: 0 });
      setMessage("Telegram disconnected.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not disconnect Telegram");
    } finally {
      setBusy(false);
    }
  }

  async function sendTest() {
    setTestBusy(true);
    setMessage(null);
    try {
      const result = await clientRequest<TelegramTestResult>("telegram/test", { method: "POST" });
      setMessage(result.message);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not send Telegram test alert");
    } finally {
      setTestBusy(false);
    }
  }

  async function refreshDeliveryStatus() {
    try {
      const next = await clientRequest<TelegramDeliveryStatus>("telegram/delivery-status");
      setDeliveryStatus(next);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not refresh Telegram delivery status");
    }
  }

  return (
    <section className="panel p-5 sm:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="font-semibold text-zinc-100">Telegram alerts</h2>
            <Badge tone={connection?.verified ? "success" : "neutral"}>
              {connection?.verified ? "Connected" : "Not connected"}
            </Badge>
          </div>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500">
            Radar sends new matching Direct ATS and Wide Search jobs to your verified Telegram chat. A Wide job that is later upgraded to a direct ATS keeps the same Radar job, so it is not intentionally alerted twice.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {connection ? (
            <>
              <button className="button-primary" onClick={sendTest} disabled={testBusy || busy}>
                {testBusy ? "Sending…" : "Send test alert"}
              </button>
              <button className="button-secondary" onClick={disconnect} disabled={busy || testBusy}>
                Disconnect
              </button>
            </>
          ) : (
            <button className="button-primary" onClick={connect} disabled={busy}>
              {busy ? "Creating link…" : "Connect Telegram"}
            </button>
          )}
        </div>
      </div>

      {connection ? (
        <>
          <dl className="mt-5 grid gap-3 border-t border-zinc-800 pt-5 text-xs sm:grid-cols-2">
            <div>
              <dt className="text-zinc-600">Username</dt>
              <dd className="mt-1 text-zinc-300">{connection.username ? `@${connection.username}` : "Not provided"}</dd>
            </div>
            <div>
              <dt className="text-zinc-600">Connected</dt>
              <dd className="mt-1 text-zinc-300">{formatDateTime(connection.connected_at)}</dd>
            </div>
          </dl>

          <div className="mt-5 rounded-xl border border-zinc-800 bg-zinc-950/40 p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-zinc-200">Job alert delivery today</p>
                <p className="mt-1 text-xs text-zinc-600">Test messages are not included in these counts.</p>
              </div>
              <button className="button-secondary" onClick={refreshDeliveryStatus}>Refresh</button>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
              <div className="rounded-lg border border-emerald-900/60 p-3">
                <span className="text-zinc-500">Sent</span>
                <strong className="mt-1 block text-lg text-emerald-300">{deliveryStatus.sent_today}</strong>
              </div>
              <div className="rounded-lg border border-zinc-800 p-3">
                <span className="text-zinc-500">Pending</span>
                <strong className="mt-1 block text-lg text-zinc-100">{deliveryStatus.pending}</strong>
              </div>
              <div className="rounded-lg border border-rose-950 p-3">
                <span className="text-zinc-500">Failed</span>
                <strong className="mt-1 block text-lg text-rose-300">{deliveryStatus.failed}</strong>
              </div>
            </div>
          </div>
        </>
      ) : null}

      {message ? (
        <p className="mt-4 rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-2 text-xs leading-5 text-zinc-400">
          {message}
        </p>
      ) : null}
    </section>
  );
}
