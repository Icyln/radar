"use client";

import { useState } from "react";
import { Badge } from "@/components/badge";
import { clientRequest } from "@/lib/client-api";
import { formatDateTime } from "@/lib/format";
import type { TelegramConnection, TelegramDeliveryStatus, TelegramLink, TelegramTestResult } from "@/types/api";

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
      setMessage(`Telegram opened in a new tab. Finish connecting before ${formatDateTime(link.expires_at)}, then refresh this page.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not create a Telegram connection link.");
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
      setMessage(err instanceof Error ? err.message : "Could not disconnect Telegram.");
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
      setMessage(err instanceof Error ? err.message : "Could not send a test notification.");
    } finally {
      setTestBusy(false);
    }
  }

  async function refreshDeliveryStatus() {
    try {
      const next = await clientRequest<TelegramDeliveryStatus>("telegram/delivery-status");
      setDeliveryStatus(next);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not refresh notification status.");
    }
  }

  return (
    <section className="panel p-5 sm:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-semibold text-main">Telegram notifications</h2>
            <Badge tone={connection?.verified ? "success" : "neutral"}>{connection?.verified ? "Connected" : "Not connected"}</Badge>
          </div>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-soft">Get notified when Radar finds a new job that matches one of your active alerts. Radar avoids intentionally notifying you twice when the same job is found from more than one source.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {connection ? <>
            <button className="button-primary" onClick={sendTest} disabled={testBusy || busy}>{testBusy ? "Sending…" : "Send test"}</button>
            <button className="button-secondary" onClick={disconnect} disabled={busy || testBusy}>Disconnect</button>
          </> : <button className="button-primary" onClick={connect} disabled={busy}>{busy ? "Creating link…" : "Connect Telegram"}</button>}
        </div>
      </div>

      {connection ? <>
        <dl className="mt-5 grid gap-3 border-t border-ui pt-5 text-xs sm:grid-cols-2">
          <div><dt className="text-faint">Telegram account</dt><dd className="mt-1 text-main">{connection.username ? `@${connection.username}` : "Connected account"}</dd></div>
          <div><dt className="text-faint">Connected</dt><dd className="mt-1 text-main">{formatDateTime(connection.connected_at)}</dd></div>
        </dl>

        <div className="panel-soft mt-5 p-4">
          <div className="flex items-center justify-between gap-3">
            <div><p className="text-sm font-medium text-main">Notifications today</p><p className="mt-1 text-xs text-faint">Test notifications are not included.</p></div>
            <button className="button-secondary" onClick={refreshDeliveryStatus}>Refresh</button>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
            <div className="status-success rounded-lg p-3"><span>Sent</span><strong className="mt-1 block text-lg">{deliveryStatus.sent_today}</strong></div>
            <div className="status-neutral rounded-lg p-3"><span>Waiting</span><strong className="mt-1 block text-lg">{deliveryStatus.pending}</strong></div>
            <div className="status-danger rounded-lg p-3"><span>Failed</span><strong className="mt-1 block text-lg">{deliveryStatus.failed}</strong></div>
          </div>
        </div>
      </> : <div className="panel-soft mt-5 p-4 text-sm leading-6 text-soft">Connecting Telegram is optional. Radar still keeps matching jobs in your workspace if you prefer not to receive chat notifications.</div>}

      {message ? <p className="panel-soft mt-4 px-3 py-2 text-xs leading-5 text-soft">{message}</p> : null}
    </section>
  );
}
