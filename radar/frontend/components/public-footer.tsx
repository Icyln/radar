import Link from "next/link";
import { Brand } from "@/components/brand";

export function PublicFooter() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 sm:px-6 md:grid-cols-[1.4fr_.8fr_.8fr] lg:px-8">
        <div className="max-w-sm">
          <Brand wordmark />
          <p className="mt-4 text-sm leading-6 text-slate-500">Radar helps you discover relevant jobs earlier with focused alerts, company tracking, and optional Telegram notifications.</p>
        </div>
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-400">Product</p>
          <nav className="mt-4 grid gap-3 text-sm text-slate-600" aria-label="Product links">
            <Link href="/#features" className="hover:text-slate-950">Features</Link>
            <Link href="/#how-it-works" className="hover:text-slate-950">How It Works</Link>
            <Link href="/how-to-use" className="hover:text-slate-950">How to Use</Link>
          </nav>
        </div>
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-400">Account</p>
          <nav className="mt-4 grid gap-3 text-sm text-slate-600" aria-label="Account links">
            <Link href="/login" className="hover:text-slate-950">Sign in</Link>
            <Link href="/register" className="hover:text-slate-950">Create account</Link>
          </nav>
        </div>
      </div>
      <div className="border-t border-slate-100">
        <div className="mx-auto max-w-7xl px-4 py-5 text-xs text-slate-400 sm:px-6 lg:px-8">© 2026 Radar. Focused job alerts without the noise.</div>
      </div>
    </footer>
  );
}
