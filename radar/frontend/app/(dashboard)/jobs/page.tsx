import Link from "next/link";
import type { ReactNode } from "react";
import { EmptyState } from "@/components/empty-state";
import { JobCard } from "@/components/job-card";
import { PageHeader } from "@/components/page-header";
import { WideSearchRefresh } from "@/components/wide-search-refresh";
import { serverRequest } from "@/lib/server-api";
import type {
  ATSProvider,
  DetectedJobPage,
  JobListItem,
  JobStatus,
  WorkMode
} from "@/types/api";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;
const views = ["matched", "detected", "saved", "ignored"] as const;
const statuses: JobStatus[] = ["ACTIVE", "UNKNOWN", "CLOSED"];
const providers: ATSProvider[] = ["GREENHOUSE", "LEVER", "ASHBY"];
const workModes: WorkMode[] = ["REMOTE", "HYBRID", "ONSITE", "UNKNOWN"];
const pageSize = 24;

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function titleCase(value: string): string {
  return value[0].toUpperCase() + value.slice(1).toLowerCase();
}

export default async function JobsPage({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const requestedView = first(params.view);
  const requestedStatus = first(params.status);
  const view = views.includes(requestedView as (typeof views)[number]) ? requestedView! : "matched";
  const status = statuses.includes(requestedStatus as JobStatus) ? requestedStatus! as JobStatus : "ACTIVE";

  const tabHref = (nextView: string, nextStatus: string) => `/jobs?view=${nextView}&status=${nextStatus}`;
  let content: ReactNode;

  if (view === "detected") {
    const q = first(params.q) ?? "";
    const company = first(params.company) ?? "";
    const provider = providers.includes(first(params.provider) as ATSProvider) ? first(params.provider)! : "";
    const mode = workModes.includes(first(params.mode) as WorkMode) ? first(params.mode)! : "";
    const source = ["all", "watchlist", "wide", "direct"].includes(first(params.source) ?? "") ? first(params.source)! : "all";
    const freshness = ["any", "1", "3", "7", "14", "30", "60", "90", "unknown"].includes(first(params.freshness) ?? "") ? first(params.freshness)! : "30";
    const page = Math.max(1, Number.parseInt(first(params.page) ?? "1", 10) || 1);
    const offset = (page - 1) * pageSize;
    const query = new URLSearchParams({ status, source, limit: String(pageSize), offset: String(offset) });
    if (q.trim()) query.set("q", q.trim());
    if (company.trim()) query.set("company", company.trim());
    if (provider) query.set("provider", provider);
    if (mode) query.set("work_mode", mode);
    query.set("freshness", freshness);

    const result = await serverRequest<DetectedJobPage>(`/api/v1/jobs/detected?${query.toString()}`);

    function pageHref(nextPage: number) {
      const next = new URLSearchParams();
      next.set("view", "detected");
      next.set("status", status);
      next.set("page", String(nextPage));
      if (q.trim()) next.set("q", q.trim());
      if (company.trim()) next.set("company", company.trim());
      if (provider) next.set("provider", provider);
      if (mode) next.set("mode", mode);
      if (source !== "all") next.set("source", source);
      if (freshness !== "30") next.set("freshness", freshness);
      return `/jobs?${next.toString()}`;
    }

    const start = result.total === 0 ? 0 : result.offset + 1;
    const end = result.offset + result.items.length;
    content = <>
      <form method="get" action="/jobs" className="mb-5 panel p-4">
        <input type="hidden" name="view" value="detected" />
        <input type="hidden" name="status" value={status} />
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
          <label className="field-label">Search
            <input className="input mt-2" type="search" name="q" defaultValue={q} placeholder="Title or company" />
          </label>
          <label className="field-label">Company
            <input className="input mt-2" name="company" defaultValue={company} placeholder="Any company" />
          </label>
          <label className="field-label">Provider
            <select className="input mt-2" name="provider" defaultValue={provider}>
              <option value="">Any provider</option>
              {providers.map((item) => <option key={item} value={item}>{titleCase(item)}</option>)}
            </select>
          </label>
          <label className="field-label">Work mode
            <select className="input mt-2" name="mode" defaultValue={mode}>
              <option value="">Any mode</option>
              {workModes.map((item) => <option key={item} value={item}>{titleCase(item)}</option>)}
            </select>
          </label>
          <label className="field-label">Source scope
            <select className="input mt-2" name="source" defaultValue={source}>
              <option value="all">All jobs</option>
              <option value="watchlist">My watchlist</option>
              <option value="wide">Wide discovery</option>
              <option value="direct">Other direct ATS</option>
            </select>
          </label>
          <label className="field-label">Freshness
            <select className="input mt-2" name="freshness" defaultValue={freshness}>
              <option value="1">Last 24 hours</option>
              <option value="3">Last 3 days</option>
              <option value="7">Last 7 days</option>
              <option value="14">Last 14 days</option>
              <option value="30">Last 30 days</option>
              <option value="60">Last 60 days</option>
              <option value="90">Last 90 days</option>
              <option value="unknown">Posting date unknown</option>
              <option value="any">Any time</option>
            </select>
          </label>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button className="button-primary" type="submit">Apply filters</button>
          <Link className="button-ghost" href={`/jobs?view=detected&status=${status}`}>Clear</Link>
          <span className="text-xs text-zinc-500">{result.total} detected · showing {start}–{end}</span>
        </div>
      </form>
      {result.items.length ? <>
        <div className="grid gap-4 xl:grid-cols-2">{result.items.map((job) => <JobCard key={job.id} job={job} compact />)}</div>
        <div className="mt-6 flex items-center justify-between gap-4 border-t border-zinc-800 pt-5">
          <Link aria-disabled={page <= 1} className={page <= 1 ? "button-secondary pointer-events-none opacity-40" : "button-secondary"} href={pageHref(page - 1)}>← Previous</Link>
          <span className="text-xs text-zinc-500">Page {page}</span>
          <Link aria-disabled={!result.has_more} className={!result.has_more ? "button-secondary pointer-events-none opacity-40" : "button-secondary"} href={pageHref(page + 1)}>Next →</Link>
        </div>
      </> : <EmptyState title={`No detected ${status.toLowerCase()} jobs`} description="No collected jobs match these filters. Detected shows everything Radar collected, including Wide discovery jobs from employers that are not yet in the registry." />}
    </>;
  } else {
    const jobs = await serverRequest<JobListItem[]>(`/api/v1/jobs?view=${view}&status=${status}&limit=100`);
    content = jobs.length
      ? <div className="grid gap-4 xl:grid-cols-2">{jobs.map((job) => <JobCard key={job.id} job={job} />)}</div>
      : <EmptyState title={`No ${view} ${status.toLowerCase()} jobs`} description="Matched is profile-driven and now includes Wide discovery jobs outside the registry. Saved and Ignored are your personal job states." />;
  }

  return <>
    <PageHeader eyebrow="History" title="Jobs" description="Wide Search can surface fresh jobs before Radar knows the employer's direct ATS. Direct ATS jobs remain verified monitoring sources." />
    <WideSearchRefresh />
    <div className="mb-5 flex flex-col gap-3 rounded-xl border border-zinc-800 bg-zinc-950/50 p-2 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-wrap gap-1">{views.map((item) => <Link key={item} href={tabHref(item, status)} className={item === view ? "tab-active" : "tab"}>{item[0].toUpperCase() + item.slice(1)}</Link>)}</div>
      <div className="flex flex-wrap gap-1">{statuses.map((item) => <Link key={item} href={tabHref(view, item)} className={item === status ? "tab-active" : "tab"}>{titleCase(item)}</Link>)}</div>
    </div>
    {content}
  </>;
}
