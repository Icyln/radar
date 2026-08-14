import Link from "next/link";
import { EmptyState } from "@/components/empty-state";
import { JobCard } from "@/components/job-card";
import { PageHeader } from "@/components/page-header";
import { serverRequest } from "@/lib/server-api";
import type { JobListItem, JobStatus } from "@/types/api";

type Params = Promise<{ view?: string; status?: string }>;
const views = ["matched", "saved", "ignored"] as const;
const statuses: JobStatus[] = ["ACTIVE", "UNKNOWN", "CLOSED"];

export default async function JobsPage({ searchParams }: { searchParams: Params }) {
  const params = await searchParams;
  const view = views.includes(params.view as (typeof views)[number]) ? params.view! : "matched";
  const status = statuses.includes(params.status as JobStatus) ? params.status! : "ACTIVE";
  const jobs = await serverRequest<JobListItem[]>(`/api/v1/jobs?view=${view}&status=${status}&limit=100`);

  const href = (nextView: string, nextStatus: string) => `/jobs?view=${nextView}&status=${nextStatus}`;
  return <><PageHeader eyebrow="History" title="Jobs" description="Review matched jobs, your saved shortlist, ignored roles, and lifecycle state." />
    <div className="mb-5 flex flex-col gap-3 rounded-xl border border-zinc-800 bg-zinc-950/50 p-2 sm:flex-row sm:items-center sm:justify-between"><div className="flex flex-wrap gap-1">{views.map((item)=><Link key={item} href={href(item,status)} className={item===view ? "tab-active" : "tab"}>{item[0].toUpperCase()+item.slice(1)}</Link>)}</div><div className="flex flex-wrap gap-1">{statuses.map((item)=><Link key={item} href={href(view,item)} className={item===status ? "tab-active" : "tab"}>{item[0]+item.slice(1).toLowerCase()}</Link>)}</div></div>
    {jobs.length ? <div className="grid gap-4 xl:grid-cols-2">{jobs.map((job)=><JobCard key={job.id} job={job} />)}</div> : <EmptyState title={`No ${view} ${status.toLowerCase()} jobs`} description="This view contains only jobs matched to your Radar account (or saved/ignored from those matches). If it is empty, verify the production database has active jobs and that an enabled profile actually matches them." />}
  </>;
}
