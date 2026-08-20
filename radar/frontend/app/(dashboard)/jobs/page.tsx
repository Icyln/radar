import Link from "next/link";
import type { ReactNode } from "react";
import { EmptyState } from "@/components/empty-state";
import { JobCard } from "@/components/job-card";
import { PageHeader } from "@/components/page-header";
import { WideSearchRefresh } from "@/components/wide-search-refresh";
import { serverRequest } from "@/lib/server-api";
import type { ATSProvider, DetectedJobPage, JobListItem, JobStatus, WorkMode } from "@/types/api";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;
const views = ["matched", "detected", "saved", "ignored"] as const;
const viewLabels = { matched: "For You", detected: "All Jobs", saved: "Saved", ignored: "Hidden" } as const;
const statuses: JobStatus[] = ["ACTIVE", "UNKNOWN", "CLOSED"];
const statusLabels: Record<JobStatus, string> = { ACTIVE: "Open", UNKNOWN: "Unclear", CLOSED: "Closed" };
const providers: ATSProvider[] = ["GREENHOUSE", "LEVER", "ASHBY"];
const workModes: WorkMode[] = ["REMOTE", "HYBRID", "ONSITE", "UNKNOWN"];
const pageSize = 24;

function first(value: string | string[] | undefined): string | undefined { return Array.isArray(value) ? value[0] : value; }
function titleCase(value: string): string { return value[0].toUpperCase() + value.slice(1).toLowerCase(); }

export default async function JobsPage({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const requestedView = first(params.view);
  const requestedStatus = first(params.status);
  const view = views.includes(requestedView as (typeof views)[number]) ? requestedView! as (typeof views)[number] : "matched";
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
    const query = new URLSearchParams({ status, source, limit: String(pageSize), offset: String(offset), freshness });
    if (q.trim()) query.set("q", q.trim());
    if (company.trim()) query.set("company", company.trim());
    if (provider) query.set("provider", provider);
    if (mode) query.set("work_mode", mode);
    const result = await serverRequest<DetectedJobPage>(`/api/v1/jobs/detected?${query.toString()}`);

    function pageHref(nextPage: number) {
      const next = new URLSearchParams({ view: "detected", status, page: String(nextPage), freshness });
      if (q.trim()) next.set("q", q.trim());
      if (company.trim()) next.set("company", company.trim());
      if (provider) next.set("provider", provider);
      if (mode) next.set("mode", mode);
      if (source !== "all") next.set("source", source);
      return `/jobs?${next.toString()}`;
    }

    const start = result.total === 0 ? 0 : result.offset + 1;
    const end = result.offset + result.items.length;
    content = <>
      <form method="get" action="/jobs" className="mb-5 panel p-4">
        <input type="hidden" name="view" value="detected" />
        <input type="hidden" name="status" value={status} />
        <div className="grid gap-3 md:grid-cols-3">
          <label className="field-label">Keyword<input className="input mt-2" type="search" name="q" defaultValue={q} placeholder="Job title or company" /></label>
          <label className="field-label">Work style<select className="input mt-2" name="mode" defaultValue={mode}><option value="">Any</option><option value="REMOTE">Remote</option><option value="HYBRID">Hybrid</option><option value="ONSITE">On-site</option></select></label>
          <label className="field-label">Posted within<select className="input mt-2" name="freshness" defaultValue={freshness}><option value="1">Last 24 hours</option><option value="3">Last 3 days</option><option value="7">Last 7 days</option><option value="14">Last 14 days</option><option value="30">Last 30 days</option><option value="60">Last 60 days</option><option value="90">Last 90 days</option><option value="any">Any time</option><option value="unknown">Date not available</option></select></label>
        </div>
        <details className="mt-4 rounded-xl border border-ui surface-soft p-3">
          <summary className="cursor-pointer text-xs font-semibold text-soft">More filters</summary>
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            <label className="field-label">Company<input className="input mt-2" name="company" defaultValue={company} placeholder="Any company" /></label>
            <label className="field-label">Where Radar found it<select className="input mt-2" name="source" defaultValue={source}><option value="all">All sources</option><option value="watchlist">Companies I follow</option><option value="wide">Broader search</option><option value="direct">Other verified company sources</option></select></label>
            <label className="field-label">Source system <span className="font-normal text-faint">(advanced)</span><select className="input mt-2" name="provider" defaultValue={provider}><option value="">Any</option>{providers.map((item) => <option key={item} value={item}>{titleCase(item)}</option>)}</select></label>
          </div>
        </details>
        <div className="mt-4 flex flex-wrap items-center gap-3"><button className="button-primary" type="submit">Apply filters</button><Link className="button-ghost" href={`/jobs?view=detected&status=${status}`}>Clear</Link><span className="text-xs text-faint">{result.total} jobs · showing {start}–{end}</span></div>
      </form>
      {result.items.length ? <><div className="grid gap-4 xl:grid-cols-2">{result.items.map((job) => <JobCard key={job.id} job={job} compact />)}</div><div className="mt-6 flex items-center justify-between gap-4 border-t border-ui pt-5"><Link aria-disabled={page <= 1} className={page <= 1 ? "button-secondary pointer-events-none opacity-40" : "button-secondary"} href={pageHref(page - 1)}>Previous</Link><span className="text-xs text-faint">Page {page}</span><Link aria-disabled={!result.has_more} className={!result.has_more ? "button-secondary pointer-events-none opacity-40" : "button-secondary"} href={pageHref(page + 1)}>Next</Link></div></> : <EmptyState title="No jobs match these filters" description="Try a wider time range or remove one of the filters." />}
    </>;
  } else {
    const jobs = await serverRequest<JobListItem[]>(`/api/v1/jobs?view=${view}&status=${status}&limit=100`);
    const emptyDescription = view === "matched" ? "Radar has not found an open job that fits your active alerts yet." : view === "saved" ? "Jobs you save will appear here." : "Jobs you hide will appear here so you can restore them later.";
    content = jobs.length ? <div className="grid gap-4 xl:grid-cols-2">{jobs.map((job) => <JobCard key={job.id} job={job} />)}</div> : <EmptyState title={`No ${viewLabels[view].toLowerCase()} jobs`} description={emptyDescription} />;
  }

  return <>
    <PageHeader eyebrow="Jobs" title="Jobs" description="Review matches, browse everything Radar has found, and keep track of jobs you save or hide." />
    {view === "matched" ? <WideSearchRefresh /> : null}
    <div className="mb-5 flex flex-col gap-3 rounded-xl border border-ui surface p-2 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-wrap gap-1">{views.map((item) => <Link key={item} href={tabHref(item, status)} className={item === view ? "tab-active" : "tab"}>{viewLabels[item]}</Link>)}</div>
      <div className="flex flex-wrap gap-1">{statuses.map((item) => <Link key={item} href={tabHref(view, item)} className={item === status ? "tab-active" : "tab"}>{statusLabels[item]}</Link>)}</div>
    </div>
    {content}
  </>;
}
