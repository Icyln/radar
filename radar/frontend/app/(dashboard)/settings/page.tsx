import { Badge } from "@/components/badge";
import { PageHeader } from "@/components/page-header";
import { TelegramSettings } from "@/components/telegram-settings";
import { ThemeToggle } from "@/components/theme-toggle";
import { formatDateTime } from "@/lib/format";
import { requireUser, serverRequest } from "@/lib/server-api";
import type { TelegramConnection, TelegramDeliveryStatus } from "@/types/api";

export default async function SettingsPage() {
  const user = await requireUser();
  const [connection, deliveryStatus] = await Promise.all([
    serverRequest<TelegramConnection | null>("/api/v1/telegram/connection"),
    serverRequest<TelegramDeliveryStatus>("/api/v1/telegram/delivery-status")
  ]);

  return <>
    <PageHeader eyebrow="Account" title="Settings" description="Manage your account, workspace appearance, and job notifications." />
    <div className="space-y-5">
      <section className="panel p-5 sm:p-6">
        <div className="flex items-center justify-between gap-3">
          <div><h2 className="font-semibold text-main">Account</h2><p className="mt-1 text-sm text-soft">Your Radar sign-in information.</p></div>
          {user.is_admin ? <Badge tone="info">Administrator</Badge> : null}
        </div>
        <dl className="mt-5 grid gap-4 border-t border-ui pt-5 text-sm sm:grid-cols-2">
          <div><dt className="text-xs text-faint">Email</dt><dd className="mt-1 text-main">{user.email}</dd></div>
          <div><dt className="text-xs text-faint">Account created</dt><dd className="mt-1 text-main">{formatDateTime(user.created_at)}</dd></div>
        </dl>
      </section>

      <section className="panel p-5 sm:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div><h2 className="font-semibold text-main">Workspace appearance</h2><p className="mt-1 max-w-2xl text-sm leading-6 text-soft">Choose light or dark mode for your signed-in workspace. The public Radar website always keeps its standard light appearance.</p></div>
          <ThemeToggle />
        </div>
      </section>

      <TelegramSettings initialConnection={connection} initialDeliveryStatus={deliveryStatus} />
    </div>
  </>;
}
