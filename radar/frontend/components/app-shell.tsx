import { Brand } from "@/components/brand";
import { LogoutButton } from "@/components/logout-button";
import { ThemeToggle } from "@/components/theme-toggle";
import { WorkspaceNav } from "@/components/workspace-nav";
import type { User } from "@/types/api";

export function AppShell({ user, children }: { user: User; children: React.ReactNode }) {
  return (
    <div className="workspace lg:grid lg:grid-cols-[236px_minmax(0,1fr)]">
      <aside className="sticky top-0 hidden h-screen border-r border-ui bg-[var(--surface)] px-4 py-5 lg:flex lg:flex-col">
        <div className="px-2"><Brand href="/dashboard" /></div>
        <div className="mt-8"><WorkspaceNav isAdmin={user.is_admin} /></div>
        <div className="mt-auto border-t border-ui px-2 pt-4">
          <p className="truncate text-xs font-semibold text-main">{user.email}</p>
          <p className="mt-1 text-[11px] text-faint">{user.is_admin ? "Administrator" : "Radar account"}</p>
          <div className="mt-3 flex flex-wrap gap-2"><ThemeToggle compact /><LogoutButton /></div>
        </div>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-40 border-b border-ui bg-[color-mix(in_srgb,var(--surface)_94%,transparent)] px-4 py-3 backdrop-blur lg:hidden">
          <div className="flex items-center justify-between gap-3">
            <Brand href="/dashboard" />
            <details className="relative">
              <summary className="button-secondary cursor-pointer list-none">Menu</summary>
              <div className="absolute right-0 mt-2 w-60 rounded-xl border border-ui bg-[var(--surface)] p-2 shadow-2xl">
                <WorkspaceNav isAdmin={user.is_admin} mobile />
                <div className="mt-2 flex gap-2 border-t border-ui p-2 pt-3"><ThemeToggle compact /><LogoutButton /></div>
              </div>
            </details>
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl px-4 py-7 sm:px-6 lg:px-8 lg:py-9">{children}</main>
      </div>
    </div>
  );
}
