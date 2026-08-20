"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const userNavigation = [
  ["/dashboard", "Home"],
  ["/profiles", "Job Alerts"],
  ["/jobs", "Jobs"],
  ["/companies", "Companies"],
  ["/settings", "Settings"]
] as const;

const adminNavigation = [
  ["/admin/system", "System status"],
  ["/admin/discovery", "Source discovery"]
] as const;

function active(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function WorkspaceNav({ isAdmin = false, mobile = false }: { isAdmin?: boolean; mobile?: boolean }) {
  const pathname = usePathname();
  return (
    <nav className={mobile ? "space-y-1" : "space-y-1"} aria-label="Workspace navigation">
      {userNavigation.map(([href, label]) => (
        <Link key={href} href={href} className={active(pathname, href) ? "nav-link nav-link-active" : "nav-link"}>{label}</Link>
      ))}
      {isAdmin ? (
        <div className="mt-5 border-t border-ui pt-4">
          <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">Admin</p>
          {adminNavigation.map(([href, label]) => (
            <Link key={href} href={href} className={active(pathname, href) ? "nav-link nav-link-active" : "nav-link"}>{label}</Link>
          ))}
        </div>
      ) : null}
    </nav>
  );
}
