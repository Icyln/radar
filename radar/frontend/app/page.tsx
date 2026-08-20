import Link from "next/link";
import { PublicFooter } from "@/components/public-footer";
import { PublicHeader } from "@/components/public-header";
import { DashboardPlaceholder, FeatureVisual, Glyph } from "@/components/public-visuals";
import { getCurrentUser } from "@/lib/server-api";

const cards = [
  { title: "Job Matches", text: "See relevant roles based on the alerts you create.", type: "matches" as const, icon: "briefcase" as const },
  { title: "Telegram Alerts", text: "Get matching jobs delivered directly to Telegram.", type: "telegram" as const, icon: "telegram" as const },
  { title: "Followed Companies", text: "Keep a closer eye on employers you care about.", type: "companies" as const, icon: "building" as const },
  { title: "Saved Jobs", text: "Keep promising opportunities easy to find later.", type: "saved" as const, icon: "bookmark" as const }
];

const features = [
  ["radar", "Focused monitoring", "Radar keeps checking job sources so you do not have to repeat the same searches every day."],
  ["search", "Smarter matching", "Your alerts narrow the noise and surface jobs closer to what you actually want."],
  ["bell", "Instant notifications", "Connect Telegram once and receive new matches when they are ready."],
  ["building", "Company tracking", "Follow specific employers and keep their openings alongside broader job discovery."],
  ["bookmark", "Save and organize", "Save useful jobs, hide the rest, and keep your workspace focused."],
  ["shield", "Simple by design", "The technical source monitoring stays behind the scenes while the workspace stays understandable."]
] as const;

