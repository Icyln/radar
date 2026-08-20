import Link from "next/link";
import { Brand } from "@/components/brand";

export function PublicHeader({ signedIn = false }: { signedIn?: boolean }) {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/70 bg-white/90 backdrop-blur-xl">
      <div className="mx-auto flex h-[72px] max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Brand wordmark />
        <nav className="hidden items-center gap-7 text-[13px] font-medium text-slate-600 md:flex" aria-label="Public navigation">
          <Link href="/" className="transition hover:text-slate-950">Home</Link>
          <Link href="/#features" className="transition hover:text-slate-950">Features</Link>
          <Link href="/#how-it-works" className="transition hover:text-slate-950">How It Works</Link>
          <Link href="/how-to-use" className="transition hover:text-slate-950">How to Use</Link>
        </nav>
        <div className="flex items-center gap-2">
          <Link href="/how-to-use" className="text-xs font-medium text-slate-600 hover:text-slate-950 md:hidden">How to Use</Link>
          {signedIn ? (
            <Link href="/dashboard" className="public-button-primary">Open workspace</Link>
          ) : (
            <>
              <Link href="/login" className="hidden rounded-xl px-3.5 py-2.5 text-[13px] font-semibold text-slate-600 transition hover:bg-slate-100 hover:text-slate-950 sm:inline-flex">Sign in</Link>
              <Link href="/register" className="public-button-primary">Get started <span aria-hidden="true">→</span></Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
