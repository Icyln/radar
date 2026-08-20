import { redirect } from "next/navigation";
import { Badge } from "@/components/badge";
import { PageHeader } from "@/components/page-header";
import { formatDateTime, humanize } from "@/lib/format";
import { requireUser, serverRequest } from "@/lib/server-api";
import type { AutomationState, DashboardSummary } from "@/types/api";

function tone(state: AutomationState): "success" | "warning" | "danger" | "neutral" {
  if (state === "HEALTHY") return "success";
  if (state === "DEGRADED") return "warning";
  if (state === "FAILED") return "danger";
  return "neutral";
}

function stateLabel(state: AutomationState): string {
  if (state === "UNKNOWN") return "Not run yet";
  return humanize(state);
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="panel-soft p-4"><p className="text-xs text-faint">{label}</p><p className="mt-1 text-xl font-semibold text-main">{value}</p></div>;
}

export default async function AdminSystemPage() {
  const user = await requireUser();
  if (!user.is_admin) redirect("/dashboard");
  const data = await serverRequest<DashboardSummary>("/api/v1/dashboard/summary");

  return <>
    <PageHeader eyebrow="Admin" title="System status" description="Operational health for the automated company monitor and broad job-search workflow." />

    <div className="grid gap-5 xl:grid-cols-2">
      <section className="panel p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><h2 className="font-semibold text-main">Company monitoring</h2><p className="mt-1 text-sm text-soft">Checks verified company career sources and matches new roles against active alerts.</p></div>
          <Badge tone={tone(data.monitoring_automation.state)}>{stateLabel(data.monitoring_automation.state)}</Badge>
        </div>
        <dl className="mt-5 grid gap-3 sm:grid-cols-2">
          <Metric label="Last run" value={formatDateTime(data.monitoring_automation.last_run_at)} />
          <Metric label="Trigger" value={data.monitoring_automation.trigger ? humanize(data.monitoring_automation.trigger) : "—"} />
          <Metric label="Companies selected" value={data.monitoring_automation.companies_selected} />
          <Metric label="Companies succeeded" value={data.monitoring_automation.companies_succeeded} />
          <Metric label="Companies failed" value={data.monitoring_automation.companies_failed} />
          <Metric label="Notifications sent" value={data.monitoring_automation.notifications_sent} />
        </dl>
      </section>

      <section className="panel p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><h2 className="font-semibold text-main">Broad job search</h2><p className="mt-1 text-sm text-soft">Searches supported public job feeds for active alert titles, deduplicates results, and sends matching notifications.</p></div>
          <Badge tone={tone(data.wide_search_automation.state)}>{stateLabel(data.wide_search_automation.state)}</Badge>
        </div>
        <dl className="mt-5 grid gap-3 sm:grid-cols-2">
          <Metric label="Last run" value={formatDateTime(data.wide_search_automation.last_run_at)} />
          <Metric label="Trigger" value={data.wide_search_automation.trigger ? humanize(data.wide_search_automation.trigger) : "—"} />
          <Metric label="Signals seen" value={data.wide_search_automation.signals_seen} />
          <Metric label="Relevant signals" value={data.wide_search_automation.signals_relevant} />
          <Metric label="New jobs" value={data.wide_search_automation.jobs_new} />
          <Metric label="Deduplicated" value={data.wide_search_automation.jobs_deduplicated} />
          <Metric label="Provider failures" value={data.wide_search_automation.provider_failures} />
          <Metric label="Notifications sent" value={data.wide_search_automation.notifications_sent} />
        </dl>
        {data.wide_search_automation.warnings.length ? <div className="status-warning mt-4 rounded-xl p-4 text-xs leading-5"><strong className="block">Warnings</strong><ul className="mt-2 list-disc space-y-1 pl-4">{data.wide_search_automation.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div> : null}
      </section>
    </div>

    <section className="panel mt-5 p-5 sm:p-6">
      <h2 className="font-semibold text-main">Current inventory</h2>
      <p className="mt-1 text-sm text-soft">A compact operational snapshot. User-facing pages intentionally hide these implementation details.</p>
      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Monitored companies" value={data.monitored_companies} />
        <Metric label="Followed companies" value={data.watched_companies} />
        <Metric label="Direct-source jobs today" value={data.direct_jobs_today} />
        <Metric label="Broad-search jobs today" value={data.wide_jobs_today} />
      </div>
    </section>
  </>;
}
