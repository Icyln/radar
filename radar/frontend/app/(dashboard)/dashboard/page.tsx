import Link from "next/link";
import { EmptyState } from "@/components/empty-state";
import { JobCard } from "@/components/job-card";
import { PageHeader } from "@/components/page-header";
import { formatDateTime } from "@/lib/format";
import { serverRequest } from "@/lib/server-api";
import type { DashboardSummary } from "@/types/api";

export default async function DashboardPage() {
  const data = await serverRequest<DashboardSummary>("/api/v1/dashboard/summary");
  const stats = [
    ["Active profiles", data.active_profiles],
    ["Registry companies", data.monitored_companies],
    ["Watched companies", data.watched_companies],
    ["Jobs discovered today", data.jobs_discovered_today],
    ["Matches today", data.matches_today],
    ["Alerts sent today", data.alerts_sent_today]
  ];
  return <><PageHeader eyebrow="Overview" title="Your job radar" description="A concise view of matching activity and monitoring health." action={<Link href="/profiles" className="button-primary">New profile</Link>} />
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">{stats.map(([label,value]) => <div key={label} className="panel p-4"><p className="text-xs text-zinc-500">{label}</p><p className="mt-2 text-2xl font-semibold tracking-tight text-zinc-50">{value}</p></div>)}</section>
    <section className="mt-6 panel p-5"><div className="flex items-center justify-between gap-4"><div><p className="text-xs text-zinc-500">Last successful crawler run</p><p className="mt-1 text-sm font-medium text-zinc-200">{formatDateTime(data.last_successful_crawler_run)}</p></div><span className="h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_15px_rgba(52,211,153,0.5)]" aria-label="Monitoring healthy" /></div></section>
    <section className="mt-8"><div className="mb-4 flex items-end justify-between"><div><h2 className="text-base font-semibold text-zinc-100">Recent matching jobs</h2><p className="mt-1 text-xs text-zinc-500">Newest jobs matched to any active profile.</p></div><Link href="/jobs" className="text-xs font-medium text-emerald-300 hover:text-emerald-200">View all →</Link></div>{data.recent_matching_jobs.length ? <div className="grid gap-4 xl:grid-cols-2">{data.recent_matching_jobs.map((job)=><JobCard key={job.id} job={job} compact />)}</div> : <EmptyState title="No matches yet" description="Create a monitoring profile, then Radar will surface matching ATS jobs here." action={<Link href="/profiles" className="button-primary">Create profile</Link>} />}</section>
  </>;
}
