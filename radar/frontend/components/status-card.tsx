type StatusCardProps = {
  title: string;
  status: "Ready" | "Phase 1" | "Later phase";
  description: string;
};

export function StatusCard({ title, status, description }: StatusCardProps) {
  return (
    <article className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-5 shadow-sm">
      <div className="flex items-center justify-between gap-4">
        <h2 className="font-semibold text-zinc-100">{title}</h2>
        <span className="rounded-full border border-zinc-700 px-2.5 py-1 text-xs text-zinc-300">
          {status}
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-zinc-400">{description}</p>
    </article>
  );
}
