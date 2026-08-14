import Link from "next/link";

export function Brand() {
  return (
    <Link href="/dashboard" className="inline-flex items-center gap-3" aria-label="Radar dashboard">
      <span className="grid h-9 w-9 place-items-center rounded-xl border border-emerald-400/30 bg-emerald-400/10 text-sm font-black text-emerald-300 shadow-[0_0_30px_rgba(52,211,153,0.08)]">
        R
      </span>
      <span>
        <span className="block text-sm font-semibold tracking-wide text-zinc-50">Radar</span>
        <span className="block text-[10px] uppercase tracking-[0.22em] text-zinc-500">Job intelligence</span>
      </span>
    </Link>
  );
}
