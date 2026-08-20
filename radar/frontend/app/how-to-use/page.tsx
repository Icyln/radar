import Link from "next/link";
import { PublicFooter } from "@/components/public-footer";
import { PublicHeader } from "@/components/public-header";
import { Glyph, RadarHeroIllustration, StepArt } from "@/components/public-visuals";
import { getCurrentUser } from "@/lib/server-api";

const workflow = [
  ["1", "search", "Set alert", "Create a focused job alert."],
  ["2", "globe", "Search", "Radar looks across job sources."],
  ["3", "building", "Follow", "Track companies you care about."],
  ["4", "telegram", "Get alerts", "Connect Telegram for notifications."],
  ["5", "list", "Review", "Save, review, or hide jobs."]
] as const;

const guide = [
  [1, "Create your Job Alert", "Add the job titles, locations, work style, and freshness that matter most. Radar searches broadly by default."],
  [2, "Choose where to search", "Keep broad searching enabled for wider coverage, or limit an alert to companies you already follow."],
  [3, "Follow companies you care about", "Use Companies to follow employers you want to watch more closely. You can also request a company that is missing."],
  [4, "Connect Telegram for alerts", "Open Settings, connect your Telegram account, and send a test message. New matching jobs can then arrive in your chat."],
  [5, "Review, save, or hide jobs", "Use Jobs to review matches, save promising roles, and hide opportunities that are not right for you."]
] as const;

export default async function HowToUsePage() {
  const user = await getCurrentUser();
  const primaryHref = user ? "/profiles" : "/register";

  return (
    <div className="public-shell">
      <PublicHeader signedIn={Boolean(user)} />
      <main>
        <section className="mx-auto grid max-w-7xl gap-10 px-4 pb-12 pt-12 sm:px-6 md:grid-cols-[.9fr_1.1fr] md:items-center md:pb-16 md:pt-16 lg:px-8">
          <div>
            <span className="inline-flex rounded-full bg-emerald-50 px-3 py-1.5 text-[10px] font-extrabold uppercase tracking-[0.16em] text-emerald-700">Get started</span>
            <h1 className="mt-5 text-[2.45rem] font-extrabold leading-[1.04] tracking-[-0.04em] text-slate-950 sm:text-5xl">How to Use Radar</h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-slate-600">Set up what you want once, let Radar keep checking, and review the opportunities that actually deserve your attention.</p>
            <div className="mt-7"><Link href={primaryHref} className="public-button-primary px-5 py-3">{user ? "Create a Job Alert" : "Get started"} <span aria-hidden="true">→</span></Link></div>
          </div>
          <RadarHeroIllustration />
        </section>

        <section className="mx-auto max-w-7xl px-4 pb-14 sm:px-6 lg:px-8">
          <div className="rounded-[24px] border border-slate-200 bg-white p-5 shadow-[0_10px_35px_rgba(15,45,36,0.05)] sm:p-7">
            <div className="flex items-center justify-center gap-3"><span className="h-px w-10 bg-emerald-200"/><h2 className="text-sm font-extrabold text-slate-900">The Radar workflow</h2><span className="h-px w-10 bg-emerald-200"/></div>
            <div className="mt-7 grid gap-5 sm:grid-cols-2 lg:grid-cols-5">
              {workflow.map(([number, icon, title, text], index) => (
                <div key={number} className="relative text-center">
                  {index < workflow.length - 1 ? <span className="absolute left-[62%] top-7 hidden w-[76%] border-t border-dashed border-emerald-200 lg:block"/> : null}
                  <span className="relative z-10 mx-auto grid h-14 w-14 place-items-center rounded-full border border-slate-200 bg-white text-emerald-700 shadow-sm"><Glyph name={icon} className="h-6 w-6"/></span>
                  <h3 className="mt-4 text-xs font-extrabold text-slate-900">{number}. {title}</h3><p className="mx-auto mt-1.5 max-w-[11rem] text-[11px] leading-5 text-slate-500">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-4 pb-14 sm:px-6 lg:px-8">
          <div className="text-center"><p className="eyebrow">Step-by-step guide</p><h2 className="mt-3 text-2xl font-extrabold tracking-[-0.025em] text-slate-950 sm:text-3xl">A clear path from setup to application.</h2></div>
          <div className="mt-9 grid gap-5 md:grid-cols-2 xl:grid-cols-5">
            {guide.map(([number, title, text]) => (
              <article key={number} className="flex min-h-full flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_8px_28px_rgba(15,45,36,0.05)]">
                <span className="grid h-7 w-7 place-items-center rounded-full bg-emerald-700 text-[10px] font-extrabold text-white">{number}</span>
                <h3 className="mt-4 min-h-[42px] text-sm font-extrabold leading-5 text-slate-900">{title}</h3>
                <div className="my-5 min-h-[150px]"><StepArt step={number as 1|2|3|4|5}/></div>
                <p className="mt-auto text-xs leading-5 text-slate-500">{text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-4 pb-14 sm:px-6 lg:px-8">
          <div className="grid gap-7 overflow-hidden rounded-[24px] border border-emerald-100 bg-[linear-gradient(110deg,#effcf7_0%,#f8fcfb_100%)] p-6 md:grid-cols-[.85fr_1.15fr] md:items-center md:p-9">
            <div className="relative mx-auto grid h-52 w-full max-w-sm place-items-center">
              <div className="absolute h-40 w-40 rounded-full border border-emerald-200"/><div className="absolute h-28 w-28 rounded-full border border-emerald-200"/><div className="absolute h-16 w-16 rounded-full border border-emerald-200"/>
              <div className="relative grid h-24 w-24 place-items-center rounded-full bg-emerald-700 text-white shadow-xl"><Glyph name="radar" className="h-11 w-11"/></div>
              <span className="absolute left-12 top-4 text-xl text-emerald-500">✦</span><span className="absolute bottom-8 right-10 text-sm text-sky-400">✦</span>
            </div>
            <div>
              <h2 className="text-xl font-extrabold text-slate-950 sm:text-2xl">Radar keeps working after you leave the page.</h2>
              <p className="mt-3 text-sm leading-6 text-slate-600">Your alert settings stay in place while scheduled monitoring continues. When a matching job appears, it is ready in your workspace and can be delivered to Telegram.</p>
              <div className="mt-6 grid gap-4 sm:grid-cols-3">
                {[["radar","Ongoing scanning","Scheduled checks continue in the background."],["search","Focused matching","Your alert settings keep the results relevant."],["shield","Private workspace","Your account and saved job activity stay yours."]].map(([icon,title,text])=><div key={title} className="grid grid-cols-[36px_1fr] gap-3"><span className="grid h-9 w-9 place-items-center rounded-xl bg-white text-emerald-700 shadow-sm"><Glyph name={icon as "radar"|"search"|"shield"} className="h-4 w-4"/></span><div><p className="text-xs font-bold text-slate-900">{title}</p><p className="mt-1 text-[10px] leading-4 text-slate-500">{text}</p></div></div>)}
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-4 pb-16 text-center sm:px-6 lg:px-8">
          <h2 className="text-lg font-extrabold text-slate-950">Ready to get started?</h2><p className="mt-2 text-sm text-slate-500">Create your first focused alert in a couple of minutes.</p>
          <Link href={primaryHref} className="public-button-primary mt-5 px-5 py-3">{user ? "Open Job Alerts" : "Get started for free"} <span aria-hidden="true">→</span></Link>
        </section>
      </main>
      <PublicFooter />
    </div>
  );
}
