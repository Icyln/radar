import Link from "next/link";
import { Brand } from "@/components/brand";
import { LogoutButton } from "@/components/logout-button";
import type { User } from "@/types/api";

const navigation = [
  ["/dashboard", "Overview"],
  ["/profiles", "Job profiles"],
  ["/jobs", "Jobs"],
  ["/companies", "Companies"],
  ["/settings", "Settings"]
] as const;

export function AppShell({ user, children }: { user: User; children: React.ReactNode }) {
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[244px_minmax(0,1fr)]">
      <aside className="hidden border-r border-zinc-800/80 bg-zinc-950/75 px-5 py-6 backdrop-blur lg:flex lg:min-h-screen lg:flex-col lg:sticky lg:top-0 lg:h-screen">
        <Brand />
        <nav className="mt-9 space-y-1">
          {navigation.map(([href, label]) => (
            <Link key={href} href={href} className="nav-link">
              {label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto border-t border-zinc-800 pt-5">
          <p className="truncate text-xs font-medium text-zinc-300">{user.email}</p>
          <p className="mt-1 text-[11px] text-zinc-600">{user.is_admin ? "Administrator" : "Radar user"}</p>
          <div className="mt-3"><LogoutButton /></div>
        </div>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-40 border-b border-zinc-800/80 bg-zinc-950/90 px-4 py-3 backdrop-blur lg:hidden">
          <div className="flex items-center justify-between gap-3">
            <Brand />
            <details className="relative">
              <summary className="cursor-pointer list-none rounded-lg border border-zinc-700 px-3 py-2 text-xs font-medium text-zinc-300">Menu</summary>
              <div className="absolute right-0 mt-2 w-52 rounded-xl border border-zinc-800 bg-zinc-950 p-2 shadow-2xl">
                {navigation.map(([href, label]) => <Link key={href} href={href} className="nav-link block">{label}</Link>)}
                <div className="mt-1 border-t border-zinc-800 pt-1"><LogoutButton /></div>
              </div>
            </details>
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl px-4 py-7 sm:px-6 lg:px-8 lg:py-9">{children}</main>
      </div>
    </div>
  );
}
