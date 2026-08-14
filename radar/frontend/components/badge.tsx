export function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "success" | "warning" | "danger" | "info" }) {
  const tones = {
    neutral: "border-zinc-700 bg-zinc-800/60 text-zinc-300",
    success: "border-emerald-800/80 bg-emerald-950/60 text-emerald-300",
    warning: "border-amber-800/80 bg-amber-950/50 text-amber-300",
    danger: "border-rose-900/80 bg-rose-950/50 text-rose-300",
    info: "border-sky-900/80 bg-sky-950/50 text-sky-300"
  };
  return <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${tones[tone]}`}>{children}</span>;
}
