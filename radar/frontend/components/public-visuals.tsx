import Image from "next/image";

function Glyph({ name, className = "h-5 w-5" }: { name: "briefcase" | "telegram" | "building" | "bookmark" | "radar" | "bell" | "search" | "shield" | "spark" | "check" | "globe" | "list"; className?: string }) {
  const common = { fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      {name === "briefcase" ? <><path {...common} d="M9 7V5.8A1.8 1.8 0 0 1 10.8 4h2.4A1.8 1.8 0 0 1 15 5.8V7"/><rect {...common} x="3" y="7" width="18" height="12" rx="2.5"/><path {...common} d="M3 11.5c5.4 2.2 12.6 2.2 18 0M10 12h4"/></> : null}
      {name === "telegram" ? <><path {...common} d="m21 4-7.4 16-3.7-6.1L4 10.7 21 4Z"/><path {...common} d="m9.9 13.9 4.3-4.1"/></> : null}
      {name === "building" ? <><path {...common} d="M5 20V7l7-3v16M12 9h7v11M8 9h1M8 12h1M8 15h1M15 12h1M15 15h1M3 20h18"/></> : null}
      {name === "bookmark" ? <path {...common} d="M6.5 4.5A1.5 1.5 0 0 1 8 3h8a1.5 1.5 0 0 1 1.5 1.5V21L12 17.5 6.5 21V4.5Z"/> : null}
      {name === "radar" ? <><circle {...common} cx="12" cy="12" r="8.5"/><circle {...common} cx="12" cy="12" r="4.7"/><path {...common} d="M12 12 18.8 6.3M12 3.5v1M20.5 12h-1M12 20.5v-1M3.5 12h1"/><circle cx="12" cy="12" r="1.35" fill="currentColor"/></> : null}
      {name === "bell" ? <><path {...common} d="M6.5 10.5a5.5 5.5 0 0 1 11 0c0 4 1.7 4.8 1.7 4.8H4.8s1.7-.8 1.7-4.8Z"/><path {...common} d="M10 18h4"/></> : null}
      {name === "search" ? <><circle {...common} cx="10.5" cy="10.5" r="6.2"/><path {...common} d="m15 15 5 5"/></> : null}
      {name === "shield" ? <><path {...common} d="M12 3 19 6v5.3c0 4.5-3 7.4-7 9.7-4-2.3-7-5.2-7-9.7V6l7-3Z"/><path {...common} d="m9 12 2 2 4-4"/></> : null}
      {name === "spark" ? <path {...common} d="M12 2.8 13.7 9l6.1 1.7-6.1 1.7L12 18.6l-1.7-6.2-6.1-1.7L10.3 9 12 2.8Z"/> : null}
      {name === "check" ? <path {...common} d="m5 12.5 4 4 10-10"/> : null}
      {name === "globe" ? <><circle {...common} cx="12" cy="12" r="9"/><path {...common} d="M3 12h18M12 3c2.2 2.5 3.3 5.5 3.3 9S14.2 18.5 12 21M12 3C9.8 5.5 8.7 8.5 8.7 12s1.1 6.5 3.3 9"/></> : null}
      {name === "list" ? <><path {...common} d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1" fill="currentColor"/><circle cx="4.5" cy="12" r="1" fill="currentColor"/><circle cx="4.5" cy="18" r="1" fill="currentColor"/></> : null}
    </svg>
  );
}

export function DashboardPlaceholder() {
  return (
    <div className="relative overflow-hidden rounded-[22px] border border-slate-200 bg-white shadow-[0_28px_75px_rgba(15,45,36,0.14)]">
      <div className="flex h-10 items-center gap-1.5 border-b border-slate-100 px-4">
        <span className="h-2.5 w-2.5 rounded-full bg-rose-400"/><span className="h-2.5 w-2.5 rounded-full bg-amber-400"/><span className="h-2.5 w-2.5 rounded-full bg-emerald-400"/>
      </div>
      <div className="grid min-h-[330px] grid-cols-[112px_1fr] sm:min-h-[390px] sm:grid-cols-[142px_1fr]">
        <div className="border-r border-slate-100 bg-slate-50/80 p-3 sm:p-4">
          <div className="mb-5 flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700"><Glyph name="radar" className="h-5 w-5"/></div>
          {['Home','Jobs','Alerts','Saved','Companies'].map((item, index) => <div key={item} className={`mb-2 h-7 rounded-lg ${index === 0 ? 'bg-emerald-50' : 'bg-white'} px-2 py-2`}><div className={`h-2 rounded-full ${index === 0 ? 'bg-emerald-200' : 'bg-slate-200'}`} style={{width: `${56 + index * 5}%`}}/></div>)}
        </div>
        <div className="relative flex items-center justify-center overflow-hidden bg-[linear-gradient(145deg,#ffffff_0%,#f7fbf9_100%)] p-5">
          <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full border border-emerald-100"/>
          <div className="absolute -right-8 -top-8 h-32 w-32 rounded-full border border-emerald-100"/>
          {/* Replace this placeholder with a real dashboard screenshot when the asset is ready. */}
          <div className="relative z-10 h-[280px] w-full overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <Image
              src="/dashboard.png"
              alt="Radar dashboard preview"
              fill
              className="object-cover"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export function FeatureVisual({ type }: { type: "matches" | "telegram" | "companies" | "saved" }) {
  if (type === "matches") return <div className="relative h-28"><div className="absolute right-1 top-1 w-32 rounded-xl border border-slate-200 bg-white p-3 shadow-sm"><div className="flex items-center justify-between"><span className="h-3 w-14 rounded bg-slate-200"/><span className="text-amber-400">★</span></div><div className="mt-3 h-2 w-full rounded bg-slate-100"/><div className="mt-2 h-2 w-4/5 rounded bg-slate-100"/><div className="mt-3 inline-flex rounded-full bg-emerald-100 px-2 py-1 text-[9px] font-bold text-emerald-700">98% match</div></div></div>;
  if (type === "telegram") return <div className="relative h-28"><div className="absolute right-1 top-0 w-36 rounded-2xl border border-sky-100 bg-white p-3 shadow-sm"><div className="flex items-center gap-2 text-[10px] font-bold text-slate-700"><span className="grid h-6 w-6 place-items-center rounded-full bg-sky-500 text-white"><Glyph name="telegram" className="h-3.5 w-3.5"/></span>Radar</div><p className="mt-2 text-[10px] font-semibold text-slate-800">New job match</p><p className="mt-1 text-[9px] text-slate-500">Product Designer · Acme</p><span className="mt-2 inline-flex rounded-lg bg-sky-50 px-2 py-1 text-[9px] font-semibold text-sky-700">View job →</span></div></div>;
  if (type === "companies") return <div className="relative h-28"><div className="absolute right-1 top-1 w-32 space-y-2 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">{[1,2,3].map((n)=><div key={n} className="flex items-center gap-2"><span className="grid h-6 w-6 place-items-center rounded-md bg-emerald-50 text-emerald-700"><Glyph name="building" className="h-3.5 w-3.5"/></span><span className="h-2 flex-1 rounded bg-slate-100"/><span className="h-2 w-2 rounded-full bg-emerald-400"/></div>)}</div></div>;
  return <div className="relative h-28"><div className="absolute right-1 top-1 w-32 rounded-xl border border-slate-200 bg-white p-3 shadow-sm"><div className="flex items-start justify-between"><div><div className="h-2 w-20 rounded bg-slate-200"/><div className="mt-2 h-2 w-14 rounded bg-slate-100"/></div><span className="text-emerald-600"><Glyph name="bookmark" className="h-4 w-4"/></span></div><div className="mt-5 h-2 w-full rounded bg-slate-100"/><div className="mt-2 h-2 w-3/4 rounded bg-slate-100"/></div></div>;
}

export function RadarHeroIllustration() {
  return (
    <div className="relative mx-auto h-[285px] w-full max-w-lg">
      <div className="absolute left-5 top-12 h-48 w-[78%] rounded-[28px] border border-slate-200 bg-white shadow-[0_22px_55px_rgba(15,45,36,0.12)] sm:left-10">
        <div className="flex h-11 items-center gap-3 border-b border-slate-100 px-4"><Glyph name="search" className="h-4 w-4 text-slate-500"/><div className="h-2.5 w-2/3 rounded-full bg-slate-100"/></div>
        <div className="space-y-3 p-4">{[0,1,2].map((n)=><div key={n} className="flex items-center gap-3"><span className={`h-3 w-3 rounded-full ${n===0?'bg-sky-400':n===1?'bg-emerald-400':'bg-amber-400'}`}/><div className="h-2.5 flex-1 rounded-full bg-slate-100"/><div className="h-2.5 w-12 rounded-full bg-emerald-100"/></div>)}</div>
      </div>
      <div className="absolute right-3 top-4 grid h-44 w-44 place-items-center rounded-full bg-[radial-gradient(circle_at_center,#ecfdf5_0_38%,#d1fae5_39%_40%,#f0fdfa_41%_59%,#a7f3d0_60%_61%,#ecfdf5_62%_100%)] shadow-[0_18px_45px_rgba(5,150,105,0.16)]">
        <div className="absolute inset-5 rounded-full border border-emerald-300"/><div className="absolute inset-12 rounded-full border border-emerald-300"/><div className="absolute left-1/2 top-1/2 h-1/2 w-[2px] origin-top -rotate-45 bg-gradient-to-b from-emerald-600 to-transparent"/><span className="h-3 w-3 rounded-full bg-emerald-600 shadow-[0_0_0_6px_rgba(16,185,129,0.12)]"/>
      </div>
      <div className="absolute bottom-1 right-10 grid h-16 w-16 place-items-center rounded-2xl border border-slate-200 bg-white text-emerald-600 shadow-lg"><Glyph name="bell" className="h-7 w-7"/></div>
      <div className="absolute bottom-4 left-1 rounded-2xl bg-emerald-950 px-4 py-3 text-white shadow-lg"><p className="text-[10px] font-semibold text-emerald-200">Radar found a match</p><p className="mt-1 text-xs font-bold">Frontend Engineer</p></div>
    </div>
  );
}

export function StepArt({ step }: { step: 1 | 2 | 3 | 4 | 5 }) {
  if (step === 1) return <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm"><div className="grid gap-2">{['Job title','Location','Work style'].map((v,i)=><div key={v}><span className="text-[8px] font-semibold text-slate-400">{v}</span><div className={`mt-1 h-7 rounded-lg border border-slate-200 ${i===0?'bg-emerald-50':'bg-slate-50'}`}/></div>)}</div></div>;
  if (step === 2) return <div className="relative grid h-36 place-items-center"><div className="grid h-28 w-28 place-items-center rounded-full bg-gradient-to-br from-sky-100 via-emerald-100 to-emerald-200 text-emerald-800"><Glyph name="globe" className="h-14 w-14"/></div><span className="absolute bottom-1 left-3 grid h-10 w-10 place-items-center rounded-xl bg-white text-emerald-700 shadow"><Glyph name="briefcase"/></span><span className="absolute right-3 top-2 grid h-10 w-10 place-items-center rounded-xl bg-white text-slate-700 shadow"><Glyph name="search"/></span></div>;
  if (step === 3) return <div className="space-y-2 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">{['Stripe','Notion','Linear'].map((v)=><div key={v} className="flex items-center gap-2"><span className="grid h-7 w-7 place-items-center rounded-lg bg-slate-100 text-slate-500"><Glyph name="building" className="h-4 w-4"/></span><span className="text-[10px] font-semibold text-slate-700">{v}</span><span className="ml-auto rounded-full bg-emerald-50 px-2 py-1 text-[8px] font-bold text-emerald-700">Following</span></div>)}</div>;
  if (step === 4) return <div className="mx-auto max-w-[190px] rounded-2xl border border-sky-100 bg-white p-4 shadow-sm"><div className="flex items-center gap-2"><span className="grid h-8 w-8 place-items-center rounded-full bg-sky-500 text-white"><Glyph name="telegram" className="h-4 w-4"/></span><p className="text-[10px] font-bold text-slate-700">Radar</p></div><p className="mt-3 text-[10px] font-bold text-slate-800">New match found!</p><p className="mt-1 text-[9px] leading-4 text-slate-500">Senior Product Manager at Stripe</p><div className="mt-3 rounded-lg bg-sky-50 py-2 text-center text-[9px] font-bold text-sky-700">View job</div></div>;
  return <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-[10px] font-bold text-slate-800">Senior Product Manager</p><p className="mt-1 text-[9px] text-slate-500">Example Company · Remote</p><div className="mt-4 h-2 rounded bg-slate-100"/><div className="mt-2 h-2 w-3/4 rounded bg-slate-100"/><div className="mt-4 flex gap-2"><span className="grid h-8 w-8 place-items-center rounded-lg bg-emerald-50 text-emerald-700"><Glyph name="bookmark" className="h-4 w-4"/></span><span className="grid h-8 w-8 place-items-center rounded-lg bg-slate-100 text-slate-600"><Glyph name="check" className="h-4 w-4"/></span></div></div>;
}

export { Glyph };
