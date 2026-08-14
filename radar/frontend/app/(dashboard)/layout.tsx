import { AppShell } from "@/components/app-shell";
import { requireUser } from "@/lib/server-api";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const user = await requireUser();
  return <AppShell user={user}>{children}</AppShell>;
}
