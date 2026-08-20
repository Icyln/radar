import { AppShell } from "@/components/app-shell";
import { requireUser } from "@/lib/server-api";

const themeScript = `
try {
  const value = localStorage.getItem('radar-workspace-theme');
  document.documentElement.dataset.workspaceTheme = value === 'dark' ? 'dark' : 'light';
} catch (_) {
  document.documentElement.dataset.workspaceTheme = 'light';
}`;

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const user = await requireUser();
  return <><script dangerouslySetInnerHTML={{ __html: themeScript }} /><AppShell user={user}>{children}</AppShell></>;
}
