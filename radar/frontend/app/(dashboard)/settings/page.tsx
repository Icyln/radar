import { Badge } from "@/components/badge";
import { PageHeader } from "@/components/page-header";
import { TelegramSettings } from "@/components/telegram-settings";
import { formatDateTime } from "@/lib/format";
import { requireUser, serverRequest } from "@/lib/server-api";
import type { TelegramConnection, TelegramDeliveryStatus } from "@/types/api";

export default async function SettingsPage() {
  const user = await requireUser();
  const connection = await serverRequest<TelegramConnection | null>("/api/v1/telegram/connection");
  const deliveryStatus = await serverRequest<TelegramDeliveryStatus>("/api/v1/telegram/delivery-status");
  return <><PageHeader eyebrow="Account" title="Settings" description="Manage your Radar account information and Telegram alert connection." />
    <div className="space-y-5"><section className="panel p-5 sm:p-6"><div className="flex items-center justify-between gap-3"><h2 className="font-semibold text-zinc-100">Account information</h2>{user.is_admin ? <Badge tone="info">Administrator</Badge> : null}</div><dl className="mt-5 grid gap-4 border-t border-zinc-800 pt-5 text-sm sm:grid-cols-2"><div><dt className="text-xs text-zinc-600">Email</dt><dd className="mt-1 text-zinc-300">{user.email}</dd></div><div><dt className="text-xs text-zinc-600">Account created</dt><dd className="mt-1 text-zinc-300">{formatDateTime(user.created_at)}</dd></div></dl></section><TelegramSettings initialConnection={connection} initialDeliveryStatus={deliveryStatus} /></div>
  </>;
}