export default async function Home() {
  const user = await getCurrentUser();
  const primaryHref = user ? "/profiles" : "/register";

  return (
    <div className="public-shell">
      <PublicHeader signedIn={Boolean(user)} />
      <main>
        <section className="relative overflow-hidden">
          <div className="pointer-events-none absolute left-[55%] top-[-8rem] h-[30rem] w-[30rem] rounded-full bg-emerald-100/50 blur-3xl" />
          <div className="pointer-events-none absolute left-[8%] top-[23rem] h-36 w-36 rounded-full border border-emerald-100/80" />
          <div className="mx-auto grid max-w-7xl gap-10 px-4 pb-12 pt-12 sm:px-6 md:grid-cols-[.9fr_1.1fr] md:items-center md:pb-16 md:pt-16 lg:px-8">
            <div className="relative z-10">
              <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 shadow-sm">
                <span className="h-2 w-2 rounded-full bg-emerald-500" /> Smarter job alerts. Better opportunities.
              </div>
              <h1 className="mt-5 max-w-xl text-[2.65rem] font-extrabold leading-[1.02] tracking-[-0.045em] text-slate-950 sm:text-[3.3rem]">
                Find the right jobs <span className="text-emerald-700">earlier.</span>
              </h1>
              <p className="mt-5 max-w-xl text-base leading-7 text-slate-600 sm:text-[17px]">
                Radar watches job sources for you, brings relevant opportunities into one clean workspace, and can send new matches straight to Telegram.
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <Link href={primaryHref} className="public-button-primary px-5 py-3">{user ? "Create a Job Alert" : "Get started for free"} <span aria-hidden="true">→</span></Link>
                <Link href="/#how-it-works" className="public-button-secondary px-5 py-3"><span className="grid h-5 w-5 place-items-center rounded-full border border-slate-300 text-[9px]">▶</span> How it works</Link>
              </div>
              <div className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-xs font-medium text-slate-500">
                {["Focused alerts", "Relevant matches", "Save and track"].map((item) => <span key={item} className="inline-flex items-center gap-1.5"><span className="grid h-4 w-4 place-items-center rounded-full border border-emerald-300 text-emerald-700"><Glyph name="check" className="h-2.5 w-2.5"/></span>{item}</span>)}
              </div>
            </div>

            <div className="relative z-10 md:pl-2 lg:pl-8">
              <DashboardPlaceholder />
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-4 pb-14 sm:px-6 lg:px-8">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {cards.map((card) => (
              <article key={card.title} className="group overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_8px_30px_rgba(15,45,36,0.05)] transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_14px_35px_rgba(15,45,36,0.08)]">
                <div className="flex items-center gap-2.5"><span className="grid h-9 w-9 place-items-center rounded-xl bg-emerald-50 text-emerald-700"><Glyph name={card.icon} className="h-5 w-5"/></span><h2 className="text-sm font-bold text-slate-900">{card.title}</h2></div>
                <p className="mt-3 max-w-[15rem] text-xs leading-5 text-slate-500">{card.text}</p>
                <FeatureVisual type={card.type}/>
              </article>
            ))}
          </div>
        </section>

        <section id="features" className="border-y border-emerald-100/70 bg-[linear-gradient(180deg,#f4fbf8_0%,#f8fbfa_100%)]">
          <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 md:py-16 lg:px-8">
            <div className="text-center">
              <p className="eyebrow">Everything in one place</p>
              <h2 className="mt-3 text-2xl font-extrabold tracking-[-0.025em] text-slate-950 sm:text-3xl">Everything you need to stay ahead.</h2>
              <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-slate-600">Radar keeps the job-search workflow understandable while the monitoring happens quietly in the background.</p>
            </div>
            <div className="mt-10 grid gap-x-5 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
              {features.map(([icon, title, text]) => (
                <article key={title} className="grid grid-cols-[44px_1fr] gap-4">
                  <span className="grid h-11 w-11 place-items-center rounded-2xl border border-emerald-100 bg-white text-emerald-700 shadow-sm"><Glyph name={icon} className="h-5 w-5"/></span>
                  <div><h3 className="text-sm font-bold text-slate-900">{title}</h3><p className="mt-1.5 text-xs leading-5 text-slate-500">{text}</p></div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="how-it-works" className="mx-auto max-w-7xl px-4 py-14 sm:px-6 md:py-16 lg:px-8">
          <div className="text-center"><p className="eyebrow">How it works</p><h2 className="mt-3 text-2xl font-extrabold tracking-[-0.025em] text-slate-950 sm:text-3xl">Set it once. Let Radar keep looking.</h2></div>
          <div className="relative mt-10 grid gap-5 md:grid-cols-3">
            <div className="pointer-events-none absolute left-[16%] right-[16%] top-7 hidden border-t border-dashed border-emerald-200 md:block" />
            {[
              ["1", "briefcase", "Set your preferences", "Tell Radar which job titles, locations, and work styles matter to you."],
              ["2", "radar", "Radar scans and matches", "Relevant openings are collected from company career sources and broader job feeds."],
              ["3", "telegram", "Get alerted and review", "Review new jobs in your workspace and optionally receive Telegram notifications."]
            ].map(([number, icon, title, text]) => (
              <article key={number} className="relative rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm">
                <span className="relative z-10 mx-auto grid h-14 w-14 place-items-center rounded-full border-4 border-white bg-emerald-700 text-white shadow-md"><Glyph name={icon as "briefcase" | "radar" | "telegram"} className="h-6 w-6"/></span>
                <span className="absolute right-4 top-4 grid h-7 w-7 place-items-center rounded-full bg-emerald-50 text-[11px] font-extrabold text-emerald-700">{number}</span>
                <h3 className="mt-5 text-sm font-bold text-slate-900">{title}</h3><p className="mx-auto mt-2 max-w-xs text-xs leading-5 text-slate-500">{text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-4 pb-16 sm:px-6 lg:px-8">
          <div className="relative overflow-hidden rounded-[24px] bg-[linear-gradient(120deg,#063b45_0%,#08765a_55%,#0aae72_100%)] px-6 py-8 text-white shadow-[0_20px_50px_rgba(5,85,65,0.18)] sm:flex sm:items-center sm:justify-between sm:gap-8 sm:px-9">
            <div className="pointer-events-none absolute -right-10 -top-28 h-72 w-72 rounded-full border border-white/10"/><div className="pointer-events-none absolute right-2 -top-16 h-52 w-52 rounded-full border border-white/10"/>
            <div className="relative z-10 flex items-start gap-4"><span className="mt-0.5 text-2xl text-emerald-200">✦</span><div><h2 className="text-xl font-extrabold">Better opportunities are out there.</h2><p className="mt-1 text-sm font-semibold text-emerald-100">Radar helps you find them earlier.</p></div></div>
            <Link href={primaryHref} className="relative z-10 mt-5 inline-flex rounded-xl bg-white px-5 py-3 text-sm font-bold text-emerald-900 shadow-sm transition hover:bg-emerald-50 sm:mt-0">{user ? "Open Job Alerts" : "Get started for free"} <span className="ml-2" aria-hidden="true">→</span></Link>
          </div>
        </section>
      </main>
      <PublicFooter />
    </div>
  );
}
