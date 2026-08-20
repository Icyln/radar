import Link from "next/link";
import { EmptyState } from "@/components/empty-state";
import { JobCard } from "@/components/job-card";
import { PageHeader } from "@/components/page-header";
import { serverRequest } from "@/lib/server-api";
import type { DashboardSummary } from "@/types/api";

export default async function DashboardPage() {
  const data = await serverRequest<DashboardSummary>("/api/v1/dashboard/summary");
  const stats = [
    ["Active job alerts", data.active_profiles, "Your searches currently running"],
    ["New matches today", data.matches_today, "Jobs matched to your alerts"],
    ["Jobs found today", data.jobs_discovered_today, "New roles Radar found for you"],
    ["Telegram alerts sent", data.alerts_sent_today, "Matching jobs delivered today"]
  ] as const;

  return <>
    <PageHeader
      eyebrow="Home"
      title="Your job radar"
      description="See what is new, then jump straight into the jobs worth reviewing."
      action={<Link href="/profiles" className="button-primary">Create Job Alert</Link>}
    />

    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {stats.map(([label, value, helper]) => <div key={label} className="panel p-4"><p className="text-xs font-medium text-soft">{label}</p><p className="mt-2 text-2xl font-semibold tracking-tight text-main">{value}</p><p className="mt-1 text-[11px] leading-5 text-faint">{helper}</p></div>)}
    </section>

    <section className="mt-8">
      <div className="mb-4 flex items-end justify-between gap-4">
        <div><h2 className="text-base font-semibold text-main">Recent matches</h2><p className="mt-1 text-xs text-soft">The newest jobs that fit one of your active alerts.</p></div>
        <Link href="/jobs" className="text-xs font-semibold text-accent">View all jobs</Link>
      </div>
      {data.recent_matching_jobs.length ? <div className="grid gap-4 xl:grid-cols-2">{data.recent_matching_jobs.map((job) => <JobCard key={job.id} job={job} compact />)}</div> : <EmptyState title="No matches yet" description="Create a Job Alert and Radar will start organizing matching roles here." action={<Link href="/profiles" className="button-primary">Create Job Alert</Link>} />}
    </section>

    <section className="mt-6 grid gap-4 md:grid-cols-2">
      <div className="panel-soft p-5"><h2 className="text-sm font-semibold text-main">Want to focus on specific companies?</h2><p className="mt-2 text-sm leading-6 text-soft">Follow companies you care about, or request a company that Radar does not know yet.</p><Link href="/companies" className="button-secondary mt-4">Manage companies</Link></div>
      <div className="panel-soft p-5"><h2 className="text-sm font-semibold text-main">Want alerts in Telegram?</h2><p className="mt-2 text-sm leading-6 text-soft">Connect Telegram once and Radar can send new matching jobs directly to your chat.</p><Link href="/settings" className="button-secondary mt-4">Open settings</Link></div>
    </section>
  </>;
}
