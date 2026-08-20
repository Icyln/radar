import Link from "next/link";
import { Brand } from "@/components/brand";
import { Glyph } from "@/components/public-visuals";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="public-shell min-h-screen">
      <header className="mx-auto flex h-[72px] max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Brand wordmark />
        <Link href="/how-to-use" className="rounded-xl px-3 py-2 text-sm font-semibold text-slate-600 transition hover:bg-white hover:text-slate-950">How to Use</Link>
      </header>
      <main className="mx-auto grid min-h-[calc(100vh-72px)] max-w-7xl gap-10 px-4 pb-12 pt-5 sm:px-6 lg:grid-cols-[1fr_.82fr] lg:items-center lg:px-8 lg:pb-16">
        <section className="hidden lg:block">
          <span className="inline-flex rounded-full border border-emerald-100 bg-white px-3 py-1.5 text-[10px] font-extrabold uppercase tracking-[0.16em] text-emerald-700 shadow-sm">Your job search, organized</span>
          <h1 className="mt-5 max-w-xl text-[2.8rem] font-extrabold leading-[1.04] tracking-[-0.04em] text-slate-950">Spend less time searching. Keep the right opportunities close.</h1>
          <p className="mt-4 max-w-xl text-base leading-7 text-slate-600">Sign in to manage focused alerts, review matches, follow companies, and receive optional Telegram notifications.</p>
          <div className="relative mt-8 max-w-xl overflow-hidden rounded-[24px] border border-emerald-100 bg-[linear-gradient(135deg,#063b45_0%,#08765a_60%,#10a66d_100%)] p-6 text-white shadow-[0_24px_65px_rgba(5,85,65,0.2)]">
            <div className="absolute -right-12 -top-20 h-64 w-64 rounded-full border border-white/10"/><div className="absolute right-3 -top-12 h-44 w-44 rounded-full border border-white/10"/>
            <div className="relative z-10 grid grid-cols-3 gap-3">
              {[["radar","Focused alerts"],["telegram","Telegram ready"],["bookmark","Save jobs"]].map(([icon,label])=><div key={label} className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur"><span className="grid h-9 w-9 place-items-center rounded-xl bg-white/10 text-emerald-100"><Glyph name={icon as "radar"|"telegram"|"bookmark"} className="h-5 w-5"/></span><p className="mt-4 text-xs font-bold">{label}</p></div>)}
            </div>
            <p className="relative z-10 mt-6 text-sm leading-6 text-emerald-50/85">The technical monitoring stays behind the scenes. Your workspace stays focused on jobs, alerts, companies, and decisions.</p>
          </div>
        </section>
        <div className="mx-auto w-full max-w-md">{children}</div>
      </main>
    </div>
  );
}
