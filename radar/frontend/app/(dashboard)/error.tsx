"use client";

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <div className="panel p-6"><p className="eyebrow text-danger">Request failed</p><h1 className="mt-2 text-xl font-semibold text-main">Radar could not load this page.</h1><p className="mt-2 text-sm text-soft">{error.message || "The service may be temporarily unavailable."}</p><button className="button-primary mt-5" onClick={reset}>Try again</button></div>;
}
