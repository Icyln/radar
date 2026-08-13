import { StatusCard } from "@/components/status-card";

const capabilities = [
  {
    title: "Backend foundation",
    status: "Ready" as const,
    description: "FastAPI, configuration, PostgreSQL/SQLAlchemy, Alembic, health routes, and test tooling."
  },
  {
    title: "Greenhouse detection",
    status: "Phase 1" as const,
    description: "Greenhouse collection, normalization, repeat-safe persistence, lifecycle handling, and crawler logs."
  },
  {
    title: "Telegram delivery",
    status: "Phase 1" as const,
    description: "Persisted notification claims and basic Telegram alerts for configured Phase-1 test targets."
  },
  {
    title: "User dashboard",
    status: "Later phase" as const,
    description: "Authentication, job profiles, saved/ignored state, and the full operational dashboard begin in Phases 2–4."
  }
];

export default function Home() {
  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-14 lg:px-8">
      <header className="max-w-3xl">
        <div className="mb-5 inline-flex rounded-full border border-zinc-800 bg-zinc-950 px-3 py-1 text-xs font-medium uppercase tracking-[0.18em] text-zinc-400">
          Radar · Foundation
        </div>
        <h1 className="text-4xl font-semibold tracking-tight text-zinc-50 sm:text-5xl">
          Detect relevant jobs early.
        </h1>
        <p className="mt-5 max-w-2xl text-base leading-7 text-zinc-400 sm:text-lg">
          Radar is a personal early-warning system for jobs published directly through company ATS systems. This build contains the production foundation and minimum Greenhouse detection pipeline.
        </p>
      </header>

      <section className="mt-12 grid gap-4 md:grid-cols-2" aria-label="Implementation status">
        {capabilities.map((capability) => (
          <StatusCard key={capability.title} {...capability} />
        ))}
      </section>

      <section className="mt-12 rounded-2xl border border-zinc-800 bg-zinc-950/60 p-6">
        <h2 className="text-lg font-semibold">Critical path</h2>
        <p className="mt-3 font-mono text-sm leading-7 text-zinc-400">
          Greenhouse → normalization → identity → lifecycle → PostgreSQL → persisted Telegram notification
        </p>
      </section>
    </main>
  );
}
