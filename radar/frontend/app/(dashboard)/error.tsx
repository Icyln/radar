"use client";

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <div className="panel p-6"><p className="eyebrow text-rose-400">Request failed</p><h1 className="mt-2 text-xl font-semibold text-zinc-100">Radar could not load this page.</h1><p className="mt-2 text-sm text-zinc-500">{error.message || "The backend may be waking up or temporarily unavailable."}</p><button className="button-primary mt-5" onClick={reset}>Try again</button></div>;
}
